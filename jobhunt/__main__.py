"""jobhunt: every open job worth your time, ranked by callback odds, plus the resume and the application record.

Run from the repository root. Your files live in workspace/ (or $JOBHUNT_WORKSPACE).

  python3 -m jobhunt init                           # create workspace/ from templates/ (never overwrites)
  python3 -m jobhunt doctor                         # check Chrome, poppler, Python packages, workspace, tests
  python3 -m jobhunt find "Company"                 # fetch ALL postings, universal checks, prepare the AI screen (exit 3)
  python3 -m jobhunt sweep --regions home,remote_us # the same across many registry companies, kept to your regions
  python3 -m jobhunt screen-apply <run_dir>         # after screen/screen_XX.txt exist: descriptions, checks, review packets
  python3 -m jobhunt rank <run_dir>                 # after fit/*.json reviews exist: score + REPORT.md / report.html
  python3 -m jobhunt list                           # APPLY_LIST.md + apply_list.html across every run and picks.yaml
  python3 -m jobhunt watch                          # postings new since the last check at watchlist.yaml companies
  python3 -m jobhunt fresh list --days 8            # postings first published in the last N days, not yet reviewed
  python3 -m jobhunt resume --variant general       # build workspace/resume/general/<Name>_Resume.pdf with every check
  python3 -m jobhunt applied add --company X --title "..." --url ...    # log an application
  python3 -m jobhunt applied import-email           # rebuild history from workspace/email_import/*.jsonl
  python3 -m jobhunt resolve "Company" | detect <careers-url> | register --name X --ats greenhouse --token x
  python3 -m jobhunt privacy-check                  # scan the repo for your personal terms before committing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

from . import ROOT, ats, ats_extra, paths, rank, resolve, screen, tracker, triage  # noqa: F401 (ats_extra registers adapters)
from .common import parse_date, slugify
from .config import load_profile, region_keys


# ----------------------------------------------------------------------------- init / doctor
def unfilled(profile: dict | None = None) -> list[str]:
    """What still holds template content. Searching with the template profile would score you as someone else."""
    import yaml
    todo = []
    profile = profile or load_profile()
    if not paths.profile().exists() or (profile.get("name") or "").strip() in ("", "Your Name"):
        todo.append("profile.yaml is still the template (say \"set me up\" to fill it in)")
    inv = paths.inventory()
    if not inv.exists() or "<Employer>" in inv.read_text() and inv.read_text().count("## ") < 8:
        todo.append("inventory.md has no entries yet (say \"interview me\")")
    res = paths.resume_yaml()
    if not res.exists() or ((yaml.safe_load(res.read_text()) or {}).get("header") or {}).get("name") == "Jordan Lee":
        todo.append("resume.yaml is still the fictional example (say \"write my resume\")")
    return todo


def _warn_if_unfilled() -> None:
    for t in unfilled():
        if t.startswith("profile") or t.startswith("inventory"):
            print(f"WARNING: {t}. Results will not reflect you.", file=sys.stderr)


WORKSPACE_FILES = ["inventory.md", "profile.yaml", "resume.yaml", "decisions.md", "watchlist.yaml", "picks.yaml"]


def cmd_init(a) -> int:
    ws = paths.workspace()
    ws.mkdir(parents=True, exist_ok=True)
    made, kept = [], []
    for name in WORKSPACE_FILES:
        src, dst = paths.templates() / name, ws / name
        if dst.exists():
            kept.append(name)
        else:
            shutil.copy(src, dst)
            made.append(name)
    for d in ("runs", "cache", "email_import", "resume"):
        (ws / d).mkdir(exist_ok=True)
    print(json.dumps({"workspace": str(ws), "created": made, "already_there": kept}, indent=1))
    if made:
        print("\nNEXT: open Claude Code (or Codex) in this repo and say \"set me up\". The setup skill interviews you to fill "
              "inventory.md, then profile.yaml and resume.yaml.", file=sys.stderr)
    return 0


def cmd_doctor(a) -> int:
    import subprocess
    from .resume import find_chrome
    checks = []
    chrome = find_chrome()
    checks.append((f"Chrome/Chromium/Edge for PDF rendering ({chrome or 'not found; set CHROME_PATH'})", bool(chrome)))
    checks.append(("pdftotext (poppler)", bool(shutil.which("pdftotext"))))
    for mod in ("requests", "bs4", "yaml", "pytest"):
        try:
            __import__(mod)
            checks.append((f"python: {mod}", True))
        except ImportError:
            checks.append((f"python: {mod} (pip install -r requirements.txt)", False))
    try:
        n = len(resolve.load_registry())
        checks.append((f"company registry ({n} entries)", n > 0))
    except Exception as e:  # noqa: BLE001
        checks.append((f"company registry: {e}", False))
    ws = paths.workspace()
    for name in ("inventory.md", "profile.yaml", "resume.yaml"):
        checks.append((f"workspace/{name} (run `python3 -m jobhunt init`)" if not (ws / name).exists() else f"workspace/{name}",
                       (ws / name).exists()))
    try:
        load_profile()
        checks.append(("profile.yaml parses", True))
    except Exception as e:  # noqa: BLE001
        checks.append((f"profile.yaml: {e}", False))
    t = subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"], capture_output=True, text=True, cwd=ROOT)
    last = t.stdout.strip().splitlines()[-1] if t.stdout.strip() else t.stderr[:80]
    checks.append((f"tests: {last}", t.returncode == 0))
    for name, ok in checks:
        print(("OK   " if ok else "FAIL ") + name)
    for t in unfilled():
        print("TODO " + t)
    return 0 if all(ok for _, ok in checks) else 1


# ----------------------------------------------------------------------------- fetching
def _cfg_from_args(a) -> dict | None:
    if not getattr(a, "ats", None):
        return None
    cfg = {"name": a.company, "ats": a.ats}
    for k in ("token", "host", "tenant", "site", "region", "endpoint"):
        v = getattr(a, k, None)
        if v:
            cfg[k] = v
    return cfg


def fetch_company(company: str, cfgs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Every posting from every board a company has, de-duplicated. Returns (jobs, per-board sources)."""
    jobs, sources = [], []
    for cfg in cfgs:
        label = f"{cfg['ats']}:{cfg.get('token') or cfg.get('site') or cfg.get('host') or cfg.get('endpoint') or ''}"
        try:
            got = ats.fetch(cfg)
        except Exception as e:  # noqa: BLE001  (reported, never silently dropped)
            sources.append({"company": company, "source": label, "error": str(e)[:300]})
            continue
        for j in got:
            j["company"] = company
        sources.append({"company": company, "source": label, "count": len(got), "expected": cfg.get("open_jobs_at_check")})
        jobs.extend(got)
    seen, uniq = set(), []
    for j in jobs:
        k = (j["ats"], j["id"])
        if k not in seen:
            seen.add(k)
            uniq.append(j)
    return uniq, sources


