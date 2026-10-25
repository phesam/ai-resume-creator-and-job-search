"""ATS adapters. Each `fetch_<ats>(cfg)` returns ALL open postings as normalized job dicts.

Adapters that cannot get full descriptions in the listing call (Workday, SmartRecruiters,
Workable) mark jobs with `needs_detail=True`; `fill_details()` fetches those on demand,
so we only pay for detail requests on jobs that survive title triage.
"""

from __future__ import annotations

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from .common import get_json, html_to_text, http, make_job, parse_date, post_json


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- Greenhouse
def fetch_greenhouse(cfg: dict) -> list[dict]:
    token = cfg["token"]
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true", timeout=120)
    jobs = []
    for j in data.get("jobs", []):
        meta = {m.get("name"): m.get("value") for m in j.get("metadata") or [] if m.get("name")}
        depts = [d.get("name", "").strip() for d in j.get("departments") or []]
        offices = [o.get("location") or o.get("name") for o in j.get("offices") or []]
        loc_name = (j.get("location") or {}).get("name") or ""
        locations = [l.strip() for l in loc_name.split(";") if l.strip()] or [o for o in offices if o]
        first = j.get("first_published")
        jobs.append(
            make_job(
                company=j.get("company_name") or cfg.get("name"),
                ats="greenhouse",
                id=str(j.get("id")),
                title=j.get("title", ""),
                url=j.get("absolute_url"),
                locations=locations,
                remote=True if re.search(r"\bremote\b", loc_name, re.I) else None,
                department=meta.get("External Department Name for Job Board") or (depts[0] if depts else None),
                team=" / ".join(depts) if depts else None,
                employment_type=meta.get("Employment Type") or meta.get("Employment type"),
                posted_at=parse_date(first) or parse_date(j.get("updated_at")),
                posted_at_source="first_published" if first else "updated_at",
                updated_at=parse_date(j.get("updated_at")),
                description=html_to_text(j.get("content")),
                requisition_id=j.get("requisition_id"),
                extra={k: v for k, v in meta.items() if v not in (None, "", [])},
            )
        )
    return jobs


# --------------------------------------------------------------------------- Lever
def fetch_lever(cfg: dict) -> list[dict]:
    slug = cfg["token"]
    base = "https://api.eu.lever.co" if cfg.get("region") == "eu" else "https://api.lever.co"
    out, skip = [], 0
    while True:
        page = get_json(f"{base}/v0/postings/{slug}?mode=json&skip={skip}&limit=250", timeout=60)
        if not page:
            break
        out.extend(page)
        if len(page) < 250:
            break
        skip += 250
    jobs = []
    for p in out:
        cats = p.get("categories") or {}
        locs = cats.get("allLocations") or ([cats["location"]] if cats.get("location") else [])
        parts = [p.get("descriptionPlain") or html_to_text(p.get("description"))]
        for lst in p.get("lists") or []:
            parts.append(f"\n{lst.get('text', '')}\n" + html_to_text(lst.get("content")))
        parts.append(p.get("additionalPlain") or html_to_text(p.get("additional")))
        sal = p.get("salaryRange") or {}
        sal_text = None
        if sal.get("min") or sal.get("max"):
            sal_text = f"{sal.get('currency', '')} {sal.get('min')} - {sal.get('max')} {sal.get('interval', '')}".strip()
        wt = (p.get("workplaceType") or "").lower() or None
        jobs.append(
            make_job(
                company=cfg.get("name"),
                ats="lever",
                id=p.get("id"),
                title=p.get("text", ""),
                url=p.get("hostedUrl") or p.get("applyUrl"),
                locations=locs,
                remote=True if wt == "remote" else (False if wt in ("onsite", "on-site") else None),
                workplace_type=wt,
                department=cats.get("department"),
                team=cats.get("team"),
                employment_type=cats.get("commitment"),
                posted_at=parse_date(p.get("createdAt")),
                posted_at_source="createdAt",
                salary_text=sal_text,
                description="\n".join(x for x in parts if x).strip(),
            )
        )
    return jobs


