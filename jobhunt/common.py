"""Shared helpers: HTTP session, HTML-to-text, dates, normalized job records."""

from __future__ import annotations

import html as htmllib
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_local = threading.local()  # one session per thread: a sweep fetches many companies in parallel


def session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9, */*;q=0.8", "Accept-Encoding": "gzip, deflate"})
        _local.session = s
    return s


def http(method: str, url: str, *, retries: int = 3, timeout=(10, 60), **kw) -> requests.Response:
    """Request with retries on 429/5xx and network errors. Raises on final failure."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session().request(method, url, timeout=timeout, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                wait = float(r.headers.get("Retry-After") or 0) or (1.5 * (attempt + 1))
                time.sleep(min(wait, 20))
                last = requests.HTTPError(f"{r.status_code} for {url}")
                continue
            return r
        except requests.RequestException as e:  # network error
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last if last else RuntimeError(f"request failed: {url}")


def get_json(url: str, **kw) -> Any:
    r = http("GET", url, **kw)
    r.raise_for_status()
    return r.json()


def post_json(url: str, payload: dict, **kw) -> Any:
    headers = {"Content-Type": "application/json", **kw.pop("headers", {})}
    r = http("POST", url, json=payload, headers=headers, **kw)
    r.raise_for_status()
    return r.json()


_BLOCK_TAGS = ("p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section")


def html_to_text(raw: str | None) -> str:
    """Convert job-description HTML to readable plain text, keeping line structure.

    Greenhouse returns HTML-escaped HTML, so unescape first.
    """
    if not raw:
        return ""
    s = raw
    if "&lt;" in s and "<" not in s[:200]:
        s = htmllib.unescape(s)
    soup = BeautifulSoup(s, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for li in soup.find_all("li"):
        li.insert_before("\n• ")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_after("\n")
    text = soup.get_text()
    text = htmllib.unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_date(value: Any) -> str | None:
    """Return an ISO-8601 UTC string from epoch-ms, epoch-s, or ISO strings."""
    if value in (None, "", 0):
        return None
    try:
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        v = str(value).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return datetime.fromisoformat(v).replace(tzinfo=timezone.utc).isoformat()
        v = v.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        pass
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def days_since(iso: str | None, now: datetime | None = None) -> float | None:
    if not iso:
        return None
    now = now or datetime.now(timezone.utc)
    try:
        return round((now - datetime.fromisoformat(iso)).total_seconds() / 86400, 1)
    except ValueError:
        return None


def make_job(**fields) -> dict:
    """Normalized job record. Every adapter returns a list of these."""
    job = {
        "company": None,
        "ats": None,
        "id": None,
        "title": "",
        "url": None,  # human-facing posting / apply URL
        "locations": [],
        "remote": None,  # True / False / None (unknown)
        "workplace_type": None,  # onsite / hybrid / remote / None
        "department": None,
        "team": None,
        "employment_type": None,
        "posted_at": None,  # best available "first posted" timestamp (ISO, UTC)
        "posted_at_source": None,  # which field it came from, for transparency
        "updated_at": None,
        "salary_text": None,
        "description": "",  # plain text
        "requisition_id": None,
        "extra": {},
    }
    job.update({k: v for k, v in fields.items() if v is not None})
    job["title"] = re.sub(r"\s+", " ", job["title"] or "").strip()
    job["locations"] = [re.sub(r"\s+", " ", l).strip() for l in job["locations"] if l and str(l).strip()]
    return job


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
