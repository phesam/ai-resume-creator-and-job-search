"""AI screening step: titles and locations are judged by a model reading each company's own wording.

Deterministic code only applies universal structural checks (explicit non-US country, internships, staff/
director titles, an explicitly stated years requirement above your limit, an explicit active-clearance
requirement, PhD required). Everything fuzzy ("is this title a role worth reading for this candidate?", "which
of my regions is this location string?") is decided by a screening subagent following
jobhunt/rubrics/SCREEN_RUBRIC.md and the run's screen/BRIEF.md, because keyword lists can't anticipate every
company's naming. Regex classifications are shown only as hints.

A run can hold one company or many (a sweep). Title groups are keyed by (company, normalized title).

Decisions are cached so repeat runs only screen new strings:
  workspace/cache/locations.json            location string -> region key (all companies)
  workspace/cache/title_screens/<slug>.json normalized title -> decision (per company)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from . import paths
from .analyze import job_family, location_class
from .common import slugify
from .config import broad_matchers, candidate_brief, load_profile, region_keys

GROUPS_PER_FILE = 120  # small files keep each screener's output short (long single outputs stall)


def loc_cache_path() -> Path:
    return paths.cache() / "locations.json"


def title_dir() -> Path:
    return paths.cache() / "title_screens"


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#/&]+", " ", (t or "").lower())).strip()


def load_locations() -> dict:
    p = loc_cache_path()
    return json.loads(p.read_text()) if p.exists() else {}


def save_locations(d: dict) -> None:
    p = loc_cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(d.items())), indent=0))


def load_title_cache(company: str) -> dict:
    p = title_dir() / f"{slugify(company)}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_title_cache(company: str, d: dict) -> None:
    title_dir().mkdir(parents=True, exist_ok=True)
    (title_dir() / f"{slugify(company)}.json").write_text(json.dumps(d, indent=0, sort_keys=True))


def _order(profile: dict) -> list[str]:
    return [r["key"] for r in profile.get("regions") or []] + ["remote_us", "other_us", "unknown", "non_us"]


def region_for(job: dict, cache: dict | None = None, profile: dict | None = None) -> dict:
    """Best region for a job: screened (cached) regions win; the regex hint is the fallback."""
    cache = load_locations() if cache is None else cache
    profile = profile or load_profile()
    order = _order(profile)
    valid = set(order)
    regions, source = [], "screened"
    for loc in job.get("locations") or []:
        r = cache.get(loc.strip())
        if r not in valid:
            source = "regex"
            r = location_class([loc], None)["best"]
            r = "non_us" if r == "non_us_remote" else r
        regions.append(r)
    if job.get("remote") and "remote_us" not in regions and "non_us" not in regions:
        regions.append("remote_us")
    if not regions:
        regions = ["unknown"]
    best = min(regions, key=lambda r: order.index(r) if r in order else len(order))
    return {"best": best, "all": sorted(set(regions), key=lambda r: order.index(r) if r in order else 99), "source": source}


def needs_location_screen(loc: str, profile: dict) -> bool:
    """In a sweep, a string worth asking the screener about: the regex put it nowhere useful, but it matches one of
    your regions' broad patterns (for example "California" when the city list misses the town)."""
    hint = location_class([loc], None)["best"]
    if hint not in ("other_us", "unknown"):
        return False
    return any(rx.search(loc) for rx in broad_matchers(profile))


# ----------------------------------------------------------------------------- inputs for the screener
def write_screen_inputs(run_dir: Path, jobs: list[dict], profile: dict | None = None,
                        location_strings: list[str] | None = None) -> dict:
    """Write screen/BRIEF.md, screen/titles_XX.md and screen/locations.md for whatever isn't cached yet.

    `location_strings`: the strings to classify (default: every location of these jobs that isn't cached)."""
    profile = profile or load_profile()
    sdir = run_dir / "screen"
    sdir.mkdir(parents=True, exist_ok=True)
    for old in sdir.glob("titles_*.md"):
        old.unlink()
    (sdir / "BRIEF.md").write_text(candidate_brief(profile))
    lcache = load_locations()
    caches: dict[str, dict] = {}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for j in jobs:
        groups[(j["company"], norm_title(j["title"]))].append(j)
    pending = {}
    for (co, nt), js in groups.items():
        if co not in caches:
            caches[co] = load_title_cache(co)
        if nt not in caches[co]:
            pending[(co, nt)] = js
    # likely-relevant first so the screener sees the important ones with fresh attention
    hint_rank = {"core": 0, "adjacent": 1, "unknown": 2, "nonmatch": 3}
    ordered = sorted(pending.items(), key=lambda kv: (hint_rank.get(job_family(kv[1][0]["title"], kv[1][0].get("department")), 2), kv[0]))
    gid_map, files = {}, []
    for f_i in range(0, len(ordered), GROUPS_PER_FILE):
        chunk = ordered[f_i: f_i + GROUPS_PER_FILE]
        lines = [f"# Titles to screen — file {f_i // GROUPS_PER_FILE + 1}", "",
                 "Format: id | company | title | department/team | postings | sample locations | regex hint (hint only, may be wrong)", ""]
        for i, ((co, nt), js) in enumerate(chunk, f_i + 1):
            gid = f"G{i:04d}"
            gid_map[gid] = [co, nt]
            j0 = js[0]
            dept = " / ".join(x for x in (j0.get("department"), j0.get("team")) if x)[:80]
            locs = "; ".join(sorted({l for j in js for l in (j.get("locations") or [])}))[:120]
            hint = job_family(j0["title"], j0.get("department"))
            lines.append(f"{gid} | {co} | {j0['title']} | {dept or '-'} | {len(js)} | {locs or '-'} | {hint}")
        path = sdir / f"titles_{f_i // GROUPS_PER_FILE + 1:02d}.md"
        path.write_text("\n".join(lines) + "\n")
        files.append(path.name)

    if location_strings is None:
        location_strings = [l for j in jobs for l in (j.get("locations") or [])]
    unknown_locs = sorted({l.strip() for l in location_strings if l.strip() and l.strip() not in lcache})
    loc_lines = ["# Location strings to classify (use the region keys in BRIEF.md)", "",
                 "Format: location string || regex suggestion (may be wrong)", ""]
    for l in unknown_locs:
        sug = location_class([l], None)["best"]
        loc_lines.append(f"{l} || {'non_us' if sug == 'non_us_remote' else sug}")
    (sdir / "locations.md").write_text("\n".join(loc_lines) + "\n")
    (sdir / "groups.json").write_text(json.dumps(gid_map))
    return {"title_files": files, "titles_pending": len(pending), "titles_cached": len(groups) - len(pending),
            "locations_pending": len(unknown_locs)}