# --------------------------------------------------------------------------- Ashby
def fetch_ashby(cfg: dict) -> list[dict]:
    org = cfg["token"]
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true", timeout=60)
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location")] + [s.get("location") for s in j.get("secondaryLocations") or []]
        comp = j.get("compensation") or {}
        wt = (j.get("workplaceType") or "").lower() or None
        jobs.append(
            make_job(
                company=cfg.get("name"),
                ats="ashby",
                id=j.get("id"),
                title=j.get("title", ""),
                url=j.get("jobUrl") or j.get("applyUrl"),
                locations=[l for l in locs if l],
                remote=bool(j.get("isRemote")) if j.get("isRemote") is not None else None,
                workplace_type=wt,
                department=j.get("department"),
                team=j.get("team"),
                employment_type=j.get("employmentType"),
                posted_at=parse_date(j.get("publishedAt")),
                posted_at_source="publishedAt",
                salary_text=comp.get("compensationTierSummary") or comp.get("scrapeableCompensationSalarySummary"),
                description=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            )
        )
    return jobs


# --------------------------------------------------------------------------- Workday
_WD_REL = re.compile(r"posted\s+(today|yesterday|(\d+)\+?\s+days?\s+ago)", re.I)


def _workday_relative(text: str | None) -> tuple[str | None, str]:
    """'Posted 3 Days Ago' -> approximate ISO date. '30+ Days Ago' is a lower bound."""
    if not text:
        return None, "unknown"
    m = _WD_REL.search(text)
    if not m:
        return None, "unknown"
    now = datetime.now(timezone.utc)
    word = m.group(1).lower()
    if word == "today":
        days = 0
    elif word == "yesterday":
        days = 1
    else:
        days = int(m.group(2))
    src = "postedOn(30+ lower bound)" if "+" in text else "postedOn(relative)"
    return (now - timedelta(days=days)).isoformat(), src


def _workday_page(base: str, offset: int, facets: dict, search: str = "") -> dict:
    payload = {"appliedFacets": facets, "limit": 20, "offset": offset, "searchText": search}
    return post_json(f"{base}/jobs", payload, timeout=45)


def _workday_collect(base: str, facets: dict) -> tuple[dict, int]:
    """Page through one facet combination. Returns ({externalPath: posting}, reported_total)."""
    first = _workday_page(base, 0, facets)
    total = first.get("total") or 0
    found = {p["externalPath"]: p for p in first.get("jobPostings", []) if p.get("externalPath")}
    offset = 20
    empty_streak = 0
    while offset < total and empty_streak < 2:
        try:
            page = _workday_page(base, offset, facets)
        except Exception as e:  # some tenants 400 past a cap
            log(f"  workday page offset={offset} failed: {e}")
            break
        posts = page.get("jobPostings", [])
        if not posts:
            empty_streak += 1
        for p in posts:
            if p.get("externalPath"):
                found[p["externalPath"]] = p
        offset += 20
        time.sleep(0.15)
    return found, total


def fetch_workday(cfg: dict) -> list[dict]:
    host, tenant, site = cfg["host"], cfg["tenant"], cfg["site"]
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    found, total = _workday_collect(base, {})
    log(f"  workday: total reported {total}, collected {len(found)}")
    capped = total == 2000  # some tenants report at most 2000; the true count is larger
    if total and (len(found) < total * 0.98 or capped):
        # Listing cap hit: partition by a facet whose buckets are each under the cap.
        first = _workday_page(base, 0, {})
        for facet in first.get("facets", []):
            param, values = facet.get("facetParameter"), facet.get("values") or []
            if values and values[0].get("facetParameter"):  # nested (e.g. locations)
                param, values = values[0]["facetParameter"], values[0].get("values") or []
            if not param or len(values) < 2:
                continue
            log(f"  workday: partitioning by facet '{param}' ({len(values)} buckets)")
            for v in values:
                part, _ = _workday_collect(base, {param: [v["id"]]})
                found.update(part)
            if capped or len(found) >= total * 0.98:
                break  # one exhaustive facet partition is enough
        log(f"  workday: after partitioning collected {len(found)} of {total}")
    jobs = []
    for path, p in found.items():
        posted, src = _workday_relative(p.get("postedOn"))
        jobs.append(
            make_job(
                company=cfg.get("name"),
                ats="workday",
                id=(p.get("bulletFields") or [path])[0],
                title=p.get("title", ""),
                url=f"https://{host}/{site}{path}",
                locations=[p.get("locationsText")] if p.get("locationsText") else [],
                remote=True if re.search(r"remote", p.get("remoteType") or "", re.I) else None,
                workplace_type=(p.get("remoteType") or None),
                employment_type=p.get("timeType"),
                posted_at=posted,
                posted_at_source=src,
                extra={"postedOn": p.get("postedOn")},
                needs_detail=True,
                detail_ref={"base": base, "path": path},
            )
        )
    return jobs