def apply_first_seen(company: str, jobs: list[dict], had_previous_run: bool) -> None:
    """Remember when each posting was first seen; use it as the posting date when the ATS gives none."""
    path = paths.cache() / "first_seen" / f"{slugify(company)}.json"
    seen = json.loads(path.read_text()) if path.exists() else {}
    today = date.today().isoformat()
    for j in jobs:
        k = f"{j['ats']}:{j['id']}"
        seen.setdefault(k, today)
        if not j.get("posted_at") and (seen[k] < today or had_previous_run):
            j["posted_at"] = parse_date(seen[k])
            j["posted_at_source"] = "first seen by jobhunt" + (" (new since last run)" if seen[k] == today else "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen))


def earlier_runs(exclude: Path | None = None) -> list[Path]:
    """Every run folder with saved postings, newest first (company runs and sweeps alike)."""
    root = paths.runs()
    if not root.exists():
        return []
    out = []
    for d in root.iterdir():
        if not d.is_dir() or not (d / "meta.json").exists() or (exclude and d.resolve() == exclude.resolve()):
            continue
        try:
            stamp = json.loads((d / "meta.json").read_text()).get("fetched_at") or ""
        except ValueError:
            stamp = ""
        out.append((stamp, d.name, d))
    return [d for _, _, d in sorted(out, reverse=True)]


def run_companies(run_dir: Path) -> list[str]:
    try:
        meta = json.loads((run_dir / "meta.json").read_text())
    except (OSError, ValueError):
        return []
    return meta.get("companies") or ([meta["company"]] if meta.get("company") else [])


def _had_run(company: str, exclude: Path) -> bool:
    return any(any(tracker.same_company(c, company) for c in run_companies(d)) for d in earlier_runs(exclude))


# ----------------------------------------------------------------------------- stage 1: find / sweep
def cmd_find(a) -> int:
    """Stage 1 for one company: fetch everything, apply universal checks, prepare the AI screen."""
    _warn_if_unfilled()
    profile = load_profile()
    cfgs = [_cfg_from_args(a)] if getattr(a, "ats", None) else resolve.lookup(a.company)
    if not cfgs:
        print(f"'{a.company}' is not in data/companies.yaml. Probing public ATS APIs...", file=sys.stderr)
        hits = resolve.probe(a.company)
        print(json.dumps({"status": "unresolved", "probe_hits": hits}, indent=1))
        print("\nNEXT: confirm the right board (board_name must be this company; names collide across companies), then\n"
              "  python3 -m jobhunt register --name '<Company>' --ats <ats> --token <token>\n"
              "or find the careers page and run: python3 -m jobhunt detect <careers_url>", file=sys.stderr)
        return 2
    company = cfgs[0]["name"]
    run_dir = Path(a.out) if getattr(a, "out", None) else paths.runs() / f"{slugify(company)}-{date.today().isoformat()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {company} from {len(cfgs)} board(s) ...", file=sys.stderr)
    jobs, sources = fetch_company(company, cfgs)
    for s in sources:
        msg = f"  FAILED {s['source']}: {s['error']}" if s.get("error") else \
            f"  {s['source']}: {s['count']} postings" + (f" (registry saw {s['expected']} when verified)" if s.get("expected") else "")
        print(msg, file=sys.stderr)
    if not jobs:
        print(json.dumps({"status": "fetch_failed", "sources": sources}, indent=1))
        return 4
    apply_first_seen(company, jobs, _had_run(company, run_dir))
    meta = {"kind": "company", "company": company, "companies": [company], "label": company,
            "fetched_at": datetime.now().isoformat(timespec="seconds"), "sources": sources,
            "source": ", ".join(s["source"] for s in sources), "total_fetched": len(jobs),
            "per_company_fetched": {company: len(jobs)}}
    return start_run(run_dir, meta, jobs, profile)


