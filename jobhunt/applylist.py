"""APPLY_LIST.md and apply_list.html: every role worth sending, across every run, in the order to send them.

    python3 -m jobhunt list              # re-score each company's newest run (no network), then rebuild
    python3 -m jobhunt list --no-rank    # rebuild from the rankings already on disk

Groups, top to bottom:
  Referral          the best few roles at each company in profile.yaml `referrals` (go through the person, not the site)
  Ask first         strong matches blocked by one stated requirement (ask a referrer or recruiter whether it is firm)
  <your region>     roles in apply_list.local_table regions
  Everywhere else   remote roles and other locations
Inside each group the order is fit x desire: the score with posting age and applicant-pool pressure taken out, so it
answers "which of these do I most want to have sent", not "which is freshest". Every row shows the posted date and
links the posting and the resume to send. Nothing is silently dropped: the "Not on this list" section counts what
was left off and why.

Settings (profile.yaml `apply_list` and `eligibility`): max_required_years, per_company_max,
referral_roles_per_company, local_table, uncapped_companies, old_posting_days, recent_applications_days;
`company_rules` narrows a company (for example only roles in one region, or only certain role types).
Hand-edits to APPLY_LIST.md are lost on rebuild; change profile.yaml or workspace/picks.yaml instead.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from . import analyze, paths, rank, tracker
from .config import load_profile, region_labels
from .resume import pdf_name

TEMPLATE = Path(__file__).with_name("applylist_template.html")
FIT_WORD = {5: "Great", 4: "Good", 3: "Partial", 2: "Stretch", 1: "Stretch", 0: "Stretch"}


# ----------------------------------------------------------------------------- inputs
def load_picks() -> list[dict]:
    p = paths.picks()
    data = (yaml.safe_load(p.read_text()) if p.exists() else None) or {}
    return list(data.get("picks") or [])


def latest_runs() -> list[Path]:
    """Run folders that got as far as candidates, newest first."""
    out = []
    root = paths.runs()
    for d in root.iterdir() if root.exists() else []:
        if (d / "candidates.json").exists() and (d / "meta.json").exists():
            stamp = json.loads((d / "meta.json").read_text()).get("fetched_at") or ""
            out.append((stamp, d.name, d))
    return [d for _, _, d in sorted(out, reverse=True)]


def resume_variant(fit: dict, job: dict, profile: dict) -> str:
    """The reviewer's resume_focus, but a variant with `posting_must_mention` needs the posting itself to ask for that
    work: one of those patterns in the title or required list, or one of `or_in_body` in the description. Choose the
    resume by what the posting asks, not by the company (a web role at a defense company gets the general resume)."""
    variants = profile.get("resume_variants") or {}
    default = next((k for k, v in variants.items() if v.get("default")), next(iter(variants), "general"))
    v = fit.get("resume_focus") or default
    if v not in variants:
        return default
    cfg = variants[v] or {}
    must, body_ok = cfg.get("posting_must_mention") or [], cfg.get("or_in_body") or []
    if not must and not body_ok:
        return v
    sec = analyze.split_sections(job.get("description") or "")
    head = f"{job.get('title') or ''}\n{sec.get('required') or ''}"
    if any(re.search(p, head, re.I) for p in must) or any(re.search(p, sec.get("body") or "", re.I) for p in body_ok):
        return v
    return default


def _rule_for(company: str, profile: dict) -> dict | None:
    return next((r for r in profile.get("company_rules") or [] if tracker.same_company(r.get("company", ""), company)), None)


def _priority(j: dict) -> float:
    p = j["rank"].get("parts") or {}
    return round(j["rank"]["score"] / max(p.get("seen_x", 1) * p.get("competition_x", 1), 0.01), 1)


def _manual_priority(p: dict, profile: dict) -> float:
    mult = profile["work_match_multipliers"]
    locs = profile["location_multipliers"]
    region = p.get("region") or "unknown"
    loc = locs.get(region, locs.get("unknown", 0.8))
    career = float(p.get("career", 4))
    if region == "other_us" and career >= 5 and profile.get("other_us_great_company"):
        loc = max(loc, profile["other_us_great_company"])
    exp = 1.0 if not p.get("yoe") or p["yoe"] <= 1 else 0.8
    return round(100 * 0.9 * mult[int(p["work"])] * exp * loc * (0.7 + 0.06 * career), 1)


def _where(text: str) -> str:
    t = (text or "").strip()
    m = re.match(r"US-([A-Z]{2})-([A-Z .]+?)-", t)                          # US-CA-EL SEGUNDO-E01 ~ ...
    if m:
        return f"{m[2].title()}, {m[1]}"
    m = re.match(r"(?:United States|US)\s*-\s*([A-Za-z ]+?)\s*-\s*(.+)$", t)   # Workday: United States-California-City
    if m:
        return f"{m[2].strip()}, {m[1].strip()}"
    return t if len(t) <= 48 else t[:45].rstrip(" ,;") + "..."


def _history(applied: str | None) -> str:
    a = applied or ""
    if a.startswith("applied before"):
        m = re.search(r"rejected (\d{4}-\d{2}-\d{2})", a)
        return f"this title rejected you {m[1]}" if m else "you applied to this title before"
    if a.startswith("similar role"):
        return a
    return ""


def rows(profile: dict, rerank: bool = True) -> tuple[list[dict], dict]:
    """Every listable role, plus counts of what was left off and why."""
    left = {"duplicates": 0, "long_shots": 0, "company_rules": {}, "not_recommended": 0}
    history = tracker.load()
    picks = load_picks()
    covered: set[str] = set()
    out, seen = [], set()
    stem = pdf_name(yaml.safe_load(paths.resume_yaml().read_text()) if paths.resume_yaml().exists() else {})
    referrals = {r["company"]: r.get("contact") or "your contact" for r in profile.get("referrals") or []
                 if not r.get("job_id") and not r.get("title")}
    for run_dir in latest_runs():
        meta = json.loads((run_dir / "meta.json").read_text())
        if rerank and any((run_dir / "fit").glob("*.json")):
            rank.rank_and_report(run_dir, profile)
        if not (run_dir / "ranked.json").exists():
            continue  # not reviewed yet: its company stays uncovered, so an older ranked run still counts
        run_cos = meta.get("companies") or [meta.get("company")]
        for j in json.loads((run_dir / "ranked.json").read_text()):
            if any(tracker.same_company(j["company"], c) for c in covered):
                continue  # a newer run holds this company: its postings there are the current ones
            fit, r = j.get("fit") or {}, j["rank"]
            pick = next((p for p in picks if tracker.same_company(p.get("company", ""), j["company"])
                         and str(p.get("job_id")) in [str(j["id"])] + [str(d["id"]) for d in j.get("duplicates") or []]), None)
            applied = tracker.match(j, history)
            if (applied or "").startswith("DUPLICATE"):
                left["duplicates"] += 1
                continue
            tier = r.get("fit_tier") or r["tier"]
            blocked = r["tier"] == "X" and r.get("unblocked_tier") in ("A", "B")
            if r["tier"] == "X" and not blocked and not pick:
                left["not_recommended"] += 1
                continue
            if tier == "D" and not pick:
                left["long_shots"] += 1
                continue
            region = r["notes"].get("location") or "unknown"
            rule = _rule_for(j["company"], profile)
            if rule and not pick:
                bad_region = rule.get("only_regions") and region not in rule["only_regions"]
                bad_type = rule.get("only_role_types") and fit.get("role_type") not in rule["only_role_types"]
                if bad_region or bad_type:
                    left["company_rules"][j["company"]] = left["company_rules"].get(j["company"], 0) + 1
                    continue
            key = (j["company"], j["title"], rank._loc_short(j, profile))
            if key in seen:
                continue
            seen.add(key)
            variant = resume_variant(fit, j, profile)
            out.append({"company": j["company"], "title": j["title"], "url": j["url"],
                        "where": _where(rank._loc_short(j, profile)), "region": region,
                        "posted": (j.get("posted_at") or "")[:10], "work": fit.get("work_match"),
                        "yoe": (j["signals"]["yoe"] or {}).get("required_min"), "variant": variant,
                        "resume": f"resume/{variant}/{stem}", "priority": _priority(j), "tracked": bool(pick),
                        "blocked": fit.get("dealbreaker") if blocked else "", "why": fit.get("why") or "",
                        "history": _history(applied), "through": referrals.get(next(
                            (c for c in referrals if tracker.same_company(c, j["company"])), ""), ""),
                        "note": (pick or {}).get("note") or ""})
        covered |= {c for c in run_cos if c}
    for p in picks:  # tracked roles with a hand score and no run behind them
        if p.get("work") is None or not p.get("url") or any(r["url"] == p["url"] for r in out):
            continue
        if any(tracker.same_company(h.get("company"), p.get("company")) and str(h.get("job_id") or "") == str(p.get("job_id"))
               for h in history if h.get("job_id")):
            left["duplicates"] += 1
            continue
        variant = p.get("variant") or "general"
        out.append({"company": p["company"], "title": p.get("title") or str(p.get("job_id")), "url": p["url"],
                    "where": p.get("where") or "", "region": p.get("region") or "unknown", "posted": str(p.get("posted") or ""),
                    "work": p["work"], "yoe": p.get("yoe"), "variant": variant, "resume": f"resume/{variant}/{stem}",
                    "priority": _manual_priority(p, profile), "tracked": True, "blocked": "", "why": p.get("note") or "",
                    "history": "", "through": next((v for c, v in referrals.items() if tracker.same_company(c, p["company"])), ""),
                    "note": p.get("note") or ""})
    for r in out:
        r["id"] = hashlib.sha1(r["url"].encode()).hexdigest()[:12]
    out.sort(key=lambda r: -r["priority"])
    return out, left


# ----------------------------------------------------------------------------- rendering
def _fit(r: dict) -> str:
    word = f"{FIT_WORD.get(r['work'], '?')} ({r['work']}/5)" if r["work"] is not None else "Not rated"
    yoe = "no years stated" if not r["yoe"] else f"asks {r['yoe']:g}+ yrs"
    return f"{word} · {yoe}" + (f" · {r['history']}" if r.get("history") else "")


def _posted(r: dict, today: date, old_days: int) -> str:
    if not r["posted"]:
        return "?"
    try:
        old = (today - date.fromisoformat(r["posted"])).days > old_days
    except ValueError:
        old = False
    return r["posted"] + (" (old)" if old else "")


def _table(rs: list[dict], today: date, old_days: int, through: bool = False, blocked: bool = False) -> list[str]:
    cols = ["#", "Position", "Company", "Location", "Posted", "Fit · years asked", "Resume"]
    cols += ["Through"] if through else []
    cols += ["The requirement"] if blocked else []
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for i, r in enumerate(rs, 1):
        title = r["title"].replace("|", "/")
        line = (f"| {i} | [{title}]({r['url']}) | {r['company']} | {r['where']} | {_posted(r, today, old_days)} | {_fit(r)} "
                f"| [{r['variant']}]({r['resume'].replace(' ', '%20')}) |")
        if through:
            line += f" {r['through']} |"
        if blocked:
            line += f" {str(r['blocked']).replace('|', '/')} |"
        md.append(line)
    return md


def build(profile: dict | None = None, rerank: bool = True) -> dict:
    profile = profile or load_profile()
    cfg = profile.get("apply_list") or {}
    today = date.today()
    old_days = int(cfg.get("old_posting_days", 120))
    max_years = float((profile.get("eligibility") or {}).get("max_required_years", 3))
    rs, left = rows(profile, rerank)
    too_senior = [r for r in rs if (r["yoe"] or 0) > max_years and not r["tracked"]]
    rs = [r for r in rs if r not in too_senior]
    # per-company cap: count what you already sent recently
    since = (today - timedelta(days=int(cfg.get("recent_applications_days", 90)))).isoformat()
    recent = [a for a in tracker.load() if (a.get("date_applied") or "") >= since]
    cap = int(cfg.get("per_company_max", 8))
    uncapped = cfg.get("uncapped_companies") or []
    kept, cut, per = [], {}, {}
    for r in rs:
        if r["company"] not in per:
            per[r["company"]] = sum(1 for a in recent if tracker.same_company(a.get("company"), r["company"]))
        per[r["company"]] += 1
        if per[r["company"]] <= cap or r["tracked"] or any(tracker.same_company(c, r["company"]) for c in uncapped):
            kept.append(r)
        else:
            cut[r["company"]] = cut.get(r["company"], 0) + 1
    rs = kept
    blocked = [r for r in rs if r["blocked"]]
    rs = [r for r in rs if not r["blocked"]]
    per_ref = int(cfg.get("referral_roles_per_company", 3))
    referral, rest, count = [], [], {}
    for r in rs:
        if r["through"]:
            count[r["company"]] = count.get(r["company"], 0) + 1
            if count[r["company"]] <= per_ref:
                referral.append(r)
                continue
        rest.append(r)
    labels = region_labels(profile)
    local_keys = cfg.get("local_table") or ([profile["regions"][0]["key"]] if profile.get("regions") else [])
    local_title = labels.get(local_keys[0], "Your region") if local_keys else ""
    local = [r for r in rest if r["region"] in local_keys]
    other = [r for r in rest if r["region"] not in local_keys]
    years = rank.candidate_yoe(profile)
    md = [
        "# Apply list", "",
        f"Updated {datetime.now():%Y-%m-%d %H:%M}. Rebuild with `python3 -m jobhunt list`.", "",
        "- **Order:** each table runs from the application you most want sent to the one you would miss least. It "
        "combines how well you meet the requirements with what you want (location, role type, career value). Posting "
        f"age is not part of the order; postings older than {old_days} days are marked (old). Fresh postings still "
        "matter: send new ones within a week.",
        f"- **Fit:** how much of the job's daily work you have already done, out of 5, then the years the posting asks "
        f"for. You have {years:g} years full time. Postings asking more than {max_years:g} years are left off.",
        "- **Resume:** which variant to send; each links to the PDF.",
        "- **Checkboxes:** open apply_list.html to tick roles off as you send them.", "",
    ]
    if referral:
        md += [f"## Referral ({len(referral)})", "",
               f"Go through the person, not the site: send them the posting link. At most {per_ref} roles per company "
               "are listed here; ask for the first one, and name a second if their referral form allows it.", "",
               *_table(referral, today, old_days, through=True), ""]
    if blocked:
        md += [f"## Ask first: one stated requirement in the way ({len(blocked)})", "",
               "Strong matches except for one line in the posting. Ask a referrer or the recruiter whether it is firm "
               "before applying cold.", "", *_table(blocked, today, old_days, blocked=True), ""]
    if local_keys:
        md += [f"## {local_title} ({len(local)})", "", *_table(local, today, old_days), ""]
    md += [f"## Everywhere else ({len(other)})", "", "Remote roles are here too.", "", *_table(other, today, old_days), ""]
    notes = []
    if left["duplicates"]:
        notes.append(f"{left['duplicates']} roles you already applied to (same posting, or the same title at that company).")
    if too_senior:
        notes.append(f"{len(too_senior)} roles that ask for more than {max_years:g} years of experience.")
    if cut:
        notes.append(f"Anything past a company's best {cap} (minus what you sent there in the last "
                     f"{cfg.get('recent_applications_days', 90)} days): "
                     + ", ".join(f"{c} ({n} more)" for c, n in sorted(cut.items(), key=lambda x: -x[1]))
                     + ". They are in that company's report.")
    for c, n in left["company_rules"].items():
        rule = _rule_for(c, profile) or {}
        notes.append(f"{n} {c} roles outside your rule for that company" + (f" ({rule['note']})" if rule.get("note") else "") + ".")
    if left["long_shots"]:
        notes.append(f"{left['long_shots']} long shots (tier D); see each run's REPORT.md.")
    if left["not_recommended"]:
        notes.append(f"{left['not_recommended']} roles the reviewer ruled out after reading the posting; see each run's REPORT.md.")
    md += ["## Not on this list", "", *[f"- {n}" for n in notes or ["Nothing was left off."]], ""]
    out_md = paths.workspace() / "APPLY_LIST.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md))

    def page_rows(group: list[dict]) -> list[dict]:
        return [{"id": r["id"], "title": r["title"], "url": r["url"], "company": r["company"], "where": r["where"],
                 "posted": r["posted"] or "?", "old": _posted(r, today, old_days).endswith("(old)"), "fit": _fit(r),
                 "variant": r["variant"], "resume": r["resume"], "why": r["blocked"] or "", "through": r["through"]}
                for r in group]
    data = {"updated": f"Updated {datetime.now():%b %d, %Y}", "groups": [g for g in [
        {"title": "Referral", "rows": page_rows(referral), "through": True, "note": "Go through the person, not the site."},
        {"title": "Ask first: one stated requirement in the way", "rows": page_rows(blocked),
         "note": "Ask whether the requirement is firm before applying."},
        {"title": local_title, "rows": page_rows(local), "note": ""} if local_keys else None,
        {"title": "Everywhere else", "rows": page_rows(other), "note": "Remote roles are here too."}] if g and g["rows"]]}
    out_html = paths.workspace() / "apply_list.html"
    out_html.write_text(TEMPLATE.read_text().replace("__DATA__", json.dumps(data).replace("</", "<\\/")))
    return {"page": str(out_md), "html": str(out_html), "referral": len(referral), "ask_first": len(blocked),
            "local": len(local), "elsewhere": len(other), "total": len(referral) + len(blocked) + len(local) + len(other),
            "left_off": {"duplicates": left["duplicates"], "too_many_years": len(too_senior), "company_cap": cut,
                         "company_rules": left["company_rules"], "long_shots": left["long_shots"],
                         "not_recommended": left["not_recommended"]}}


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