def _workday_detail(job: dict) -> None:
    ref = job["detail_ref"]
    info = get_json(f"{ref['base']}{ref['path']}", timeout=45).get("jobPostingInfo", {})
    job["description"] = html_to_text(info.get("jobDescription"))
    locs = [info.get("location")] + list(info.get("additionalLocations") or [])
    job["locations"] = [l for l in locs if l] or job["locations"]
    if info.get("startDate"):
        job["posted_at"] = parse_date(info["startDate"])
        job["posted_at_source"] = "startDate"
    if info.get("externalUrl"):
        job["url"] = info["externalUrl"]
    job["requisition_id"] = info.get("jobReqId")


# --------------------------------------------------------------------------- SmartRecruiters
def fetch_smartrecruiters(cfg: dict) -> list[dict]:
    cid = cfg["token"]
    out, offset = [], 0
    while True:
        page = get_json(f"https://api.smartrecruiters.com/v1/companies/{cid}/postings?limit=100&offset={offset}", timeout=45)
        content = page.get("content", [])
        out.extend(content)
        offset += len(content)
        if not content or offset >= page.get("totalFound", 0):
            break
    jobs = []
    for p in out:
        loc = p.get("location") or {}
        loc_text = loc.get("fullLocation") or ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
        jobs.append(
            make_job(
                company=cfg.get("name") or (p.get("company") or {}).get("name"),
                ats="smartrecruiters",
                id=p.get("id"),
                title=p.get("name", ""),
                url=f"https://jobs.smartrecruiters.com/{cid}/{p.get('id')}",
                locations=[loc_text] if loc_text else [],
                remote=loc.get("remote"),
                department=(p.get("department") or {}).get("label"),
                team=(p.get("function") or {}).get("label"),
                employment_type=(p.get("typeOfEmployment") or {}).get("label"),
                posted_at=parse_date(p.get("releasedDate")),
                posted_at_source="releasedDate",
                extra={"experienceLevel": (p.get("experienceLevel") or {}).get("label")},
                needs_detail=True,
                detail_ref={"url": p.get("ref") or f"https://api.smartrecruiters.com/v1/companies/{cid}/postings/{p.get('id')}"},
            )
        )
    return jobs


def _smartrecruiters_detail(job: dict) -> None:
    d = get_json(job["detail_ref"]["url"], timeout=45)
    sections = (d.get("jobAd") or {}).get("sections") or {}
    parts = []
    for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation"):
        sec = sections.get(key) or {}
        if sec.get("text"):
            parts.append(f"{sec.get('title', '')}\n{html_to_text(sec['text'])}")
    job["description"] = "\n\n".join(parts)
    if d.get("applyUrl"):
        job["url"] = d["applyUrl"]


# --------------------------------------------------------------------------- Workable
def fetch_workable(cfg: dict) -> list[dict]:
    sub = cfg["token"]
    out, token = [], None
    while True:
        payload = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        if token:
            payload["token"] = token
        page = post_json(f"https://apply.workable.com/api/v3/accounts/{sub}/jobs", payload, timeout=45)
        out.extend(page.get("results", []))
        token = page.get("nextPage")
        if not token:
            break
    jobs = []
    for p in out:
        loc = p.get("location") or {}
        loc_text = ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
        jobs.append(
            make_job(
                company=cfg.get("name"),
                ats="workable",
                id=p.get("shortcode"),
                title=p.get("title", ""),
                url=f"https://apply.workable.com/{sub}/j/{p.get('shortcode')}/",
                locations=[loc_text] if loc_text else [],
                remote=p.get("remote"),
                workplace_type=p.get("workplace"),
                department=", ".join(p.get("department") or []) if isinstance(p.get("department"), list) else p.get("department"),
                employment_type=p.get("type"),
                posted_at=parse_date(p.get("published")),
                posted_at_source="published",
                needs_detail=True,
                detail_ref={"url": f"https://apply.workable.com/api/v2/accounts/{sub}/jobs/{p.get('shortcode')}"},
            )
        )
    return jobs


