"""applications.csv: the record of where you have applied (manual logs + email-confirmation imports)."""

from __future__ import annotations

import csv
import re
from datetime import date

from . import paths
FIELDS = ["date_applied", "company", "title", "job_id", "url", "location", "status", "status_date", "source", "resume", "notes"]

# An application that is still open on the employer's side.
LIVE = {"applied", "screen", "assessment", "interview", "interviewing", "onsite", "offer"}
# After about six months an old outcome stops counting as a duplicate (docs/JOB_SEARCH.md, "Duplicates").
STALE_DAYS = 180

_SUFFIX = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "technologies", "technology", "industries", "labs", "the"}


def _norm_company(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company|technologies|industries|labs|the)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _company_tokens(s: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (s or "").lower())
    return [w for w in words if w not in _SUFFIX] or words


_ALIASES: dict[str, str] | None = None


def _canonical(name: str) -> str:
    """The registry's name for a company known by an alias there ('Disney' -> 'The Walt Disney Company')."""
    global _ALIASES
    if _ALIASES is None:
        _ALIASES = {}
        reg = paths.registry()
        if reg.exists():
            import yaml
            for c in yaml.safe_load(reg.read_text()) or []:
                for alias in (c.get("aliases") or []):
                    _ALIASES.setdefault(_norm_company(alias), c["name"])
    return _ALIASES.get(_norm_company(name), name)


def same_company(a: str, b: str) -> bool:
    """Whole-word match, so 'Hadrian' = 'Hadrian Automation' and 'Anduril' = 'Anduril Industries',
    but 'SpaceX' is not 'SpaceXAI' and 'Box' is not 'Dropbox'. Registry aliases count as the same company."""
    ta, tb = _company_tokens(_canonical(a)), _company_tokens(_canonical(b))
    n = min(len(ta), len(tb))
    return n > 0 and ta[:n] == tb[:n]


def _norm_title(s: str) -> str:
    s = re.sub(r"\[[^\]]*\]", " ", s or "")  # tags like [EVERGREEN] or [2026] are not part of the role's name
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load() -> list[dict]:
    path = paths.applications()
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    path = paths.applications()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) or "" for k in FIELDS})


def add(company: str, title: str, *, job_id: str = "", url: str = "", location: str = "", status: str = "applied",
        source: str = "manual", resume: str = "", notes: str = "", when: str | None = None) -> dict:
    """Log an application, or update one already on record.

    The same posting (job id or URL at the same company) is updated, never duplicated. An outcome (rejected,
    interview, offer...) without an id or URL updates the latest application with the same title. An update keeps the
    original application date and records the outcome's date in status_date."""
    rows = load()
    day = when or date.today().isoformat()
    mine = [r for r in rows if same_company(r.get("company"), company)]
    hit = next((r for r in reversed(mine) if (job_id and r.get("job_id") == job_id) or (url and r.get("url") == url)), None)
    if hit is None and status != "applied" and not job_id and not url:
        hit = next((r for r in reversed(mine) if same_title(r.get("title"), title)), None)
    if hit is not None:
        for k, v in (("title", title), ("job_id", job_id), ("url", url), ("location", location), ("resume", resume)):
            if v and not hit.get(k):
                hit[k] = v
        if status != (hit.get("status") or "applied"):
            hit["status"], hit["status_date"] = status, day
        if notes:
            hit["notes"] = "; ".join(x for x in (hit.get("notes"), notes) if x)
        save(rows)
        return hit
    row = {"date_applied": day, "company": company, "title": title, "job_id": job_id, "url": url, "location": location,
           "status": status, "status_date": day if status != "applied" else "", "source": source, "resume": resume,
           "notes": notes}
    rows.append(row)
    save(rows)
    return row


_GENERIC = {"the", "a", "an", "of", "and", "for", "to", "in", "at", "i", "ii", "iii"}


def _tokens(s: str) -> frozenset:
    return frozenset(w for w in _norm_title(s).split() if w not in _GENERIC)


_LEVEL = {"i": 1, "ii": 2, "iii": 3, "1": 1, "2": 2, "3": 3}


def _level(title: str) -> int | None:
    found = {_LEVEL[w] for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if w in _LEVEL}
    return found.pop() if len(found) == 1 else None


def same_title(a: str, b: str) -> bool:
    """Same words, ignoring filler. 'Software Engineer I' and 'Software Engineer II' are different postings
    when both name a level; a title with no level still matches either (emails often drop it)."""
    ta, tb = _tokens(a), _tokens(b)
    la, lb = _level(a), _level(b)
    if la and lb and la != lb:
        return False
    return bool(ta) and ta == tb


def similar_title(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.75 or (min(len(ta), len(tb)) >= 3 and (ta <= tb or tb <= ta))


def _when(r: dict) -> str:
    return r.get("status_date") or r.get("date_applied") or ""


def _age_days(r: dict, today: date) -> int | None:
    m = re.match(r"(\d{4})-(\d{2})(?:-(\d{2}))?", _when(r))
    if not m:
        return None
    return (today - date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))).days


def describe(r: dict) -> str:
    """'applied 2026-09-18' or 'rejected 2026-07-03 (applied 2026-06-27)'."""
    status = r.get("status") or "applied"
    applied = r.get("date_applied") or "?"
    changed = r.get("status_date") or ""
    if status == "applied" or not changed or changed == applied:
        return f"{status} {applied}"
    return f"{status} {changed} (applied {applied})"


def match(job: dict, rows: list[dict], today: date | None = None) -> str | None:
    """Note if this job was (possibly) applied to already.

    'same posting' = same job id/url. 'same title' = identical title words at the same company (likely the
    same role reposted or in another location). 'similar role' = high overlap but different words; shown
    for information only, never treated as a duplicate. Results that start with DUPLICATE are never
    suggested as picks.
    """
    today = today or date.today()
    jid = str(job.get("id") or "")
    exact, same, similar = [], [], []
    for r in rows:
        if not same_company(r.get("company"), job.get("company")):
            continue
        if jid and (r.get("job_id") == jid or (r.get("url") and jid in r["url"])):
            exact.append(r)
        elif same_title(r.get("title"), job.get("title")):
            same.append(r)
        elif similar_title(r.get("title"), job.get("title")):
            similar.append(r)

    def pick(cands: list[dict]) -> dict:  # an open application matters most, then the latest outcome
        return max(cands, key=lambda r: ((r.get("status") or "applied") in LIVE, _when(r)))

    if exact:
        r = pick(exact)
        return f"DUPLICATE: {describe(r)} (same posting, {r.get('source') or 'manual'})"
    if same:
        r = pick(same)
        status = r.get("status") or "applied"
        age = _age_days(r, today)
        if status not in LIVE and status != "possibly-applied" and age is not None and age > STALE_DAYS:
            return f"applied before: {describe(r)} for the same title, over 6 months ago"
        return f"DUPLICATE?: {describe(r)} for the same title (source: {r.get('source') or 'manual'})"
    if similar:
        r = pick(similar)
        return f"similar role on record: '{r.get('title')}' ({describe(r)})"
    return None


def for_company(company: str) -> list[dict]:
    return [r for r in load() if same_company(r.get("company"), company)]