def apply_screen(run_dir: Path, profile: dict | None = None) -> dict:
    """Merge screen/screen*.(txt|json) decisions into the caches."""
    profile = profile or load_profile()
    valid_regions = set(region_keys(profile))
    sdir = run_dir / "screen"
    gid_map = json.loads((sdir / "groups.json").read_text()) if (sdir / "groups.json").exists() else {}
    caches: dict[str, dict] = {}
    lcache = load_locations()
    n_t = n_l = 0
    bad_regions: set[str] = set()
    decisions = [json.loads(p.read_text()) for p in sorted(sdir.glob("screen*.json"))]
    decisions += [parse_compact(p.read_text()) for p in sorted(sdir.glob("screen*.txt"))]
    for d in decisions:
        for gid, dec in (d.get("titles") or {}).items():
            if gid not in gid_map:
                continue
            co, nt = gid_map[gid]
            caches.setdefault(co, load_title_cache(co))
            caches[co][nt] = {"keep": bool(dec.get("keep", True)), "family": dec.get("family", "software"),
                              "reason": (dec.get("reason") or "")[:160]}
            n_t += 1
        for loc, reg in (d.get("locations") or {}).items():
            if reg in valid_regions:
                lcache[loc.strip()] = reg
                n_l += 1
            else:
                bad_regions.add(reg)
    for co, c in caches.items():
        save_title_cache(co, c)
    save_locations(lcache)
    # The decisions now live in the caches. Move the files aside: their G-ids belong to this groups.json, and a
    # later screen-prep numbers its new titles from G0001 again, so re-reading them would pin old decisions on
    # different titles.
    done = sorted([*sdir.glob("screen*.json"), *sdir.glob("screen*.txt")])
    if done:
        dest = sdir / "applied" / datetime.now().strftime("%Y%m%d-%H%M%S")
        dest.mkdir(parents=True, exist_ok=True)
        for f in done:
            f.rename(dest / f.name)
        (dest / "groups.json").write_text(json.dumps(gid_map))
    missing = sum(1 for co, nt in gid_map.values() if nt not in (caches.get(co) or load_title_cache(co)))
    out = {"titles_applied": n_t, "locations_applied": n_l, "titles_still_unscreened": missing}
    if bad_regions:
        out["unknown_region_keys_ignored"] = sorted(bad_regions)
    return out


def title_decision(company: str, title: str, cache: dict | None = None) -> dict | None:
    cache = load_title_cache(company) if cache is None else cache
    return cache.get(norm_title(title))


def parse_compact(text: str) -> dict:
    """Compact screener output, one decision per line:
         G0001 keep software
         G0002 keep adjacent
         G0003 drop <short reason>
         L Costa Mesa, California, United States => home
    """
    titles, locs = {}, {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("L ") and "=>" in line:
            loc, reg = line[2:].rsplit("=>", 1)
            locs[loc.strip()] = reg.strip().lower()
            continue
        m = re.match(r"^(G\d{3,5})\s+(keep|drop)\b\s*(.*)$", line, re.I)
        if not m:
            continue
        gid, verdict, rest = m.group(1), m.group(2).lower(), m.group(3).strip()
        if verdict == "keep":
            fam = rest.split()[0].lower() if rest else "software"
            titles[gid] = {"keep": True, "family": fam if fam in ("software", "adjacent") else "software", "reason": ""}
        else:
            titles[gid] = {"keep": False, "family": "other", "reason": rest[:160]}
    return {"titles": titles, "locations": locs}