def _workable_detail(job: dict) -> None:
    d = get_json(job["detail_ref"]["url"], timeout=45)
    parts = [html_to_text(d.get(k)) for k in ("description", "requirements", "benefits") if d.get(k)]
    job["description"] = "\n\n".join(parts)


# --------------------------------------------------------------------------- Recruitee
def fetch_recruitee(cfg: dict) -> list[dict]:
    sub = cfg["token"]
    data = get_json(f"https://{sub}.recruitee.com/api/offers/", timeout=45)
    jobs = []
    for p in data.get("offers", []):
        jobs.append(
            make_job(
                company=cfg.get("name") or p.get("company_name"),
                ats="recruitee",
                id=str(p.get("id")),
                title=p.get("title", ""),
                url=p.get("careers_url") or p.get("careers_apply_url"),
                locations=[p.get("location")] if p.get("location") else [],
                remote=p.get("remote"),
                department=p.get("department"),
                employment_type=p.get("employment_type_code"),
                posted_at=parse_date(p.get("published_at") or p.get("created_at")),
                posted_at_source="published_at",
                description=html_to_text((p.get("description") or "") + "\n" + (p.get("requirements") or "")),
            )
        )
    return jobs


# --------------------------------------------------------------------------- registry
FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "workday": fetch_workday,
    "smartrecruiters": fetch_smartrecruiters,
    "workable": fetch_workable,
    "recruitee": fetch_recruitee,
}

DETAILERS = {
    "workday": _workday_detail,
    "smartrecruiters": _smartrecruiters_detail,
    "workable": _workable_detail,
}


def register(name: str, fetcher, detailer=None) -> None:
    """Let other modules (e.g. custom big-company adapters) plug in."""
    FETCHERS[name] = fetcher
    if detailer:
        DETAILERS[name] = detailer


def fill_details(jobs: list[dict], workers: int = 6) -> int:
    """Fetch full descriptions for jobs flagged needs_detail. Returns number filled."""
    todo = [j for j in jobs if j.get("needs_detail")]
    if not todo:
        return 0

    def work(job):
        fn = DETAILERS.get(job["ats"])
        if not fn:
            return False
        try:
            fn(job)
            job["needs_detail"] = False
            return True
        except Exception as e:
            job.setdefault("extra", {})["detail_error"] = str(e)[:200]
            return False

    serial = {"eightfold", "meta"}
    done = 0
    slow = [j for j in todo if j["ats"] in serial]
    fast = [j for j in todo if j["ats"] not in serial]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for ok in ex.map(work, fast):
            done += 1 if ok else 0
    for j in slow:  # rate-limited platforms: one at a time (each detail call sleeps first)
        done += 1 if work(j) else 0
    return done


def fetch(cfg: dict) -> list[dict]:
    ats = cfg["ats"]
    if ats.startswith("unsupported"):
        raise ValueError(
            f"{cfg.get('name')} uses {ats.split(':', 1)[-1]} which has no adapter yet. Careers page: {cfg.get('careers_url')}. "
            "See research/ats_api_reference.md for a known endpoint, write an adapter in jobhunt/ats_extra.py, "
            "or list the jobs with the browser tools and tell the user the list may be incomplete."
        )
    if ats not in FETCHERS:
        raise ValueError(f"No adapter for ATS '{ats}'. Known: {', '.join(sorted(FETCHERS))}")
    return FETCHERS[ats](cfg)


__all__ = ["fetch", "fill_details", "register", "FETCHERS", "quote"]