def _select_sweep_companies(a) -> list[tuple[str, list[dict]]]:
    by_name: dict[str, list[dict]] = defaultdict(list)
    wanted = {resolve._norm(x) for x in (a.companies or "").split(",") if x.strip()}
    cats = [c.strip().lower() for c in (a.category or "").split(",") if c.strip()]
    for e in resolve.load_registry():
        if str(e.get("ats", "")).startswith("unsupported"):
            continue
        if wanted and resolve._norm(e["name"]) not in wanted and not any(resolve._norm(x) in wanted for x in e.get("aliases") or []):
            continue
        if cats and not any(c in str(e.get("category") or "").lower() for c in cats):
            continue
        by_name[e["name"]].append(e)
    items = sorted(by_name.items())
    return items[: a.limit] if a.limit else items


def cmd_sweep(a) -> int:
    """Stage 1 across many companies: fetch in parallel, keep postings in the regions asked for, universal checks,
    prepare the AI screen. Same next steps as `find`."""
    _warn_if_unfilled()
    profile = load_profile()
    valid = set(region_keys(profile))
    regions = [r.strip() for r in (a.regions or "").split(",") if r.strip()] or \
        [r["key"] for r in profile["regions"]] + ["remote_us"]
    bad = [r for r in regions if r not in valid]
    if bad:
        print(f"Unknown region keys {bad}. Yours are: {sorted(valid)} (profile.yaml `regions`).", file=sys.stderr)
        return 2
    items = _select_sweep_companies(a)
    if not items:
        print("No registry companies match that selection.", file=sys.stderr)
        return 2
    name = slugify(a.name or "-".join(regions[:2]))
    run_dir = Path(a.out) if a.out else paths.runs() / f"sweep-{name}-{date.today().isoformat()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Sweeping {len(items)} companies with {a.workers} workers; keeping regions {regions} ...", file=sys.stderr)
    jobs, sources, per_company = [], [], {}
    def work(item):
        return item[0], *fetch_company(*item)
    if a.workers <= 1:
        results = (work(i) for i in items)
    else:
        pool = ThreadPoolExecutor(max_workers=a.workers)
        results = (f.result() for f in as_completed([pool.submit(work, i) for i in items]))
    done = 0
    for company, got, src in results:
        done += 1
        sources += src
        per_company[company] = len(got)
        if got:
            apply_first_seen(company, got, _had_run(company, run_dir))
            jobs.extend(got)
        if done % 25 == 0 or done == len(items):
            print(f"  {done}/{len(items)} companies, {len(jobs)} postings so far", file=sys.stderr)
    kept, outside = region_prefilter(jobs, regions, profile)
    errors = [s for s in sources if s.get("error")]
    meta = {"kind": "sweep", "company": None, "companies": sorted({j["company"] for j in kept}),
            "label": f"Sweep: {', '.join(regions)}", "regions": regions,
            "fetched_at": datetime.now().isoformat(timespec="seconds"), "sources": sources,
            "source": f"{len(items)} companies' own hiring systems", "total_fetched": len(jobs),
            "in_regions": len(kept), "outside_regions": len(outside), "per_company_fetched": per_company,
            "fetch_errors": len(errors)}
    (run_dir / "fetch_errors.json").write_text(json.dumps(errors, indent=1))
    print(f"  {len(jobs)} postings fetched; {len(kept)} have a location in {regions} or need a closer look; "
          f"{len(errors)} board(s) failed (see fetch_errors.json)", file=sys.stderr)
    return start_run(run_dir, meta, kept, profile)


