"""Company name -> ATS config.

Order: (1) data/companies.yaml registry, (2) probe public ATS APIs with slug guesses,
(3) detect from a careers-page URL. Probe/detect results must be confirmed (right company,
plausible job count) before they are saved to the registry.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote, urljoin

import yaml

from . import paths
from .common import http


def _norm(s: str) -> str:
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\b(inc|incorporated|llc|ltd|corp|corporation|co|company|technologies|technology|industries|labs|group|holdings|the)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def load_registry() -> list[dict]:
    reg = paths.registry()
    if not reg.exists():
        return []
    return yaml.safe_load(reg.read_text()) or []


def save_entry(entry: dict) -> None:
    reg = load_registry()
    key = _norm(entry["name"])
    reg = [e for e in reg if _norm(e["name"]) != key]
    reg.append(entry)
    reg.sort(key=lambda e: e["name"].lower())
    paths.registry().parent.mkdir(parents=True, exist_ok=True)
    paths.registry().write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True, width=120))


def lookup(name: str) -> list[dict]:
    """All registry entries matching a name or alias (a company can have several boards)."""
    q = _norm(name)
    hits = []
    for e in load_registry():
        names = [e["name"]] + list(e.get("aliases") or [])
        if any(_norm(n) == q for n in names):
            hits.append(e)
    if hits:
        uniq, keys = [], set()
        for e in hits:  # one entry per distinct board
            k = tuple(str(e.get(f) or "") for f in ("ats", "token", "host", "tenant", "site", "domain", "company_filter"))
            if k not in keys:
                keys.add(k)
                uniq.append(e)
        return uniq
    scored = []
    for e in load_registry():
        names = [e["name"]] + list(e.get("aliases") or [])
        best = max(SequenceMatcher(None, q, _norm(n)).ratio() for n in names)
        if best >= 0.86:
            scored.append((best, e))
    return [e for _, e in sorted(scored, key=lambda x: -x[0])]


# ----------------------------------------------------------------------------- probing
def slug_guesses(name: str) -> list[str]:
    base = name.lower().strip()
    words = re.findall(r"[a-z0-9]+", base)
    core = [w for w in words if w not in ("inc", "llc", "the", "co", "corp", "corporation", "company")]
    out = []
    for ws in (core, words):
        if not ws:
            continue
        out += ["".join(ws), "-".join(ws), "_".join(ws)]
    if core:
        first = core[0]
        out += [first, f"{first}hq", f"{first}inc", f"{first}ai", f"{first}labs", f"{first}industries", f"{first}technologies",
                f"{first}-industries", f"{first}-technologies", f"join{first}", f"{first}careers", f"{first}jobs"]
    seen, uniq = set(), []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:18]


def _probe_one(ats: str, slug: str) -> dict | None:
    try:
        if ats == "greenhouse":
            r = http("GET", f"https://boards-api.greenhouse.io/v1/boards/{slug}", retries=1, timeout=15)
            if r.status_code != 200:
                return None
            board = r.json().get("name")
            r2 = http("GET", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", retries=1, timeout=30)
            n = len(r2.json().get("jobs", [])) if r2.status_code == 200 else None
            return {"ats": ats, "token": slug, "board_name": board, "open_jobs": n}
        if ats == "lever":
            r = http("GET", f"https://api.lever.co/v0/postings/{slug}?mode=json", retries=1, timeout=30)
            if r.status_code != 200 or not isinstance(r.json(), list):
                return None
            data = r.json()
            return {"ats": ats, "token": slug, "board_name": slug, "open_jobs": len(data)}
        if ats == "ashby":
            r = http("GET", f"https://api.ashbyhq.com/posting-api/job-board/{slug}", retries=1, timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
            return {"ats": ats, "token": slug, "board_name": slug, "open_jobs": len(data.get("jobs", []))}
        if ats == "smartrecruiters":
            r = http("GET", f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1", retries=1, timeout=15)
            if r.status_code != 200 or not r.json().get("totalFound"):
                return None
            return {"ats": ats, "token": slug, "board_name": slug, "open_jobs": r.json().get("totalFound")}
        if ats == "workable":
            r = http("GET", f"https://apply.workable.com/api/v1/widget/accounts/{slug}", retries=1, timeout=15)
            if r.status_code != 200:
                return None
            d = r.json()
            return {"ats": ats, "token": slug, "board_name": d.get("name"), "open_jobs": len(d.get("jobs", []))}
        if ats == "recruitee":
            r = http("GET", f"https://{slug}.recruitee.com/api/offers/", retries=1, timeout=15)
            if r.status_code != 200:
                return None
            return {"ats": ats, "token": slug, "board_name": slug, "open_jobs": len(r.json().get("offers", []))}
    except Exception:
        return None
    return None


def probe(name: str) -> list[dict]:
    """Try slug guesses on ATSs with predictable public APIs. Returns hits (unverified!)."""
    tasks = [(ats, s) for s in slug_guesses(name) for ats in ("greenhouse", "lever", "ashby", "smartrecruiters", "workable")]
    hits = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(lambda t: _probe_one(*t), tasks):
            if res:
                hits.append(res)
    # de-dup and drop empty boards
    seen, out = set(), []
    for h in sorted(hits, key=lambda h: -(h.get("open_jobs") or 0)):
        k = (h["ats"], h["token"].lower())
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


# ----------------------------------------------------------------------------- detection
DETECT = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=|embed/job_app\?for=)?([A-Za-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/([A-Za-z0-9_-]+)", re.I)),
    ("greenhouse", re.compile(r"greenhouse\.io/embed/job_board/js\?for=([A-Za-z0-9_-]+)", re.I)),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)", re.I)),
    ("lever", re.compile(r"api\.(?:eu\.)?lever\.co/v0/postings/([A-Za-z0-9_.-]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)", re.I)),
    ("ashby", re.compile(r"api\.ashbyhq\.com/posting-api/job-board/([A-Za-z0-9_.%-]+)", re.I)),
    ("workday", re.compile(r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)", re.I)),
    ("workday_site", re.compile(r"(wd\d+)\.myworkdaysite\.com/(?:[a-z]{2}-[A-Z]{2}/)?recruiting/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)", re.I)),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I)),
    ("workable", re.compile(r"apply\.workable\.com/([A-Za-z0-9_-]+)", re.I)),
    ("recruitee", re.compile(r"([a-z0-9-]+)\.recruitee\.com", re.I)),
    # Detected but not (yet) supported by an adapter; reported so Claude can handle them.
    ("icims", re.compile(r"([a-z0-9-]+)\.icims\.com", re.I)),
    ("jobvite", re.compile(r"jobs\.jobvite\.com/([A-Za-z0-9_-]+)", re.I)),
    ("eightfold", re.compile(r"([a-z0-9-]+)\.eightfold\.ai", re.I)),
    ("phenom", re.compile(r"(phenompeople\.com|cdn\.phenompeople)", re.I)),
    ("oracle", re.compile(r"([a-z0-9-]+\.fa\.[a-z0-9-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-z-]+/sites/([A-Za-z0-9_]+)", re.I)),
    ("successfactors", re.compile(r"(successfactors\.com|jobs\.sap\.com|career\d*\.successfactors)", re.I)),
    ("taleo", re.compile(r"([a-z0-9-]+)\.taleo\.net", re.I)),
    ("bamboohr", re.compile(r"([a-z0-9-]+)\.bamboohr\.com", re.I)),
    ("pinpoint", re.compile(r"([a-z0-9-]+)\.pinpointhq\.com", re.I)),
    ("rippling", re.compile(r"ats\.rippling\.com/([A-Za-z0-9_-]+)", re.I)),
    ("teamtailor", re.compile(r"([a-z0-9-]+)\.teamtailor\.com", re.I)),
    ("breezy", re.compile(r"([a-z0-9-]+)\.breezy\.hr", re.I)),
    ("jazzhr", re.compile(r"([a-z0-9-]+)\.applytojob\.com", re.I)),
    ("gem", re.compile(r"jobs\.gem\.com/([A-Za-z0-9_-]+)", re.I)),
    ("dover", re.compile(r"app\.dover\.(?:io|com)/(?:apply|jobs)/([A-Za-z0-9_-]+)", re.I)),
]
_BAD_TOKENS = {"embed", "v1", "boards", "jobs", "job", "api", "js", "static", "assets", "careers", "www", "cdn", "images"}


def detect_in_text(text: str) -> list[dict]:
    found = []
    for ats, rx in DETECT:
        for m in rx.finditer(text):
            if ats == "workday":
                tenant, wd, site = m.group(1), m.group(2), m.group(3)
                if site.lower() in ("wday", "en-us"):
                    continue
                found.append({"ats": "workday", "host": f"{tenant}.{wd}.myworkdayjobs.com", "tenant": tenant, "site": site})
            elif ats == "workday_site":
                wd, tenant, site = m.group(1), m.group(2), m.group(3)
                found.append({"ats": "workday", "host": f"{wd}.myworkdaysite.com", "tenant": tenant, "site": site})
            else:
                tok = unquote(m.group(1)) if m.groups() else m.group(0)
                if tok.lower() in _BAD_TOKENS:
                    continue
                entry = {"ats": ats, "token": tok}
                if ats == "oracle":
                    entry = {"ats": "oracle", "host": m.group(1), "site": m.group(2)}
                found.append(entry)
    seen, out = set(), []
    for f in found:
        k = tuple(sorted(f.items()))
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def detect_from_url(url: str, follow_links: bool = True) -> list[dict]:
    """Fetch a careers page (and same-site 'jobs/careers' links one hop deep) and detect ATSs."""
    found = detect_in_text(url)
    try:
        r = http("GET", url, retries=1, timeout=25, allow_redirects=True)
    except Exception as e:
        return found + [{"error": f"fetch failed: {e}"}]
    found += detect_in_text(r.url) + detect_in_text(r.text)
    if follow_links and not [f for f in found if f.get("ats") in ("greenhouse", "lever", "ashby", "workday", "smartrecruiters", "workable", "recruitee")]:
        links = re.findall(r'href="([^"]+)"', r.text)
        cand = [urljoin(r.url, l) for l in links if re.search(r"job|career|opening|position|work-with-us|join", l, re.I)]
        for l in list(dict.fromkeys(cand))[:8]:
            try:
                r2 = http("GET", l, retries=1, timeout=20)
                found += detect_in_text(r2.url) + detect_in_text(r2.text)
            except Exception:
                continue
    seen, out = set(), []
    for f in found:
        k = tuple(sorted(f.items()))
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out
