"""Adapters for big-company career sites and less common ATSs.

Endpoints and quirks come from research/ats_api_reference.md (all verified live 2026-10-02).
Registry config fields per ats:
  amazon:          {}                                   (all US jobs, partitioned by state)
  apple:           {}                                   (all US jobs)
  google:          {}                                   (all US jobs)
  meta:            {}                                   (all jobs; dates/descriptions fetched per candidate)
  eightfold:       {host, domain, [location], [queries]} (classic v2 or PCSX, auto-detected; rate-limited)
  phenom:          {host, lang, country, page_id}
  brassring:       {partner_id, site_id}
  talentbrew:      {site, [lang]}                       (Radancy front-ends: Intuit, Disney)
  oracle:          {host, site}
  icims:           {token}                              (careers-<token>.icims.com)
  pinpoint/rippling/gem/dover/teamtailor/breezy/bamboohr/jobvite: {token}
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from . import ats
from .ats import log
from .common import get_json, html_to_text, http, make_job, parse_date, post_json, session, USER_AGENT


def _jsonld_jobposting(html_text: str) -> dict:
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html_text, re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and it.get("@type") == "JobPosting":
                return it
            if isinstance(it, dict) and isinstance(it.get("@graph"), list):
                for g in it["@graph"]:
                    if isinstance(g, dict) and g.get("@type") == "JobPosting":
                        return g
    return {}


def _loose_date(s: str | None) -> str | None:
    """'2026-9-30' (TalentBrew) or ISO -> ISO."""
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s.strip())
    if m:
        return parse_date(f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}")
    return parse_date(s)


# =============================================================================== Amazon
def fetch_amazon(cfg: dict) -> list[dict]:
    base = "https://www.amazon.jobs/en/search.json"
    facets = get_json(base, params={"result_limit": 1, "offset": 0, "normalized_country_code[]": "USA",
                                    "facets[]": "normalized_state_name"}, timeout=45)
    states = [list(d.keys())[0] for d in (facets.get("facets") or {}).get("normalized_state_name_facet", [])]
    if not states:
        states = [None]
    found = {}
    for st in states:
        offset = 0
        while True:
            params = {"result_limit": 100, "offset": offset, "sort": "recent", "normalized_country_code[]": "USA"}
            if st:
                params["normalized_state_name[]"] = st
            page = get_json(base, params=params, timeout=45)
            jobs = page.get("jobs") or []
            for j in jobs:
                found[str(j.get("id_icims") or j.get("id"))] = j
            offset += 100
            if not jobs or offset >= min(page.get("hits") or 0, 10000):
                break
            time.sleep(0.4)
    out = []
    cf = (cfg.get("company_filter") or "").lower()
    for jid, j in found.items():
        if cf and cf not in (j.get("company_name") or "").lower():
            continue
        desc = "\n\n".join(x for x in (
            html_to_text(j.get("description")),
            "Basic qualifications:\n" + html_to_text(j.get("basic_qualifications")) if j.get("basic_qualifications") else "",
            "Preferred qualifications:\n" + html_to_text(j.get("preferred_qualifications")) if j.get("preferred_qualifications") else "",
        ) if x)
        posted = re.sub(r"\s+", " ", j.get("posted_date") or "")
        out.append(make_job(
            company="Amazon", ats="amazon", id=jid, title=j.get("title", ""),
            url="https://www.amazon.jobs" + (j.get("job_path") or ""),
            locations=[j.get("normalized_location") or j.get("location") or ""],
            department=j.get("job_category"), team=(j.get("team") or {}).get("label") or j.get("business_category"),
            employment_type=j.get("job_schedule_type"),
            posted_at=parse_date(posted), posted_at_source="posted_date",
            description=desc, extra={"company_name": j.get("company_name"), "is_intern": j.get("is_intern")},
        ))
    return out


# =============================================================================== Apple
def fetch_apple(cfg: dict) -> list[dict]:
    s = session()
    r = http("GET", "https://jobs.apple.com/api/v1/CSRFToken", timeout=30)
    tok = r.headers.get("x-apple-csrf-token")
    hdr = {"x-apple-csrf-token": tok or "", "Origin": "https://jobs.apple.com", "Referer": "https://jobs.apple.com/en-us/search",
           "Content-Type": "application/json"}
    body = {"query": "", "filters": {"locations": ["postLocation-USA"]}, "page": 1, "locale": "en-us", "sort": "newest",
            "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}}
    found, page, total = {}, 1, None
    while True:
        body["page"] = page
        res = s.post("https://jobs.apple.com/api/v1/search", json=body, headers=hdr, timeout=45).json().get("res", {})
        if total is None:
            total = res.get("totalRecords") or 0
            if not total:
                raise RuntimeError("Apple search returned 0 results (CSRF/format problem)")
        rows = res.get("searchResults") or []
        for j in rows:
            found[str(j.get("positionId") or j.get("id"))] = j
        if not rows or page * 20 >= total:
            break
        page += 1
        time.sleep(0.3)
    out = []
    for pid, j in found.items():
        locs = [", ".join(x for x in (l.get("city"), l.get("stateProvince"), l.get("countryName")) if x) or l.get("name", "")
                for l in j.get("locations") or []]
        slug = j.get("transformedPostingTitle") or ""
        out.append(make_job(
            company="Apple", ats="apple", id=pid, title=j.get("postingTitle", ""),
            url=f"https://jobs.apple.com/en-us/details/{pid}/{slug}", locations=locs,
            team=(j.get("team") or {}).get("teamName"),
            posted_at=None if j.get("managedPipelineRole") else parse_date(j.get("postDateInGMT")),
            posted_at_source="postDateInGMT" if not j.get("managedPipelineRole") else "pipeline role (date unreliable)",
            description=j.get("jobSummary") or "", extra={"type": j.get("type")},
            needs_detail=True, detail_ref={"pid": pid},
        ))
    return out


def _apple_detail(job: dict) -> None:
    d = get_json(f"https://jobs.apple.com/api/v1/jobDetails/{job['detail_ref']['pid']}?locale=en-us", timeout=45).get("res", {})
    parts = [("Summary", d.get("jobSummary")), ("Description", d.get("description")), ("Responsibilities", d.get("responsibilities")),
             ("Minimum Qualifications", d.get("minimumQualifications")), ("Preferred Qualifications", d.get("preferredQualifications"))]
    job["description"] = "\n\n".join(f"{h}\n{html_to_text(v)}" for h, v in parts if v)
    footers = d.get("postingFooters") or []
    if footers:
        job["salary_text"] = " ".join(html_to_text(f.get("content") if isinstance(f, dict) else str(f)) for f in footers)[:400]


# =============================================================================== Google
def fetch_google(cfg: dict) -> list[dict]:
    url = "https://www.google.com/about/careers/applications/_/HiringCportalFrontendUi/data/batchexecute"
    params = {"rpcids": "r06xKb", "source-path": "/about/careers/applications/jobs/results/", "hl": "en-US", "rt": "c"}
    found, page, total = {}, 1, None
    while True:
        req = [[None, None, None, None, "en-US", None, [["United States"]], page, None, None, 1]]
        data = {"f.req": json.dumps([[["r06xKb", json.dumps(req), None, "generic"]]])}
        r = http("POST", url, params=params, data=data, timeout=45,
                 headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        t = r.text
        payload = None
        for line in t.split("\n"):
            line = line.strip()
            if line.startswith("[["):
                try:
                    arr = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for e in arr:
                    if isinstance(e, list) and len(e) > 2 and e[0] == "wrb.fr" and e[1] == "r06xKb" and e[2]:
                        payload = json.loads(e[2])
                        break
            if payload:
                break
        if not payload:
            break
        jobs = payload[0] or []
        if total is None:
            total = payload[2] or 0
        for j in jobs:
            found[str(j[0])] = j
        if not jobs or page * 20 >= (total or 0):
            break
        page += 1
        time.sleep(1.2)

    def g(arr, i, sub=None):
        try:
            v = arr[i]
            return v[sub] if sub is not None and isinstance(v, list) else v
        except (IndexError, TypeError):
            return None

    out = []
    for jid, j in found.items():
        locs = []
        for loc in g(j, 9) or []:
            if isinstance(loc, list) and loc:
                locs.append(loc[0])
        ts_created = g(j, 12)
        ts_updated = g(j, 13)
        desc = "\n\n".join(x for x in (
            html_to_text(g(j, 10, 1)), "Responsibilities\n" + html_to_text(g(j, 3, 1)) if g(j, 3, 1) else "",
            "Minimum qualifications\n" + html_to_text(g(j, 19, 1)) if g(j, 19, 1) else "",
            "Qualifications\n" + html_to_text(g(j, 4, 1)) if g(j, 4, 1) else "",
        ) if x)
        out.append(make_job(
            company=g(j, 7) or "Google", ats="google", id=jid, title=g(j, 1) or "",
            url=f"https://www.google.com/about/careers/applications/jobs/results/{jid}", locations=locs,
            posted_at=parse_date(ts_created[0]) if isinstance(ts_created, list) and ts_created else None,
            posted_at_source="created",
            updated_at=parse_date(ts_updated[0]) if isinstance(ts_updated, list) and ts_updated else None,
            description=desc,
        ))
    return out


# =============================================================================== Meta
_META_NAV = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9",
             "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-Dest": "document", "Sec-Fetch-User": "?1",
             "Upgrade-Insecure-Requests": "1"}


def fetch_meta(cfg: dict) -> list[dict]:
    s = session()
    page = s.get("https://www.metacareers.com/jobsearch/", headers=_META_NAV, timeout=45).text
    m = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', page)
    if not m:
        raise RuntimeError("Meta: could not read LSD token (page blocked?)")
    lsd = m.group(1)
    doc_id = cfg.get("doc_id") or "27807005005556827"
    for js in re.findall(r'https://static\.xx\.fbcdn\.net/rsrc\.php/[^"\']+\.js', page)[:15]:
        try:
            body = s.get(js, timeout=30).text
        except Exception:
            continue
        mm = re.search(r'CPJobSearchSourceQuery_candidate_portalRelayOperation",\[\],\(function\([^)]*\)\{\w+\.exports="(\d+)"', body)
        if mm:
            doc_id = mm.group(1)
            break
    variables = {"search_input": {"q": "", "divisions": [], "offices": [], "roles": [], "leadership_levels": [], "saved_jobs": [],
                                  "saved_searches": [], "sub_teams": [], "teams": [], "is_leadership": False, "is_remote_only": False,
                                  "sort_by_new": True, "results_per_page": None}}
    r = s.post("https://www.metacareers.com/graphql", timeout=60,
               headers={"X-FB-LSD": lsd, "X-FB-Friendly-Name": "CPJobSearchSourceQuery", "Origin": "https://www.metacareers.com",
                        "Referer": "https://www.metacareers.com/jobsearch/", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"},
               data={"lsd": lsd, "fb_api_caller_class": "RelayModern", "fb_api_req_friendly_name": "CPJobSearchSourceQuery",
                     "doc_id": doc_id, "server_timestamps": "true", "variables": json.dumps(variables)})
    data = json.loads(r.text)
    jobs = data["data"]["job_search_with_featured_jobs"]["all_jobs"]
    out = []
    for j in jobs:
        out.append(make_job(
            company="Meta", ats="meta", id=str(j.get("id")), title=j.get("title", ""),
            url=f"https://www.metacareers.com/jobs/{j.get('id')}/", locations=list(j.get("locations") or []),
            needs_detail=True, detail_ref={"id": str(j.get("id"))},
        ))
    return out


def _meta_detail(job: dict) -> None:
    time.sleep(2.0)  # Meta is bot-sensitive
    html_text = session().get(f"https://www.metacareers.com/jobs/{job['detail_ref']['id']}/", headers=_META_NAV, timeout=45).text
    jp = _jsonld_jobposting(html_text)
    if not jp:
        raise RuntimeError("no JobPosting JSON-LD")
    parts = [html_to_text(jp.get("description"))]
    for k in ("responsibilities", "qualifications"):
        v = jp.get(k)
        if v:
            parts.append(f"{k.capitalize()}\n" + (html_to_text(v) if isinstance(v, str) else "\n".join(map(str, v))))
    job["description"] = "\n\n".join(p for p in parts if p)
    job["posted_at"] = parse_date(jp.get("datePosted"))
    job["posted_at_source"] = "datePosted (JSON-LD)"


# =============================================================================== Eightfold (classic v2 + PCSX)
def _ef_get(url: str, params: dict) -> dict:
    for attempt in range(6):
        r = http("GET", url, params=params, timeout=45, retries=1)
        if r.status_code == 429:
            time.sleep(8 * (attempt + 1))
            continue
        if r.status_code == 403:
            return {"_forbidden": r.text[:200]}
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Eightfold kept rate-limiting (429)")


def fetch_eightfold(cfg: dict) -> list[dict]:
    host, domain = cfg["host"], cfg["domain"]
    location = cfg.get("location", "")
    queries = cfg.get("queries") or [""]
    gap = float(cfg.get("delay", 4.5))
    mode = cfg.get("mode")
    if not mode:
        probe = _ef_get(f"https://{host}/api/pcsx/search", {"domain": domain, "query": "", "location": location, "start": 0, "sort_by": "timestamp"})
        mode = "classic" if "_forbidden" in probe else "pcsx"
    found = {}
    seen_before = set(cfg.get("_seen") or [])  # watch mode: stop after pages of already-seen postings
    for q in queries:
        start = 0
        stale_pages = 0
        while True:
            if mode == "pcsx":
                d = _ef_get(f"https://{host}/api/pcsx/search", {"domain": domain, "query": q, "location": location, "start": start, "sort_by": "timestamp"})
                data = d.get("data") or {}
                rows, total = data.get("positions") or [], data.get("count") or 0
            else:
                d = _ef_get(f"https://{host}/api/apply/v2/jobs", {"domain": domain, "query": q, "location": location, "start": start, "num": 10, "sort_by": "timestamp"})
                rows, total = d.get("positions") or [], d.get("count") or 0
            for p in rows:
                found[str(p.get("id"))] = p
            start += 10
            if seen_before and rows and all(str(p.get("id")) in seen_before for p in rows):
                stale_pages += 1
                if stale_pages >= 3:
                    break
            else:
                stale_pages = 0
            if not rows or start >= total:
                break
            time.sleep(gap)
        log(f"  eightfold[{q or 'all'}]: {len(found)} unique so far")
    out = []
    for pid, p in found.items():
        if mode == "pcsx":
            posted = p.get("creationTs") or p.get("postedTs")
            out.append(make_job(
                company=cfg.get("name"), ats="eightfold", id=pid, title=p.get("name", ""),
                url=f"https://{host}{p.get('positionUrl') or '/careers/job/' + pid}",
                locations=list(p.get("standardizedLocations") or p.get("locations") or []),
                department=p.get("department"), workplace_type=p.get("workLocationOption"),
                posted_at=parse_date(posted), posted_at_source="creationTs", updated_at=parse_date(p.get("postedTs")),
                requisition_id=p.get("displayJobId"),
                needs_detail=True, detail_ref={"mode": mode, "host": host, "domain": domain, "id": pid, "gap": gap},
            ))
        else:
            out.append(make_job(
                company=cfg.get("name"), ats="eightfold", id=pid, title=p.get("name") or p.get("posting_name") or "",
                url=p.get("canonicalPositionUrl") or f"https://{host}/careers/job/{pid}",
                locations=list(p.get("locations") or [p.get("location")]), department=p.get("department"),
                workplace_type=p.get("work_location_option"),
                posted_at=parse_date(p.get("t_create")), posted_at_source="t_create", updated_at=parse_date(p.get("t_update")),
                requisition_id=p.get("display_job_id"),
                needs_detail=True, detail_ref={"mode": mode, "host": host, "domain": domain, "id": pid, "gap": gap},
            ))
    return out


def _eightfold_detail(job: dict) -> None:
    ref = job["detail_ref"]
    time.sleep(ref.get("gap", 4.5))
    if ref["mode"] == "pcsx":
        d = _ef_get(f"https://{ref['host']}/api/pcsx/position_details", {"position_id": ref["id"], "domain": ref["domain"], "hl": "en"}).get("data") or {}
        job["description"] = html_to_text(d.get("jobDescription"))
        if d.get("publicUrl"):
            job["url"] = d["publicUrl"]
    else:
        d = _ef_get(f"https://{ref['host']}/api/apply/v2/jobs/{ref['id']}", {"domain": ref["domain"]})
        job["description"] = html_to_text(d.get("job_description"))


# =============================================================================== Phenom
def _phenom_config(host: str) -> dict:
    """Read lang/country/pageId from the tenant's server-rendered search page."""
    for path in ("/global/en/search-results", "/us/en/search-results", "/search-results"):
        try:
            r = http("GET", f"https://{host}{path}", timeout=30, retries=1)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        t = r.text
        pid = re.search(r'"pageId"\s*:\s*"(page\d+)"', t)
        lang = re.search(r'"locale"\s*:\s*"([a-z]{2}_[a-z]{2,6})"', t)
        country = re.search(r'"country"\s*:\s*"([a-z]{2,6})"', t)
        if pid:
            return {"page_id": pid.group(1), "lang": lang.group(1) if lang else "en_us", "country": country.group(1) if country else "us"}
    return {}