_N_LOCATIONS = re.compile(r"^\s*\d+\s+locations?\s*$", re.I)


def region_prefilter(jobs: list[dict], regions: list[str], profile: dict) -> tuple[list[dict], list[dict]]:
    """Keep postings with a location in `regions`, plus ones whose location can't be judged yet: no location,
    "3 Locations" (Workday lists multi-site postings that way until the detail page is read), or a string that
    matches one of your regions' broad patterns but no known place (the location screener decides those)."""
    lcache = screen.load_locations()
    want = set(regions)
    kept, out = [], []
    for j in jobs:
        locs = [l for l in (j.get("locations") or []) if l and l.strip()]
        if not locs or any(_N_LOCATIONS.match(l) for l in locs):
            j["region_pending"] = True
            if locs and not j.get("needs_detail"):
                j["needs_detail"] = True
            kept.append(j)
            continue
        reg = screen.region_for(j, lcache, profile)
        if set(reg["all"]) & want:
            kept.append(j)
        elif any(l.strip() not in lcache and screen.needs_location_screen(l, profile) for l in locs):
            j["region_pending"] = True
            kept.append(j)
        else:
            out.append(j)
    return kept, out


def screening_pool(survivors: list[dict], profile: dict, regions_wanted: list[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Jobs whose description is already in hand get the evidence-based checks (years, clearance, PhD) before
    screening; jobs that still need a detail fetch are screened by title first."""
    have = [j for j in survivors if not j.get("needs_detail")]
    later = [j for j in survivors if j.get("needs_detail")]
    passed, out = triage.run_description_filters(have, profile, regions_wanted)
    return passed + later, out


def start_run(run_dir: Path, meta: dict, all_jobs: list[dict], profile: dict) -> int:
    survivors, _ = triage.run_title_filters(all_jobs, profile)
    pool, _ = screening_pool(survivors, profile, meta.get("regions"))
    (run_dir / "jobs_all.json").write_text(json.dumps(all_jobs, default=str))
    locs = None
    if meta.get("kind") == "sweep":  # only strings from postings that survived; the rest were judged by the regex hint
        locs = [l for j in pool for l in (j.get("locations") or [])]
    info = screen.write_screen_inputs(run_dir, pool, profile, locs)
    meta.update({"after_title_checks": len(survivors), "after_evidence_checks": len(pool), "screen": info})
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    if info["titles_pending"] or info["locations_pending"]:
        print(json.dumps({"status": "screen_needed", "label": meta["label"], "total_fetched": meta["total_fetched"],
                          "after_title_checks": len(survivors), "to_screen_jobs": len(pool), **info,
                          "run_dir": str(run_dir)}, indent=1))
        print(f"\nNEXT: screen {info['titles_pending']} new titles and {info['locations_pending']} new location strings. "
              f"One subagent per {run_dir}/screen/titles_XX.md writes screen/screen_XX.txt following "
              f"jobhunt/rubrics/SCREEN_RUBRIC.md and screen/BRIEF.md (the first one also classifies screen/locations.md). "
              f"Then run:\n  python3 -m jobhunt screen-apply {run_dir}", file=sys.stderr)
        return 3
    return finish_run(run_dir, profile)


# ----------------------------------------------------------------------------- stage 2: screen-apply
def cmd_screen_prep(a) -> int:
    run_dir = Path(a.run_dir)
    meta = json.loads((run_dir / "meta.json").read_text())
    profile = load_profile()
    all_jobs = json.loads((run_dir / "jobs_all.json").read_text())
    survivors, _ = triage.run_title_filters(all_jobs, profile)
    pool, _ = screening_pool(survivors, profile, meta.get("regions"))
    locs = [l for j in pool for l in (j.get("locations") or [])] if meta.get("kind") == "sweep" else None
    info = screen.write_screen_inputs(run_dir, pool, profile, locs)
    meta["screen"] = info
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(info, indent=1))
    return 0


def cmd_screen_apply(a) -> int:
    run_dir = Path(a.run_dir)
    profile = load_profile()
    res = screen.apply_screen(run_dir, profile)
    print(json.dumps(res), file=sys.stderr)
    return finish_run(run_dir, profile)


def finish_run(run_dir: Path, profile: dict) -> int:
    """Apply screen decisions, fetch descriptions for kept jobs, evidence-based checks, review packets."""
    meta = json.loads((run_dir / "meta.json").read_text())
    regions_wanted = meta.get("regions")
    all_jobs = json.loads((run_dir / "jobs_all.json").read_text())
    survivors, title_out = triage.run_title_filters(all_jobs, profile)
    pool, early_out = screening_pool(survivors, profile, regions_wanted)
    title_out = title_out + early_out
    caches: dict[str, dict] = {}
    kept, screened_out, unscreened = [], [], 0
    for j in pool:
        if j["company"] not in caches:
            caches[j["company"]] = screen.load_title_cache(j["company"])
        dec = caches[j["company"]].get(screen.norm_title(j["title"]))
        if dec is None:
            unscreened += 1
            dec = {"keep": True, "family": "software", "reason": "not screened; kept by default"}
        j["screen"] = dec
        if dec["keep"]:
            kept.append(j)
        else:
            j["exclude_reasons"] = ["screened_out"]
            screened_out.append(j)
    need = [j for j in kept if j.get("needs_detail")]
    if need:
        print(f"Fetching full descriptions for {len(need)} screened-in postings ...", file=sys.stderr)
        n = ats.fill_details(need)
        print(f"  filled {n}/{len(need)}", file=sys.stderr)
        for j in need:
            if j.get("needs_detail"):  # the detail fetch failed: judge it on what we have rather than lose it
                j["detail_failed"] = True
                j["needs_detail"] = False
    candidates, desc_out = triage.run_description_filters(kept, profile, regions_wanted)
    excluded = title_out + screened_out + desc_out
    triage.assign_keys(candidates)
    triage.write_triage_outputs(run_dir, meta["label"], all_jobs, candidates, excluded, meta.get("total_fetched"))
    carried = carry_over_fits(run_dir, candidates)
    to_review = [j for j in candidates if (j["company"], str(j["id"])) not in carried]
    packets = triage.write_review_packets(run_dir, to_review, all_jobs)
    prev = previous_ids(run_dir, sorted({j["company"] for j in candidates}))
    newly_posted = [j for j in candidates if j["company"] in prev and (j["company"], str(j["id"])) not in prev[j["company"]]]
    (run_dir / "jobs_all.json").write_text(json.dumps(all_jobs, default=str))
    meta.update({
        "candidates": len(candidates),
        "excluded": len(excluded),
        "screened_out": len(screened_out),
        "unscreened_kept_by_default": unscreened,
        "detail_fetch_failed": sum(1 for j in need if j.get("detail_failed")),
        "review_batches": [p.name for p in packets],
        "reviews_carried_over": len(carried),
        "new_since_last_run": [{"company": j["company"], "id": j["id"], "title": j["title"]} for j in newly_posted] if prev else None,
    })
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    summary = {k: meta.get(k) for k in ("label", "total_fetched", "after_title_checks", "after_evidence_checks", "screened_out",
                                        "candidates", "excluded", "review_batches", "reviews_carried_over",
                                        "unscreened_kept_by_default", "detail_fetch_failed")}
    if meta["new_since_last_run"] is not None:
        summary["new_candidates_since_last_run"] = len(meta["new_since_last_run"])
    print(json.dumps(summary, indent=1))
    if packets:
        print(f"\nNEXT: one reviewer per two or three files in {run_dir}/review/ writes {run_dir}/fit/<same name>.json. "
              f"Reviewers read {paths.rubrics() / 'REVIEW_RUBRIC.md'}, {paths.inventory()} and {run_dir / 'screen' / 'BRIEF.md'}. "
              f"Then:\n  python3 -m jobhunt rank {run_dir}", file=sys.stderr)
    print(f"\nRun folder: {run_dir}", file=sys.stderr)
    return 0


def _desc_key(job: dict) -> str:
    return hashlib.md5((job.get("description") or "")[:6000].encode()).hexdigest()


def _fit_rows(fp: Path) -> list[dict]:
    data = json.loads(fp.read_text())
    rows = data if isinstance(data, list) else data.get("jobs", [])
    return [r for r in rows if isinstance(r, dict)]


def carry_over_fits(run_dir: Path, candidates: list[dict]) -> set:
    """Copy reviewer rows from earlier runs (company runs or sweeps) for postings whose text hasn't changed.
    Returns the (company, id) pairs that need no new review."""
    by_cid = {(j["company"], str(j["id"])): j for j in candidates}
    by_key = {j["key"]: j for j in candidates}
    reviewed_here = set()  # same-day re-run: reviews already sitting in this run folder
    for fp in sorted((run_dir / "fit").glob("*.json")):
        if fp.name == "carried_over.json":
            continue
        for row in _fit_rows(fp):
            j = by_key.get(row.get("key"))
            if j and str(row.get("id")) == str(j["id"]):
                reviewed_here.add((j["company"], str(j["id"])))
    found: dict = {}
    companies = {j["company"] for j in candidates}
    for old in earlier_runs(run_dir):
        if not set(run_companies(old)) & companies or not (old / "candidates.json").exists():
            continue
        old_cands = {j.get("key"): j for j in json.loads((old / "candidates.json").read_text())}
        for fp in sorted((old / "fit").glob("*.json")):
            for row in _fit_rows(fp):
                oj = old_cands.get(row.get("key"))
                if not oj or str(oj.get("id")) != str(row.get("id")):
                    continue
                cid = (oj.get("company"), str(oj["id"]))
                new = by_cid.get(cid)
                if new and cid not in found and cid not in reviewed_here and _desc_key(oj) == _desc_key(new):
                    found[cid] = dict(row, key=new["key"], carried_from=old.name)
    if found:
        (run_dir / "fit").mkdir(exist_ok=True)
        (run_dir / "fit" / "carried_over.json").write_text(json.dumps(list(found.values()), indent=1))
    return set(found) | reviewed_here


def previous_ids(run_dir: Path, companies: list[str]) -> dict:
    """For each company with an earlier run: the (company, id) pairs that run's candidates held."""
    out: dict = {}
    for old in earlier_runs(run_dir):
        p = old / "candidates.json"
        if not p.exists():
            continue
        cos = [c for c in companies if c not in out and c in run_companies(old)]
        if not cos:
            continue
        ids = {(j.get("company"), str(j.get("id"))) for j in json.loads(p.read_text())}
        for c in cos:
            out[c] = {x for x in ids if x[0] == c}
    return out


# ----------------------------------------------------------------------------- stage 3: rank / list / resume
def cmd_rank(a) -> int:
    run_dir = Path(a.run_dir)
    ranked = rank.rank_and_report(run_dir, load_profile(), resume=a.resume,
                                  advice=Path(a.advice_file).read_text() if a.advice_file else None)
    tiers: dict = {}
    for j in ranked:
        tiers[j["rank"]["tier"]] = tiers.get(j["rank"]["tier"], 0) + 1
    print(json.dumps({"ranked": len(ranked), "tiers": tiers, "report": str(run_dir / "REPORT.md")}, indent=1))
    return 0


def cmd_list(a) -> int:
    from . import applylist
    print(json.dumps(applylist.build(load_profile(), rerank=not a.no_rank), indent=1))
    return 0


def cmd_resume(a) -> int:
    from . import resume
    import yaml
    src = Path(a.yaml) if a.yaml else paths.resume_yaml()
    data = yaml.safe_load(src.read_text())
    variants = list((data.get("variants") or {}).keys()) or [data.get("default_variant", "general")]
    todo = variants if a.all else [a.variant or data.get("default_variant", variants[0])]
    stem = resume.pdf_name(data)
    ok = True
    for v in todo:
        out = Path(a.out) if (a.out and not a.all) else paths.resume_dir() / v / stem
        rep = resume.build(src, out, v, emphasize=[x for x in (a.emphasize or "").split(",") if x.strip()], wording=a.wording)
        print(json.dumps(rep, indent=1))
        ok = ok and rep["status"] == "ok" and not rep.get("lint") and not rep.get("short_last_lines")
    return 0 if ok else 1


# ----------------------------------------------------------------------------- watch / fresh
def cmd_watch(a) -> int:
    from .watch import run_watch
    run_watch(load_profile(), a.companies or None)
    return 0


def cmd_fresh(a) -> int:
    from . import watch
    if a.action == "list":
        print(json.dumps(watch.fresh(a.days, a.companies or None), indent=1))
    elif a.action == "show":
        if len(a.companies) != 2:
            print("usage: jobhunt fresh show <company> <id>", file=sys.stderr)
            return 2
        print(watch.show(a.companies[0], a.companies[1]))
    elif a.action == "mark":
        print(json.dumps({"reviewed_total": watch.mark(a.companies)}))
    return 0


# ----------------------------------------------------------------------------- registry
def cmd_resolve(a) -> int:
    hits = resolve.lookup(a.company)
    if hits:
        print(json.dumps({"status": "registry", "entries": hits}, indent=1, default=str))
        return 0
    print(json.dumps({"status": "probe", "hits": resolve.probe(a.company)}, indent=1))
    return 0


def cmd_detect(a) -> int:
    print(json.dumps(resolve.detect_from_url(a.url), indent=1))
    return 0


def cmd_register(a) -> int:
    entry = {"name": a.name, "aliases": [x.strip() for x in (a.aliases or "").split(",") if x.strip()], "ats": a.ats}
    for k in ("token", "host", "tenant", "site", "region", "endpoint", "careers_url", "notes", "category"):
        v = getattr(a, k, None)
        if v:
            entry[k] = v
    entry["verified"] = date.today().isoformat()
    resolve.save_entry(entry)
    print(json.dumps(entry, indent=1))
    return 0


# ----------------------------------------------------------------------------- application history
def cmd_applied(a) -> int:
    if a.action == "import-email":
        from .email_import import run
        print(json.dumps(run(Path(a.path) if a.path else None), indent=1))
        return 0
    if a.action == "stats":
        from collections import Counter
        rows = tracker.load()
        st = Counter((r.get("status") or "applied") for r in rows)
        interviewed = [r for r in rows if (r.get("status") or "") in ("screen", "interview", "interviewing", "onsite", "offer")
                       or "after interviews" in (r.get("notes") or "")]
        assessed = [r for r in rows if r.get("status") == "assessment"]
        total = len(rows)
        print(f"Applications on record: {total}  |  reached a human interview: {len(interviewed)}"
              + (f"  ({100 * len(interviewed) / total:.1f}%)" if total else "")
              + f"  |  automated assessment only: {len(assessed)}")
        for r in interviewed:
            print(f"  interview: {r['company']} — {r['title']} (applied {r['date_applied']}, now {r['status']})")
        print("By status:", dict(st))
        for field in ("resume", "source", "company"):
            c = Counter((r.get(field) or "-") for r in rows)
            print(f"By {field}:", dict(c.most_common(12)))
        print("Statuses to use when logging outcomes: applied, rejected, screen, interview, onsite, offer, withdrawn")
        return 0
    if a.action == "add":
        if not a.company or not a.title:
            print("applied add needs --company and --title", file=sys.stderr)
            return 2
        if a.when and not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", a.when):
            print("--when must be YYYY-MM-DD (or YYYY-MM)", file=sys.stderr)
            return 2
        row = tracker.add(a.company, a.title, job_id=a.job_id or "", url=a.url or "", location=a.location or "",
                          status=a.status, source=a.source, resume=a.resume or "", notes=a.notes or "", when=a.when)
        print(json.dumps(row, indent=1))
        return 0
    rows = tracker.load()
    if a.company:
        rows = [r for r in rows if tracker.same_company(r.get("company"), a.company)]
    for r in rows:
        print(f"{r['date_applied']}  {r['company']:<22} {r['status']:<10} {r['title']}  {r.get('url', '')}")
    print(f"({len(rows)} rows)", file=sys.stderr)
    return 0


def cmd_privacy(a) -> int:
    from .privacy import run
    return run(a.terms)


# ----------------------------------------------------------------------------- argparse
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="jobhunt", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create workspace/ from templates/ (never overwrites)").set_defaults(fn=cmd_init)
    sub.add_parser("doctor", help="check that this machine has everything the workflow needs").set_defaults(fn=cmd_doctor)

    f = sub.add_parser("find", help="fetch ALL jobs for a company and prepare the screen")
    f.add_argument("company")
    for k in ("ats", "token", "host", "tenant", "site", "region", "endpoint", "out"):
        f.add_argument(f"--{k}")
    f.set_defaults(fn=cmd_find)

    sw = sub.add_parser("sweep", help="fetch many registry companies at once and keep postings in your regions")
    sw.add_argument("--regions", help="comma-separated region keys from profile.yaml (default: all yours + remote_us)")
    sw.add_argument("--companies", help="comma-separated names (default: every supported registry company)")
    sw.add_argument("--category", help="registry category words to keep, e.g. 'robotics,space'")
    sw.add_argument("--name", help="short name for the run folder")
    sw.add_argument("--workers", type=int, default=12)
    sw.add_argument("--limit", type=int, help="only the first N companies (for a quick trial)")
    sw.add_argument("--out")
    sw.set_defaults(fn=cmd_sweep)

    sp = sub.add_parser("screen-prep", help="rebuild screen inputs from a run's saved jobs (no refetch)")
    sp.add_argument("run_dir")
    sp.set_defaults(fn=cmd_screen_prep)

    sa = sub.add_parser("screen-apply", help="apply screen/screen_XX.(txt|json) decisions and build review packets")
    sa.add_argument("run_dir")
    sa.set_defaults(fn=cmd_screen_apply)

    r = sub.add_parser("rank", help="score candidates using fit/*.json and write the report")
    r.add_argument("run_dir")
    r.add_argument("--resume", help="resume to name in the report")
    r.add_argument("--advice-file", help="markdown file with run-specific advice for the top of the report")
    r.set_defaults(fn=cmd_rank)

    li = sub.add_parser("list", help="APPLY_LIST.md and apply_list.html: every role worth sending, in order")
    li.add_argument("--no-rank", action="store_true", help="use rankings on disk instead of re-scoring each run")
    li.set_defaults(fn=cmd_list)

    rs = sub.add_parser("resume", help="build the one-page resume PDF and run every check")
    rs.add_argument("--variant")
    rs.add_argument("--all", action="store_true", help="build every variant")
    rs.add_argument("--yaml", help="resume source (default workspace/resume.yaml)")
    rs.add_argument("--out", help="output PDF (default workspace/resume/<variant>/<Name>_Resume.pdf)")
    rs.add_argument("--emphasize", help="skills from a posting to move first in the skills lines (reorder only)")
    rs.add_argument("--wording", help="use the named alternative text for bullets that define one under `alt:`")
    rs.set_defaults(fn=cmd_resume)

    w = sub.add_parser("watch", help="postings new since the last check at watchlist.yaml companies (no model calls)")
    w.add_argument("companies", nargs="*", help="override watchlist.yaml")
    w.set_defaults(fn=cmd_watch)

    fr = sub.add_parser("fresh", help="postings first published in the last N days at watchlist companies")
    fr.add_argument("action", choices=["list", "show", "mark"])
    fr.add_argument("companies", nargs="*", help="list: companies (default watchlist); show: <company> <id>; mark: ids")
    fr.add_argument("--days", type=int, default=8)
    fr.set_defaults(fn=cmd_fresh)

    s = sub.add_parser("resolve", help="registry entry for a company, or probe public ATS APIs")
    s.add_argument("company")
    s.set_defaults(fn=cmd_resolve)

    d = sub.add_parser("detect", help="work out a careers page's applicant tracking system")
    d.add_argument("url")
    d.set_defaults(fn=cmd_detect)

    g = sub.add_parser("register", help="add or replace a company in data/companies.yaml")
    g.add_argument("--name", required=True)
    g.add_argument("--aliases")
    g.add_argument("--ats", required=True)
    for k in ("token", "host", "tenant", "site", "region", "endpoint", "careers_url", "notes", "category"):
        g.add_argument(f"--{k.replace('_', '-')}", dest=k)
    g.set_defaults(fn=cmd_register)

    ap = sub.add_parser("applied", help="your application record (applications.csv)")
    ap.add_argument("action", choices=["add", "list", "stats", "import-email"])
    ap.add_argument("path", nargs="?", help="folder of event files for import-email")
    ap.add_argument("--company")
    ap.add_argument("--title")
    ap.add_argument("--job-id")
    ap.add_argument("--url")
    ap.add_argument("--location")
    ap.add_argument("--status", default="applied")
    ap.add_argument("--source", default="manual")
    ap.add_argument("--resume")
    ap.add_argument("--notes")
    ap.add_argument("--when")
    ap.set_defaults(fn=cmd_applied)

    pc = sub.add_parser("privacy-check", help="scan tracked repo files for your personal terms (workspace/privacy_terms.txt)")
    pc.add_argument("--terms", help="file of terms, one per line (default workspace/privacy_terms.txt)")
    pc.set_defaults(fn=cmd_privacy)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
