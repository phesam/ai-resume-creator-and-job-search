"""Catch new postings early at the companies you care most about (workspace/watchlist.yaml).

Applications in a posting's first week are the likeliest to be read: Ashby's data shows 2.5-3x as many applications
arrive in week one as in any later week, and recruiters review as they come in. Some employers say it outright
(one told the case-study candidate that replies are most likely within a week of posting).

  python3 -m jobhunt watch [company ...]             # postings not seen in any earlier check (no model calls)
  python3 -m jobhunt fresh list [--days 8] [company ...]   # first published in the last N days, not yet reviewed
  python3 -m jobhunt fresh show <company> <id>       # one posting in full, with its required form questions
  python3 -m jobhunt fresh mark <id> [<id> ...]      # record postings as reviewed so `fresh list` skips them

`watch` depends on what earlier checks saw; `fresh` asks for every open posting and uses the hiring system's own
publish date, so a posting missed one day still shows up the next. Both write nothing to your apply list: an agent
(the watch skill) reads the new postings, decides eligibility and adds the good ones to picks.yaml.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

from . import ats, paths, resolve, screen, triage
from .common import days_since, slugify


def watchlist() -> list[str]:
    p = paths.watchlist()
    return list((yaml.safe_load(p.read_text()) or {}).get("companies") or []) if p.exists() else []


def _fetch(name: str) -> tuple[str, list[dict], list[str]]:
    cfgs = resolve.lookup(name)
    if not cfgs:
        raise LookupError(f"{name} is not in data/companies.yaml. Find its board with `python3 -m jobhunt resolve \"{name}\"` "
                          f"(or `detect <careers-url>`), then add it with `python3 -m jobhunt register`.")
    company = cfgs[0]["name"]
    jobs, errors, keys = [], [], set()
    for cfg in cfgs:
        try:
            for j in ats.fetch(cfg):
                if (j["ats"], j["id"]) not in keys:
                    keys.add((j["ats"], j["id"]))
                    j["company"] = company
                    jobs.append(j)
        except Exception as e:  # noqa: BLE001  keep going; report it
            errors.append(f"{cfg['ats']}: {str(e)[:160]}")
    return company, jobs, errors


def run_watch(profile: dict, names: list[str] | None = None) -> Path:
    names = names or watchlist()
    seen_dir = paths.cache() / "seen"
    lines = [f"# New postings — {date.today().isoformat()}", "",
             "Only postings not seen in any earlier check. ★ = title already screened as worth reading for you; "
             "? = title not screened yet (run find-jobs on that company to screen and rank it).", ""]
    totals = {"new_relevant": 0, "new_unscreened": 0, "errors": 0}
    for name in names:
        try:
            company, jobs, errors = _fetch(name)
        except LookupError as e:
            lines += [f"## {name}", "", str(e), ""]
            continue
        seen_path = seen_dir / f"{slugify(company)}.json"
        first_time = not seen_path.exists()
        seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
        survivors, _ = triage.run_title_filters(jobs, profile)
        tcache = screen.load_title_cache(company)
        new_rel, new_unscr = [], []
        for j in survivors:
            if j["id"] in seen:
                continue
            dec = tcache.get(screen.norm_title(j["title"]))
            if dec is None:
                new_unscr.append(j)
            elif dec.get("keep"):
                new_rel.append(j)
        seen |= {j["id"] for j in jobs}
        seen_dir.mkdir(parents=True, exist_ok=True)
        seen_path.write_text(json.dumps(sorted(seen)))
        lines.append(f"## {company} — {len(jobs)} open")
        if errors:
            totals["errors"] += 1
            lines.append(f"⚠ fetch problems (this list may be incomplete): {'; '.join(errors)}")
        if first_time:
            lines += ["First check: baseline recorded; later checks list only new postings.", ""]
            continue
        lines.append("")
        for j in sorted(new_rel, key=lambda x: x.get("posted_at") or "", reverse=True):
            age = days_since(j.get("posted_at"))
            lines.append(f"- ★ [{j['title']}]({j['url']}) — {'; '.join(j.get('locations') or [])[:80]} · "
                         f"{'posted ' + str(age) + ' days ago' if age is not None else 'new today'}")
        for j in new_unscr[:40]:
            lines.append(f"- ? [{j['title']}]({j['url']}) — {'; '.join(j.get('locations') or [])[:80]}")
        if len(new_unscr) > 40:
            lines.append(f"- … and {len(new_unscr) - 40} more unscreened new titles")
        if not new_rel and not new_unscr:
            lines.append("No new relevant postings.")
        lines.append("")
        totals["new_relevant"] += len(new_rel)
        totals["new_unscreened"] += len(new_unscr)
    paths.runs().mkdir(parents=True, exist_ok=True)
    out = paths.runs() / f"watch-{date.today().isoformat()}.md"
    out.write_text("\n".join(lines) + "\n")
    print(json.dumps({"digest": str(out), **totals}), file=sys.stdout)
    return out


# ----------------------------------------------------------------------------- fresh postings
def _reviewed_path() -> Path:
    return paths.cache() / "fresh_reviewed.json"


def reviewed() -> set[str]:
    p = _reviewed_path()
    return set(json.loads(p.read_text())) if p.exists() else set()


def mark(ids: list[str]) -> int:
    done = reviewed() | {str(i) for i in ids}
    _reviewed_path().parent.mkdir(parents=True, exist_ok=True)
    _reviewed_path().write_text(json.dumps(sorted(done)))
    return len(done)


def fresh(days: int = 8, names: list[str] | None = None) -> dict:
    """Postings first published in the last `days` days that were not marked reviewed. A company that could not
    be fetched is listed under `errors`, never reported as having nothing new."""
    cut = (date.today() - timedelta(days=days)).isoformat()
    done, out, errors, no_dates = reviewed(), [], {}, []
    for name in names or watchlist():
        try:
            company, jobs, errs = _fetch(name)
        except LookupError as e:
            errors[name] = str(e)
            continue
        if errs:
            errors[company] = "; ".join(errs)
        dated = [j for j in jobs if j.get("posted_at")]
        if jobs and not dated:
            no_dates.append(company)  # this hiring system gives no dates; `watch` is the tool for it
        for j in dated:
            if j["posted_at"][:10] >= cut and str(j["id"]) not in done:
                out.append({"company": company, "id": str(j["id"]), "title": j["title"], "url": j["url"],
                            "locations": j.get("locations") or [], "published": j["posted_at"][:10]})
    out.sort(key=lambda p: (p["company"], p["published"]))
    return {"since": cut, "new": out, "errors": errors, "no_publish_dates": no_dates}


def show(name: str, job_id: str) -> str:
    """One posting in full: locations, dates, pay, description and (where the hiring system exposes them) the
    required application-form questions, which are often the real filter (years, a language, clearance)."""
    from .forms import form_questions
    company, jobs, _ = _fetch(name)
    job = next((j for j in jobs if str(j["id"]) == str(job_id)), None)
    if not job:
        return f"{company}: no open posting with id {job_id} (it may have closed)."
    if job.get("needs_detail"):
        ats.fill_details([job])
    cfg = next((c for c in resolve.lookup(name) if c.get("ats") == job["ats"]), {})
    questions = form_questions(job, cfg)
    q = "\n".join(f"- {x}" for x in questions) if questions else (
        "(this hiring system does not publish its form; open the application to see the questions)" if questions is None else "(none)")
    return (f"{job['title']} — {company}\nURL: {job['url']}\nLocations: {'; '.join(job.get('locations') or [])}\n"
            f"Published: {(job.get('posted_at') or '?')[:10]} ({job.get('posted_at_source') or '?'})\n"
            f"Pay: {job.get('salary_text') or '-'}\n\n{job.get('description') or '(no description)'}\n\n"
            f"Required form questions:\n{q}")