def fetch_phenom(cfg: dict) -> list[dict]:
    if not cfg.get("page_id"):
        cfg = {**_phenom_config(cfg["host"]), **cfg}
    host, lang, country, page_id = cfg["host"], cfg.get("lang", "en_us"), cfg.get("country", "us"), cfg.get("page_id", "page13")
    found, frm, total = {}, 0, None
    while True:
        body = {"lang": lang, "deviceType": "desktop", "country": country, "pageName": "search-results", "ddoKey": "refineSearch",
                "sortBy": "", "subsearch": "", "from": frm, "jobs": True, "counts": True, "all_fields": [], "size": 100, "clearAll": False,
                "jdsource": "facets", "isSliderEnable": False, "pageId": page_id, "siteType": "external", "keywords": "", "global": True,
                "selected_fields": {}, "locationData": {}}
        rs = post_json(f"https://{host}/widgets", body, timeout=45).get("refineSearch") or {}
        rows = (rs.get("data") or {}).get("jobs") or []
        total = rs.get("totalHits") if total is None else total
        for j in rows:
            found[str(j.get("jobSeqNo") or j.get("jobId"))] = j
        frm += 100
        if not rows or frm >= (total or 0):
            break
        time.sleep(0.4)
    out = []
    for seq, j in found.items():
        locs = j.get("multi_location") or [j.get("location") or ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)]
        out.append(make_job(
            company=cfg.get("name"), ats="phenom", id=str(j.get("jobId") or seq), title=j.get("title", ""),
            url=f"https://{host}/{country}/{lang.split('_')[0]}/job/{j.get('jobId')}",
            locations=[l for l in locs if l], department=j.get("category"), employment_type=j.get("type"),
            posted_at=parse_date(j.get("postedDate")), posted_at_source="postedDate", description=j.get("descriptionTeaser") or "",
            needs_detail=True, detail_ref={"host": host, "lang": lang, "country": country, "seq": j.get("jobSeqNo")},
        ))
    return out


