"""Recall-first triage.

Only clear-cut mismatches are excluded, and every exclusion carries a reason so the
excluded list can be skimmed for misses. Everything else becomes a candidate that gets
a full read (by AI review subagents) before ranking.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .analyze import analyze, boilerplate_lines, split_sections, strip_boilerplate

REASONS = {
    "screened_out": "Not a role worth reading for you (AI title screen; reason listed)",
    "outside_regions": "No location in the regions this sweep covers",
    "non_us": "Located outside the US only",
    "intern": "Internship / co-op",
    "employment_type": "Contract / temporary / part-time",
    "level_title": "Title level well above you (staff / principal / lead / manager / director)",
    "senior_no_low_yoe": "'Senior' title without a stated requirement within your years limit",
    "yoe_too_high": "Requires more years of experience than your limit (profile.yaml eligibility.max_required_years)",
    "active_clearance": "Requires an active security clearance you don't hold",
    "phd_required": "PhD required",
    "family_nonmatch": "Not a software or software-adjacent role (by title)",
}


def _profile_limits(profile: dict) -> dict:
    t = profile.get("triage", {})
    return {
        "max_required_yoe": float(t.get("max_required_yoe", 3)),
        "exclude_employment": [x.lower() for x in t.get("exclude_employment_types", ["contract", "temporary", "part-time", "part time", "intern"])],
        "has_clearance": (profile.get("clearance") or "none").lower() not in ("none", "", "no"),
        "include_families": t.get("include_families", ["core", "adjacent", "unknown"]),
    }


def title_level_reasons(job: dict, lim: dict) -> list[str]:
    """Universal checks that need only the title/location/employment type."""
    from .analyze import explicitly_non_us, title_level
    reasons = []
    if explicitly_non_us(job.get("locations") or []):
        reasons.append("non_us")
    lvl = title_level(job.get("title", ""))
    if lvl == "intern":
        reasons.append("intern")
    et = (job.get("employment_type") or "").lower()
    if et and any(x in et for x in lim["exclude_employment"]):
        reasons.append("intern" if "intern" in et else "employment_type")
    if lvl in ("manager", "staff+", "lead"):
        reasons.append("level_title")
    return list(dict.fromkeys(reasons))


def description_level_reasons(job: dict, sig: dict, lim: dict) -> list[str]:
    """Universal checks that need the posting text; each one has quoted evidence in the signals."""
    reasons = []
    req = sig["yoe"]["required_min"]
    if sig["level"] in ("senior", "senior+") and (req is None or req > lim["max_required_yoe"]):
        reasons.append("senior_no_low_yoe")
    if req is not None and req > lim["max_required_yoe"]:
        reasons.append("yoe_too_high")
    if sig["clearance"]["status"] == "active_required" and not lim["has_clearance"]:
        reasons.append("active_clearance")
    if sig["degree"]["phd_required"]:
        reasons.append("phd_required")
    return reasons


def run_title_filters(jobs: list[dict], profile: dict) -> tuple[list[dict], list[dict]]:
    lim = _profile_limits(profile)
    keep, out = [], []
    for j in jobs:
        r = title_level_reasons(j, lim)
        j["exclude_reasons"] = r
        (out if r else keep).append(j)
    return keep, out


def run_description_filters(jobs: list[dict], profile: dict, regions_wanted: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Evidence-based checks on the posting text. `regions_wanted` (a sweep's region filter) drops postings with no
    location in those regions, once their locations are known."""
    from .screen import load_locations, needs_location_screen, region_for
    lim = _profile_limits(profile)
    lcache = load_locations()
    keep, out = [], []
    for j in jobs:
        sig = analyze(j)
        sig["location"] = region_for(j, lcache, profile)
        dec = j.get("screen") or {}
        if dec.get("family"):
            sig["family"] = {"software": "core", "adjacent": "adjacent"}.get(dec["family"], sig["family"])
        j["signals"] = sig
        r = description_level_reasons(j, sig, lim)
        if sig["location"]["best"] == "non_us" and sig["location"]["source"] == "screened":
            r.insert(0, "non_us")
        elif regions_wanted and not set(sig["location"]["all"]) & set(regions_wanted) and not j.get("needs_detail"):
            # A string that might be in one of your regions but that the screener hasn't classified yet is kept;
            # the reviewer reads the posting and can set its region.
            unsure = j.get("region_pending") and sig["location"]["source"] == "regex" and any(
                needs_location_screen(l, profile) for l in (j.get("locations") or []) if l.strip() not in lcache)
            if not unsure:
                r.insert(0, "outside_regions")
        j["exclude_reasons"] = r
        (out if r else keep).append(j)
    return keep, out


