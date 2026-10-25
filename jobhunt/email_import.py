"""Merge application events found in email into applications.csv.

Events live in workspace/email_import/*.jsonl, one JSON object per line:
  {"date": "2026-09-18", "company": "Acme Robotics", "title": "Software Engineer (Platform Team)",
   "kind": "applied" | "rejected" | "interview" | "assessment", "sender": "...", "msg_id": "...", "subject": "..."}
The track-applications skill explains how an agent produces them from Gmail (read-only).

python3 -m jobhunt applied import-email [folder]

Email is the authoritative record. Email rows are rebuilt from the event files on every run, so the
import is safe to repeat after adding newer event files. Manual logs (`applied add`) are kept, and when the
inbox also shows the same application, the manual row's job id, link and notes move onto the email row.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from . import paths, tracker

STAMP = "_last_import.json"
KINDS = ("applied", "assessment", "interview", "rejected")  # also the order of events that share a day


def load_events(folder: Path, skip_prefix: str | None = None) -> list[dict]:
    seen, events = set(), []
    for p in sorted(folder.glob("*.jsonl")):
        if skip_prefix and p.name.startswith(skip_prefix):
            continue
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except ValueError:
                print(f"skipped {p.name}:{n} (not JSON)", file=sys.stderr)
                continue
            if e.get("kind") not in KINDS or not (e.get("company") or "").strip() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e.get("date") or ""):
                print(f"skipped {p.name}:{n} (needs date, company and a known kind)", file=sys.stderr)
                continue
            key = e.get("msg_id") or (e["date"], e["company"], e.get("title"), e["kind"])
            if key in seen:
                continue
            seen.add(key)
            events.append(e)
    events.sort(key=lambda e: (e["date"], KINDS.index(e["kind"])))
    return events


def _days(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def _title(e: dict) -> str:
    return re.sub(r"\s+", " ", (e.get("title") or "")).strip(" #")  # some systems prefix titles with '#'


def _new(e: dict, status: str, note: str = "") -> dict:
    return {"date_applied": e["date"], "company": e["company"].strip(), "title": _title(e),
            "job_id": "", "url": "", "location": "", "status": status, "status_date": e["date"], "source": "email",
            "resume": "", "_auto": [note] if note else [], "_n": 1, "_interviewed": status == "interview"}


def _targets(open_rows: list[dict], title: str, single: bool) -> list[dict]:
    """Which open application(s) at this company does a later email refer to?"""
    if title:
        hit = [r for r in open_rows if tracker.same_title(r["title"], title)] \
            or [r for r in open_rows if tracker.similar_title(r["title"], title)]
        if not hit:
            blank = [r for r in open_rows if not r["title"]]
            if blank:  # this email names the role a confirmation left out; replies usually follow the latest application
                blank[-1]["title"] = title
                hit = blank[-1:]
        return hit[-1:] if single else hit
    staged = [r for r in open_rows if r["status"] in ("interview", "assessment")]
    if staged:  # no role named: an application already in process is the likeliest subject
        return staged[-1:]
    if len(open_rows) > 1:  # a guess: say so
        if single:
            open_rows[-1]["_auto"].append("that email did not name the role; matched to the latest open application")
        else:
            open_rows[0]["_auto"].append("the rejection email did not name the role; matched to the oldest open application")
    return open_rows[-1:] if single else open_rows[:1]


def build_rows(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for e in events:
        title = _title(e)
        mine = [r for r in rows if tracker.same_company(r["company"], e["company"])]
        open_rows = [r for r in mine if r["status"] in tracker.LIVE]
        if e["kind"] == "applied":
            twin = next((r for r in open_rows if title and r["date_applied"] == e["date"] and tracker.same_title(r["title"], title)), None)
            if twin:
                twin["_n"] += 1
            else:
                rows.append(_new(e, "applied"))
        elif e["kind"] == "rejected":
            hit = _targets(open_rows, title, single=False)
            if not hit:
                repeat = any(r["status"] == "rejected" and _days(r["status_date"], e["date"]) <= 14
                             and (not title or not r["title"] or tracker.same_title(r["title"], title)) for r in mine)
                if not repeat:
                    rows.append(_new(e, "rejected", "rejection email; no application confirmation on record"))
                continue
            for r in hit:
                r["status"], r["status_date"] = "rejected", e["date"]
        else:  # interview or assessment
            hit = _targets(open_rows, title, single=True)
            if not hit:
                rows.append(_new(e, e["kind"], "no application confirmation on record"))
                continue
            r = hit[0]
            if title:  # a later email names this role, so an earlier guess about it is confirmed
                r["_auto"] = [n for n in r["_auto"] if "did not name the role" not in n]
            if e["kind"] == "interview" or r["status"] == "applied":
                r["status"] = e["kind"]
            r["status_date"] = e["date"]
            r["_interviewed"] = r["_interviewed"] or e["kind"] == "interview"
    for r in rows:
        if r["_n"] > 1:
            r["_auto"].append(f"{r['_n']} confirmation emails that day")
        if r["status"] == "rejected" and r["_interviewed"]:
            r["_auto"].append("rejected after interviews")
    return rows


def _key(r: dict) -> tuple:
    return (tuple(tracker._company_tokens(r.get("company"))), tracker._tokens(r.get("title")), r.get("date_applied"))


def merge(existing: list[dict], email_rows: list[dict], today: str) -> list[dict]:
    """Combine rebuilt email rows with what was already in the tracker."""
    old_email = {_key(r): r for r in existing if (r.get("source") or "").startswith("email")}
    others = [r for r in existing if not (r.get("source") or "").startswith("email")]
    for r in email_rows:  # keep what earlier runs or you attached to this application
        prev = old_email.get(_key(r))
        r["_manual"] = ""
        if not prev and not r["title"]:
            # A manual log named the role this confirmation email left out; the name was stored on the email row.
            prev = next((o for o in old_email.values() if o.get("source") == "email+manual"
                         and o.get("date_applied") == r["date_applied"]
                         and tracker.same_company(o.get("company"), r["company"])), None)
            if prev:
                r["title"] = prev.get("title") or ""
        if prev:
            for k in ("job_id", "url", "location", "resume"):
                r[k] = r[k] or prev.get(k) or ""
            r["_manual"] = (prev.get("notes") or "").partition(" | ")[2]
            r["source"] = prev.get("source") or "email"
            if prev.get("status") == "rejected" and r["status"] in tracker.LIVE:
                r["status"], r["status_date"] = "rejected", prev.get("status_date") or r["status_date"]
    kept = []
    for m in others:
        status = m.get("status") or "applied"
        peers = [r for r in email_rows if tracker.same_company(r["company"], m.get("company"))]
        hit = [r for r in peers if tracker.same_title(r["title"], m.get("title"))]
        if not hit and m.get("date_applied"):
            # The confirmation email named no role: a manual log from the same days supplies it (one application, not two).
            hit = [r for r in peers if not r["title"] and r["source"] == "email" and _days(r["date_applied"], m["date_applied"]) <= 3]
            for r in hit[-1:]:
                r["title"] = m.get("title") or ""
        if hit:  # a manual log of an application the inbox also shows: keep its id, link and notes
            r = hit[-1]
            for k in ("job_id", "url", "location", "resume"):
                r[k] = r[k] or m.get(k) or ""
            r["_manual"] = r["_manual"] or m.get("notes") or ""
            r["source"] = "email+manual"
            if status == "rejected" and r["status"] in tracker.LIVE:
                r["status"] = "rejected"
            continue
        kept.append(m)
    for r in email_rows:
        auto = "; ".join(dict.fromkeys(r["_auto"]))
        r["notes"] = auto + (" | " + r["_manual"] if r["_manual"] else "")
    email_rows.sort(key=lambda r: (r["date_applied"], r["company"].lower()), reverse=True)
    return email_rows + kept


def summarize(rows: list[dict]) -> dict:
    confirmed = [r for r in rows if (r.get("source") or "").startswith("email")]
    by_status: dict = {}
    for r in confirmed:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    progressed = [r for r in confirmed if r["status"] in ("assessment", "interview") or "after interviews" in (r.get("notes") or "")]
    return {
        "applications_confirmed_by_email": len(confirmed),
        "companies": len({tuple(tracker._company_tokens(r["company"])) for r in confirmed}),
        "by_status": by_status,
        "reached_assessment_or_interview": len(progressed),
        "manual_logs_without_email": len(rows) - len(confirmed),
    }


def run(folder: Path | None = None) -> dict:
    folder = Path(folder or paths.email_dir())
    events = load_events(folder)
    if not events:
        raise SystemExit(f"No events found in {folder}/*.jsonl")
    today = date.today().isoformat()
    rows = merge(tracker.load(), build_rows(events), today)
    tracker.save(rows)
    # Files named extra*.jsonl hold one-off finds (a search for one company by name, older mail); they are
    # imported like the rest but don't count toward the period the systematic searches covered.
    swept = load_events(folder, skip_prefix="extra") or events
    stamp = {"imported": today, "events": len(events), "first": swept[0]["date"], "last": swept[-1]["date"]}
    (folder / STAMP).write_text(json.dumps(stamp, indent=1))
    return {**summarize(rows), **stamp}


def last_import(folder: Path | None = None) -> dict | None:
    p = Path(folder or paths.email_dir()) / STAMP
    return json.loads(p.read_text()) if p.exists() else None