def _phenom_detail(job: dict) -> None:
    ref = job["detail_ref"]
    body = {"lang": ref["lang"], "deviceType": "desktop", "country": ref["country"], "pageName": "job", "ddoKey": "jobDetail", "jobSeqNo": ref["seq"]}
    d = post_json(f"https://{ref['host']}/widgets", body, timeout=45)
    jd = ((d.get("jobDetail") or {}).get("data") or {}).get("job") or {}
    job["description"] = html_to_text(jd.get("description")) + ("\n\n" + html_to_text(jd.get("jobRequirements")) if jd.get("jobRequirements") else "")


# =============================================================================== BrassRing (General Atomics)
def fetch_brassring(cfg: dict) -> list[dict]:
    pid, sid = str(cfg["partner_id"]), str(cfg["site_id"])
    s = session()
    home = f"https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid={pid}&siteid={sid}"
    h = s.get(home, timeout=60).text
    tok = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', h)
    sr = re.search(r'id="searchResults" type="hidden" value="([^"]+)"', h)
    import html as _html
    kw_fields, loc_fields = "", ""
    if sr:
        try:
            emb = json.loads(_html.unescape(sr.group(1)))
            kw_fields = emb.get("KeywordCustomSolrFields", "")
            loc_fields = emb.get("LocationCustomSolrFields", "")
        except json.JSONDecodeError:
            pass
    hdr = {"RFT": tok.group(1) if tok else "", "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "Referer": home}
    body = {"partnerId": pid, "siteId": sid, "keyword": "", "location": "", "keywordCustomSolrFields": kw_fields,
            "locationCustomSolrFields": loc_fields, "linkId": "", "Latitude": 0, "Longitude": 0, "facetfilterfields": {"Facet": []},
            "powersearchoptions": {"PowerSearchOption": []}, "SortType": "LastUpdated", "encryptedSessionValue": ""}
    first = s.post("https://sjobs.brassring.com/TgNewUI/Search/Ajax/MatchedJobs", json=body, headers=hdr, timeout=60).json()
    total = first.get("JobsCount") or 0
    jobs = list((first.get("Jobs") or {}).get("Job") or [])
    page = 2
    while len(jobs) < total and page < 200:
        b2 = dict(body, pageNumber=page)
        r = s.post("https://sjobs.brassring.com/TgNewUI/Search/Ajax/ProcessSortAndShowMoreJobs", json=b2, headers=hdr, timeout=60).json()
        more = (r.get("Jobs") or {}).get("Job") or []
        if not more:
            break
        jobs += more
        page += 1
        time.sleep(0.5)
    out = []
    for j in jobs:
        q = {x.get("QuestionName", "").lower(): x.get("Value") for x in j.get("Questions") or []}
        title = q.get("formtext8") or q.get("jobtitle") or ""
        city, state = q.get("formtext5") or "", q.get("formtext4") or ""
        out.append(make_job(
            company=cfg.get("name"), ats="brassring", id=str(q.get("reqid") or q.get("autoreq")), title=_html.unescape(title),
            url=j.get("Link"), locations=[", ".join(x for x in (city, state) if x)], department=q.get("department"),
            posted_at=parse_date(datetime.strptime(q["lastupdated"], "%d-%b-%Y").strftime("%Y-%m-%d")) if q.get("lastupdated") else None,
            posted_at_source="lastupdated", description=html_to_text(q.get("jobdescription")),
            requisition_id=q.get("autoreq"),
            needs_detail=True, detail_ref={"pid": pid, "sid": sid, "reqid": q.get("reqid"), "hdr": hdr},
        ))
    return out


def _brassring_detail(job: dict) -> None:
    ref = job["detail_ref"]
    body = {"partnerId": ref["pid"], "siteId": ref["sid"], "jobid": ref["reqid"], "configMode": "", "jobSiteId": ref["sid"]}
    d = session().post("https://sjobs.brassring.com/TgNewUI/Search/Ajax/JobDetails", json=body, headers=ref["hdr"], timeout=60).json()
    qs = ((d.get("ServiceResponse") or {}).get("Jobdetails") or {}).get("JobDetailQuestions") or []
    parts = []
    for x in qs:
        name, val = x.get("QuestionName") or x.get("VerityZone") or "", x.get("AnswerValue")
        if val:
            parts.append(f"{name}: {html_to_text(val)}")
    job["description"] = "\n\n".join(parts)


# =============================================================================== Radancy TalentBrew (Intuit, Disney front-end)
def fetch_talentbrew(cfg: dict) -> list[dict]:
    site = cfg["site"].rstrip("/")
    lang = cfg.get("lang", "")
    base = f"https://{site}/{lang + '/' if lang else ''}search-jobs/results"
    found, page, pages = {}, 1, None
    while True:
        params = {"ActiveFacetID": 0, "CurrentPage": page, "RecordsPerPage": 100, "Distance": 50, "RadiusUnitType": 0, "Keywords": "",
                  "Location": "", "ShowRadius": "False", "IsPagination": "False", "SearchResultsModuleName": "Search Results",
                  "SearchFiltersModuleName": "Search Filters", "SortCriteria": 0, "SortDirection": 0, "SearchType": 5}
        r = http("GET", base, params=params, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=45).json()
        res = r.get("results") or ""
        if pages is None:
            m = re.search(r'data-total-pages="(\d+)"', res)
            pages = int(m.group(1)) if m else 1
        for m in re.finditer(r'<a[^>]+href="([^"]*/job/[^"]+/(\d+))"[^>]*data-job-id="(\d+)"[^>]*>(.*?)</a>', res, re.S):
            href, jid, title_html = m.group(1), m.group(3), m.group(4)
            t = re.search(r"<h2[^>]*>(.*?)</h2>", title_html, re.S)
            loc = re.search(r'class="job-location"[^>]*>(.*?)</span>', title_html, re.S)
            found[jid] = {"href": href if href.startswith("http") else f"https://{site}{href}",
                          "title": html_to_text(t.group(1)) if t else html_to_text(title_html),
                          "loc": html_to_text(loc.group(1)) if loc else ""}
        if page >= pages:
            break
        page += 1
        time.sleep(0.4)
    return [make_job(company=cfg.get("name"), ats="talentbrew", id=jid, title=v["title"], url=v["href"],
                     locations=[v["loc"]] if v["loc"] else [], needs_detail=True, detail_ref={"url": v["href"]})
            for jid, v in found.items()]


def _jsonld_detail(job: dict) -> None:
    html_text = http("GET", job["detail_ref"]["url"], timeout=45).text
    jp = _jsonld_jobposting(html_text)
    if not jp:
        raise RuntimeError("no JobPosting JSON-LD")
    job["description"] = html_to_text(jp.get("description"))
    job["posted_at"] = _loose_date(jp.get("datePosted"))
    job["posted_at_source"] = "datePosted (JSON-LD)"
    locs = []
    jl = jp.get("jobLocation")
    for loc in (jl if isinstance(jl, list) else [jl] if jl else []):
        a = (loc or {}).get("address") or {}
        if isinstance(a, dict):
            locs.append(", ".join(x for x in (a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry")) if isinstance(x, str) and x))
    if locs:
        job["locations"] = locs


# =============================================================================== Oracle Recruiting Cloud
def fetch_oracle(cfg: dict) -> list[dict]:
    host, site = cfg["host"], cfg["site"]
    out, offset, total = [], 0, None
    while True:
        url = (f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
               f"&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber={site},limit=200,offset={offset},sortBy=POSTING_DATES_DESC")
        item = get_json(url, timeout=60)["items"][0]
        total = item.get("TotalJobsCount") if total is None else total
        rows = item.get("requisitionList") or []
        for j in rows:
            locs = [j.get("PrimaryLocation")] + [s.get("Name") for s in j.get("secondaryLocations") or []]
            out.append(make_job(
                company=cfg.get("name"), ats="oracle", id=str(j.get("Id")), title=j.get("Title", ""),
                url=f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{j.get('Id')}", locations=[l for l in locs if l],
                department=j.get("JobFamily"), workplace_type=j.get("WorkplaceType"),
                posted_at=parse_date(j.get("PostedDate")), posted_at_source="PostedDate", description=j.get("ShortDescriptionStr") or "",
                needs_detail=True, detail_ref={"host": host, "site": site, "id": j.get("Id")},
            ))
        offset += 200
        if not rows or offset >= (total or 0):
            break
    return out


def _oracle_detail(job: dict) -> None:
    ref = job["detail_ref"]
    url = (f"https://{ref['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
           f"&finder=ById;Id=\"{ref['id']}\",siteNumber={ref['site']}")
    it = get_json(url, timeout=60)["items"][0]
    job["description"] = "\n\n".join(html_to_text(it.get(k)) for k in ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr") if it.get(k))
    if it.get("ExternalPostedStartDate"):
        job["posted_at"] = parse_date(it["ExternalPostedStartDate"])


# =============================================================================== iCIMS
def fetch_icims(cfg: dict) -> list[dict]:
    tok = cfg["token"]
    host = cfg.get("host") or f"careers-{tok}.icims.com"
    found, pr, pages = {}, 0, None
    while True:
        html_text = http("GET", f"https://{host}/jobs/search", params={"ss": 1, "in_iframe": 1, "pr": pr}, timeout=45).text
        if pages is None:
            m = re.search(r"of (\d+) , Current Page", html_text)
            pages = int(m.group(1)) if m else 1
        for m in re.finditer(rf'href="(https://{re.escape(host)}/jobs/(\d+)/[^"]+/job[^"]*)"[^>]*title="\d+ - ([^"]+)"', html_text):
            found[m.group(2)] = (m.group(1).split("?")[0], m.group(3))
        pr += 1
        if pr >= pages:
            break
        time.sleep(0.5)
    import html as _html
    return [make_job(company=cfg.get("name"), ats="icims", id=jid, title=_html.unescape(t), url=u,
                     needs_detail=True, detail_ref={"url": u + "?in_iframe=1"}) for jid, (u, t) in found.items()]


# =============================================================================== small startup ATSs (simple JSON)
def fetch_pinpoint(cfg: dict) -> list[dict]:
    d = get_json(f"https://{cfg['token']}.pinpointhq.com/postings.json", timeout=45).get("data", [])
    out = []
    for p in d:
        parts = [p.get(k) for k in ("description", "key_responsibilities", "skills_knowledge_expertise") if p.get(k)]
        loc = p.get("location") or {}
        out.append(make_job(company=cfg.get("name"), ats="pinpoint", id=str(p.get("id")), title=p.get("title", ""), url=p.get("url"),
                            locations=[loc.get("name") or ", ".join(x for x in (loc.get("city"), loc.get("province")) if x)],
                            workplace_type=p.get("workplace_type"), department=((p.get("job") or {}).get("department") or {}).get("name"),
                            employment_type=p.get("employment_type"), salary_text=p.get("compensation"),
                            description=html_to_text("\n".join(parts)),
                            needs_detail=True, detail_ref={"url": p.get("url"), "date_only": True}))
    return out


def _date_only_detail(job: dict) -> None:
    html_text = http("GET", job["detail_ref"]["url"], timeout=45).text
    jp = _jsonld_jobposting(html_text)
    if jp.get("datePosted"):
        job["posted_at"] = _loose_date(jp["datePosted"])
        job["posted_at_source"] = "datePosted (JSON-LD)"


def fetch_rippling(cfg: dict) -> list[dict]:
    slug = cfg["token"]
    items, page = [], 0
    while True:
        d = get_json(f"https://ats.rippling.com/api/v2/board/{slug}/jobs", params={"page": page, "pageSize": 500}, timeout=45)
        items += d.get("items") or []
        page += 1
        if page >= (d.get("totalPages") or 1):
            break
    return [make_job(company=cfg.get("name"), ats="rippling", id=str(j.get("id")), title=j.get("name", ""), url=j.get("url"),
                     locations=[l.get("name") for l in j.get("locations") or [] if l.get("name")],
                     department=(j.get("department") or {}).get("name"),
                     needs_detail=True, detail_ref={"url": f"https://ats.rippling.com/api/v2/board/{slug}/jobs/{j.get('id')}"})
            for j in items]


def _rippling_detail(job: dict) -> None:
    d = get_json(job["detail_ref"]["url"], timeout=45)
    desc = d.get("description") or {}
    job["description"] = "\n\n".join(html_to_text(desc.get(k)) for k in ("role", "company") if desc.get(k))
    job["posted_at"] = parse_date(d.get("createdOn"))
    job["posted_at_source"] = "createdOn"
    pr = d.get("payRangeDetails") or []
    if pr:
        p = pr[0]
        job["salary_text"] = f"${p.get('rangeStart')} - ${p.get('rangeEnd')} {p.get('frequency', '')}"


def fetch_gem(cfg: dict) -> list[dict]:
    d = get_json(f"https://api.gem.com/job_board/v0/{cfg['token']}/job_posts/", timeout=45)
    return [make_job(company=cfg.get("name"), ats="gem", id=str(j.get("id")), title=j.get("title", ""), url=j.get("absolute_url"),
                     locations=[(j.get("location") or {}).get("name")] if (j.get("location") or {}).get("name") else [],
                     workplace_type=j.get("location_type"), department=", ".join(x.get("name", "") for x in j.get("departments") or []),
                     employment_type=j.get("employment_type"),
                     posted_at=parse_date(j.get("first_published_at") or j.get("created_at")), posted_at_source="first_published_at",
                     updated_at=parse_date(j.get("updated_at")),
                     description=j.get("content_plain") or html_to_text(j.get("content"))) for j in d]


def fetch_dover(cfg: dict) -> list[dict]:
    cid = get_json(f"https://app.dover.com/api/v1/careers-page-slug/{cfg['token']}", timeout=45)["id"]
    url, rows = f"https://app.dover.com/api/v1/careers-page/{cid}/jobs", []
    while url:
        d = get_json(url, timeout=45)
        rows += d.get("results") or []
        url = d.get("next")
    out = []
    for j in rows:
        if j.get("is_published") is False or j.get("is_sample"):
            continue
        locs = [((l.get("location_option") or {}).get("display_name")) for l in j.get("locations") or []]
        out.append(make_job(company=cfg.get("name"), ats="dover", id=str(j.get("id")), title=j.get("title", ""),
                            url=f"https://app.dover.com/apply/{cfg['token']}/{j.get('id')}", locations=[l for l in locs if l],
                            workplace_type=j.get("workplace_type"),
                            needs_detail=True, detail_ref={"url": f"https://app.dover.com/api/v1/inbound/application-portal-job/{j.get('id')}"}))
    return out


def _dover_detail(job: dict) -> None:
    d = get_json(job["detail_ref"]["url"], timeout=45)
    job["description"] = html_to_text(d.get("user_provided_description"))
    job["posted_at"] = parse_date(d.get("created"))
    job["posted_at_source"] = "created"


def fetch_teamtailor(cfg: dict) -> list[dict]:
    site = cfg.get("host") or f"{cfg['token']}.teamtailor.com"
    d = get_json(f"https://{site}/jobs.json", timeout=45)
    out = []
    for it in d.get("items") or []:
        jp = it.get("_jobposting") or {}
        locs = []
        jl = jp.get("jobLocation")
        for loc in (jl if isinstance(jl, list) else [jl] if jl else []):
            a = (loc or {}).get("address") or {}
            locs.append(", ".join(x for x in (a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry")) if isinstance(x, str) and x))
        out.append(make_job(company=cfg.get("name"), ats="teamtailor", id=str(it.get("id")), title=it.get("title", ""), url=it.get("url"),
                            locations=[l for l in locs if l], posted_at=parse_date(it.get("date_published")), posted_at_source="date_published",
                            description=html_to_text(it.get("content_html"))))
    return out


def fetch_breezy(cfg: dict) -> list[dict]:
    d = get_json(f"https://{cfg['token']}.breezy.hr/json", params={"verbose": "true"}, timeout=45)
    out = []
    for j in d:
        loc = j.get("location") or {}
        out.append(make_job(company=cfg.get("name"), ats="breezy", id=str(j.get("id")), title=j.get("name", ""), url=j.get("url"),
                            locations=[loc.get("name") or ""], department=j.get("department"),
                            employment_type=(j.get("type") or {}).get("name"), salary_text=j.get("salary"),
                            posted_at=parse_date(j.get("published_date")), posted_at_source="published_date",
                            description=html_to_text(j.get("description"))))
    return out


def fetch_bamboohr(cfg: dict) -> list[dict]:
    co = cfg["token"]
    d = get_json(f"https://{co}.bamboohr.com/careers/list", timeout=45)
    out = []
    for j in d.get("result") or []:
        loc = j.get("location") or {}
        out.append(make_job(company=cfg.get("name"), ats="bamboohr", id=str(j.get("id")), title=j.get("jobOpeningName", ""),
                            url=f"https://{co}.bamboohr.com/careers/{j.get('id')}",
                            locations=[", ".join(x for x in (loc.get("city"), loc.get("state")) if x)] if loc else [],
                            remote=j.get("isRemote"), department=j.get("departmentLabel"), employment_type=j.get("employmentStatusLabel"),
                            needs_detail=True, detail_ref={"url": f"https://{co}.bamboohr.com/careers/{j.get('id')}/detail"}))
    return out


def _bamboohr_detail(job: dict) -> None:
    jo = (get_json(job["detail_ref"]["url"], timeout=45).get("result") or {}).get("jobOpening") or {}
    job["description"] = html_to_text(jo.get("description"))
    job["posted_at"] = parse_date(jo.get("datePosted"))
    job["posted_at_source"] = "datePosted"
    if jo.get("compensation"):
        job["salary_text"] = str(jo["compensation"])


def fetch_jobvite(cfg: dict) -> list[dict]:
    co = cfg["token"]
    html_text = http("GET", f"https://jobs.jobvite.com/{co}/jobs", timeout=45).text
    found = {}
    for m in re.finditer(rf'<a href="/{re.escape(co)}/job/([A-Za-z0-9]+)"[^>]*>(.*?)</a>\s*</td>\s*<td class="jv-job-list-location">(.*?)</td>', html_text, re.S):
        found[m.group(1)] = (html_to_text(m.group(2)), html_to_text(m.group(3)))
    return [make_job(company=cfg.get("name"), ats="jobvite", id=jid, title=t, url=f"https://jobs.jobvite.com/{co}/job/{jid}",
                     locations=[l] if l else [], posted_at_source="none (Jobvite shows no dates)",
                     needs_detail=True, detail_ref={"url": f"https://jobs.jobvite.com/{co}/job/{jid}"})
            for jid, (t, l) in found.items()]


def _jobvite_detail(job: dict) -> None:
    html_text = http("GET", job["detail_ref"]["url"], timeout=45).text
    m = re.search(r'<div class="jv-job-detail-description"[^>]*>(.*?)</div>\s*(?:<div class="jv-job-detail-|</div>)', html_text, re.S)
    job["description"] = html_to_text(m.group(1) if m else html_text)


# =============================================================================== registration
ats.register("amazon", fetch_amazon)
ats.register("apple", fetch_apple, _apple_detail)
ats.register("google", fetch_google)
ats.register("meta", fetch_meta, _meta_detail)
ats.register("eightfold", fetch_eightfold, _eightfold_detail)
ats.register("phenom", fetch_phenom, _phenom_detail)
ats.register("brassring", fetch_brassring, _brassring_detail)
ats.register("talentbrew", fetch_talentbrew, _jsonld_detail)
ats.register("oracle", fetch_oracle, _oracle_detail)
ats.register("icims", fetch_icims, _jsonld_detail)
ats.register("pinpoint", fetch_pinpoint, _date_only_detail)
ats.register("rippling", fetch_rippling, _rippling_detail)
ats.register("gem", fetch_gem)
ats.register("dover", fetch_dover, _dover_detail)
ats.register("teamtailor", fetch_teamtailor)
ats.register("breezy", fetch_breezy)
ats.register("bamboohr", fetch_bamboohr, _bamboohr_detail)
ats.register("jobvite", fetch_jobvite, _jobvite_detail)


# =============================================================================== Jibe (Google-hosted career sites over iCIMS etc.)
def fetch_jibe(cfg: dict) -> list[dict]:
    host = cfg["host"]
    out, page, total = [], 1, None
    while True:
        d = get_json(f"https://{host}/api/jobs", params={"page": page, "limit": 100}, timeout=45)
        rows = d.get("jobs") or []
        total = d.get("totalCount") if total is None else total
        for row in rows:
            j = row.get("data") or row
            parts = [j.get("description"), j.get("responsibilities"), j.get("qualifications")]
            out.append(make_job(
                company=cfg.get("name"), ats="jibe", id=str(j.get("req_id") or j.get("slug")), title=j.get("title", ""),
                url=f"https://{host}/jobs/{j.get('slug')}" if j.get("slug") else j.get("apply_url"),
                locations=[j.get("full_location") or ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)],
                department=", ".join(c.get("name", "") for c in (j.get("categories") or []) if isinstance(c, dict)) or None,
                employment_type=j.get("employment_type"),
                posted_at=parse_date((j.get("posted_date") or "").replace("+0000", "+00:00")), posted_at_source="posted_date",
                updated_at=parse_date((j.get("update_date") or "").replace("+0000", "+00:00")),
                description=html_to_text("\n".join(x for x in parts if x)),
                extra={"apply_url": j.get("apply_url"), "lat": j.get("latitude"), "lng": j.get("longitude")},
            ))
        page += 1
        if not rows or len(out) >= (total or 0):
            break
        time.sleep(0.3)
    return out


# =============================================================================== TikTok
def fetch_tiktok(cfg: dict) -> list[dict]:
    url = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
    hdr = {"website-path": "tiktok", "Origin": "https://lifeattiktok.com", "Referer": "https://lifeattiktok.com/"}
    out, offset, total = [], 0, None
    while True:
        body = {"recruitment_id_list": [], "job_category_id_list": [], "subject_id_list": [], "location_code_list": [],
                "keyword": cfg.get("keyword", ""), "limit": 100, "offset": offset}
        d = (post_json(url, body, headers=hdr, timeout=45).get("data") or {})
        rows = d.get("job_post_list") or []
        total = d.get("count") if total is None else total
        for j in rows:
            city = (j.get("city_info") or {})
            loc = city.get("en_name") or city.get("name") or ""
            parent = (city.get("parent") or {}) if isinstance(city.get("parent"), dict) else {}
            country = ((parent.get("parent") or {}) if isinstance(parent.get("parent"), dict) else {}).get("en_name") or parent.get("en_name") or ""
            out.append(make_job(
                company="TikTok", ats="tiktok", id=str(j.get("id")), title=j.get("title", ""),
                url=f"https://lifeattiktok.com/search/{j.get('id')}", locations=[", ".join(x for x in (loc, country) if x)],
                department=(j.get("job_category") or {}).get("en_name"),
                employment_type=(j.get("recruit_type") or {}).get("en_name"),
                description=(j.get("description") or "") + "\n\nRequirements\n" + (j.get("requirement") or ""),
                posted_at_source="none (TikTok shows no dates)",
            ))
        offset += 100
        if not rows or offset >= (total or 0):
            break
        time.sleep(0.4)
    return out


# =============================================================================== Atlassian
def fetch_atlassian(cfg: dict) -> list[dict]:
    rows = get_json("https://www.atlassian.com/endpoint/careers/listings", timeout=60)
    return [make_job(company="Atlassian", ats="atlassian", id=str(j.get("id")), title=j.get("title", ""),
                     url=j.get("applyUrl") or (j.get("portalJobPost") or {}).get("portalUrl"),
                     locations=list(j.get("locations") or []), department=j.get("category"), employment_type=j.get("type"),
                     description=html_to_text("\n".join(x for x in (j.get("overview"), j.get("responsibilities"), j.get("qualifications")) if x)),
                     posted_at_source="none (no dates in listing)") for j in rows]


ats.register("jibe", fetch_jibe)
ats.register("tiktok", fetch_tiktok)
ats.register("atlassian", fetch_atlassian)

# Rate-limited platforms: fetch details serially.
SERIAL_DETAIL = {"eightfold", "meta"}