# ----------------------------------------------------------------------------- outputs
def _short_date(iso: str | None) -> str:
    return iso[:10] if iso else "?"


def write_triage_outputs(run_dir: Path, label: str, all_jobs: list[dict], candidates: list[dict], excluded: list[dict],
                         total_fetched: int | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "candidates.json").write_text(json.dumps(candidates, indent=1, default=str))
    (run_dir / "excluded.json").write_text(json.dumps(excluded, indent=1, default=str))

    by_reason: dict[str, list[dict]] = defaultdict(list)
    for j in excluded:
        by_reason[j["exclude_reasons"][0]].append(j)
    fam = Counter(j["signals"]["family"] for j in candidates)

    lines = [
        f"# Triage: {label}",
        "",
        f"- Total open postings fetched: **{total_fetched or len(all_jobs)}**",
        *([f"- In the regions asked for, or not yet placed: **{len(all_jobs)}**"] if total_fetched and total_fetched != len(all_jobs) else []),
        f"- Candidates for full review: **{len(candidates)}** "
        f"(software: {fam.get('core', 0)}, adjacent: {fam.get('adjacent', 0)}, unclassified titles: {fam.get('unknown', 0)})",
        f"- Excluded: **{len(excluded)}**",
        "",
        "## Exclusions by first reason",
        "",
    ]
    for code, items in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"- {REASONS.get(code, code)}: {len(items)}")
    lines += ["", "## Software/adjacent roles excluded by a structural rule (skim these for misses)", ""]
    from .analyze import job_family

    def fam(j):
        sig = j.get("signals")
        if sig and sig.get("family"):
            return sig["family"]
        return job_family(j.get("title", ""), j.get("department"))  # hint only, for this listing

    sw_ex = [j for j in excluded if j["exclude_reasons"] and j["exclude_reasons"][0] != "screened_out"
             and fam(j) in ("core", "adjacent")]
    for j in sorted(sw_ex, key=lambda x: (x["company"], x["title"])):
        sig = j.get("signals") or {}
        yoe = (sig.get("yoe") or {}).get("required_min")
        clr = (sig.get("clearance") or {}).get("status", "-")
        lines.append(
            f"- {j['company']}: {j['title']} | {', '.join(j['locations'][:2])} | yoe={yoe if yoe is not None else '?'} | "
            f"clr={clr} | why: {', '.join(j['exclude_reasons'])}"
        )
    lines += ["", "## Screened out by title (company: title → screener's reason)", ""]
    scr = Counter((f"{j['company']}: {j['title']}", (j.get("screen") or {}).get("reason", "")) for j in excluded if j["exclude_reasons"][:1] == ["screened_out"])
    lines.append("; ".join(f"{t} ({r})" + (f" ×{c}" if c > 1 else "") for (t, r), c in sorted(scr.items())))
    (run_dir / "triage.md").write_text("\n".join(lines) + "\n")


DUTIES_RX = re.compile(r"^\s*(what you.ll do|what you will do|responsibilities|key responsibilities|about the (?:role|job)|"
                       r"in this role|the role|you.re excited about this opportunity because you will|your (?:role|impact)|"
                       r"day[- ]to[- ]day)\b[^\n]{0,60}$", re.I | re.M)


def job_card(j: dict, boiler: set | None = None, heading: str | None = None) -> list[str]:
    """One posting as a compact card for a reviewer. The day-to-day duties are shown in full: what a person
    in the job does all week says more about fit than the list of minimum qualifications."""
    sig = j["signals"]
    desc = strip_boilerplate(j.get("description") or "", boiler or set())
    desc = re.sub(r"\n{2,}(?=•)", "\n", desc)  # compact bullet lists
    secs = split_sections(desc)
    yoe = sig["yoe"]
    sal = sig["salary"]
    out = [
        heading or f"## [{j.get('key', '-')}] {j['company']} — {j['title']}",
        f"- id: {j['id']} | posted: {_short_date(j.get('posted_at'))} ({sig['age_days']} days, via {j.get('posted_at_source')})"
        f" | locations: {'; '.join(j['locations'][:4])}{' (+more)' if len(j['locations']) > 4 else ''}",
        f"- dept/team: {j.get('department') or '-'} / {j.get('team') or '-'} | type: {j.get('employment_type') or '-'}",
        f"- signals: family={sig['family']} level={sig['level']} yoe_required={yoe['required_min']} "
        f"(pref {yoe['preferred_min']}) clearance={sig['clearance']['status']} poly={sig['clearance']['polygraph']} "
        f"us_person={sig['us_person_required']} salary={sal.get('text') or '-'}",
    ]
    if yoe["mentions"]:
        snips = list(dict.fromkeys(m["snippet"][:160] for m in yoe["mentions"]))
        out.append("- yoe evidence: " + " || ".join(snips[:3]))
    if sig["seniority_phrases"]:
        out.append("- seniority phrases: " + ", ".join(sig["seniority_phrases"]))
    body = (secs["body"] or "").strip()
    req = (secs["required"] or "").strip()
    pref = (secs["preferred"] or "").strip()
    if not req and not pref:
        out += ["", "DESCRIPTION:", desc[:4200]]
    else:
        duties = list(DUTIES_RX.finditer(body))
        if duties:  # short intro, then the duties in full
            cut = duties[0].start()
            intro = body[:cut].strip()
            if len(intro) > 600:  # keep the end of the intro, starting at a sentence
                intro = intro[-600:]
                intro = intro[intro.find(". ") + 2:] if ". " in intro[:200] else intro
            out += ["", "ABOUT:", intro, "", "WHAT THE JOB IS:", body[cut:].strip()[:2200]]
        else:
            out += ["", "ABOUT AND DUTIES:", body[:2600]]
        out += ["", "REQUIRED:", req[:2000], "", "PREFERRED:", pref[:1200]]
    return out + ["", "---", ""]


def write_review_packets(run_dir: Path, candidates: list[dict], all_jobs: list[dict], batch_size: int = 15) -> list[Path]:
    """Compact job cards for subagent review, each company's boilerplate (about us, benefits, EEO) stripped."""
    by_company: dict[str, list[dict]] = defaultdict(list)
    for j in all_jobs:
        by_company[j["company"]].append(j)
    boiler = {co: boilerplate_lines(js) for co, js in by_company.items()}
    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    for old in review_dir.glob("*batch_*.md"):
        old.unlink()
    # Unique prefix per review pass so a re-run's reviewers never overwrite earlier fit/*.json files.
    from datetime import datetime as _dt
    prefix = "p" + _dt.now().strftime("%m%d%H%M") + "_"
    # Identical postings (same title + same text, e.g. one req listed in several cities) are reviewed once;
    # rank.py copies the review to the duplicates.
    seen, unique = set(), []
    for j in candidates:
        k = dup_key(j)
        if k in seen:
            continue
        seen.add(k)
        unique.append(j)
    order = sorted(unique, key=lambda j: ({"core": 0, "adjacent": 1, "unknown": 2}.get(j["signals"]["family"], 3), j["company"], j["title"]))
    paths = []
    for b in range(0, len(order), batch_size):
        chunk = order[b: b + batch_size]
        out = [f"# Review batch {b // batch_size + 1:02d} ({len(chunk)} jobs)", ""]
        for j in chunk:
            out += job_card(j, boiler.get(j["company"]))
        path = review_dir / f"{prefix}batch_{b // batch_size + 1:02d}.md"
        path.write_text("\n".join(out))
        paths.append(path)
    return paths


def assign_keys(candidates: list[dict]) -> None:
    for i, j in enumerate(sorted(candidates, key=lambda x: (x["company"], x["title"], str(x["id"]))), 1):
        j["key"] = f"J{i:03d}"


def dup_key(job: dict) -> tuple:
    import hashlib
    title = re.sub(r"\W+", " ", (job.get("title") or "").lower()).strip()
    desc = re.sub(r"\s+", " ", (job.get("description") or "")[:4000]).lower()
    return (job.get("company") or "", title, hashlib.md5(desc.encode()).hexdigest())
