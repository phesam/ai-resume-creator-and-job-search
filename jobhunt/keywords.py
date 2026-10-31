"""Which technologies the roles you want actually ask for, and whether your resume shows the ones you have.

    python3 -m jobhunt keywords --companies "Acme,Globex,Initech" [--match "software|backend"] [--limit 200]
    python3 -m jobhunt keywords --run workspace/runs/acme-2026-10-02     # use a run's candidates instead of fetching

It counts each technology across the postings, then marks where it appears for you: in a bullet, only in the skills
lines, only in the inventory, or nowhere. The useful rows are "in the inventory, not on the resume": skills the page
doesn't show yet. Inventory lines marked "do not claim", "do not list" or "unconfirmed" don't count, and neither do the
inventory template's own instructions or the fictional template resume. A term you never used is never added, however
often postings ask for it.
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

import yaml

from . import ats, ats_extra, paths, resolve  # noqa: F401 (ats_extra registers adapters)
from .terms import TERMS
from .watch import _fetch

NOT_CLAIMED = re.compile(r"do not (claim|list)|don't (claim|list)|coursework only|never used|did not use|could not defend|unconfirmed"
                         r"|^\W*(wants?|targets?|target roles|looking for)\b", re.I)


def claimable(inventory: str) -> str:
    """The inventory without lines that keep a skill off the resume, and without the template's own instructions."""
    template = set((paths.templates() / "inventory.md").read_text().splitlines())
    return "\n".join(line for line in inventory.splitlines() if line not in template and not NOT_CLAIMED.search(line))


def _where(rx: re.Pattern, bullets: str, skills: str, inventory: str) -> str:
    if rx.search(bullets):
        return "in a bullet"
    if rx.search(skills):
        return "skills line only"
    if rx.search(inventory):
        return "IN INVENTORY, NOT ON RESUME"
    return "-"


def count(jobs: list[dict]) -> list[tuple[str, int, re.Pattern]]:
    texts = [f"{j.get('title') or ''}\n{j.get('description') or ''}" for j in jobs]
    rows = [(name, sum(1 for t in texts if rx.search(t)), rx) for name, rx in TERMS]
    return sorted([r for r in rows if r[1]], key=lambda r: -r[1])


def run(a) -> int:
    jobs: list[dict] = []
    if a.run:
        jobs = json.loads((Path(a.run) / "candidates.json").read_text())
    else:
        names = [n.strip() for n in (a.companies or "").split(",") if n.strip()]
        if not names:
            print("Name companies with --companies, or a finished run with --run.", file=sys.stderr)
            return 2
        match = re.compile(a.match, re.I)
        by_company = []
        for name in names:
            try:
                _, got, errors = _fetch(name)
            except LookupError as e:
                print(e, file=sys.stderr)
                continue
            for err in errors:
                print(f"{name}: {err}", file=sys.stderr)
            by_company.append([j for j in got if match.search(j.get("title") or "")])
        # Take from each company in turn, so --limit doesn't fill up on the first one named.
        jobs = [j for row in itertools.zip_longest(*by_company) for j in row if j][: a.limit]
        need = [j for j in jobs if j.get("needs_detail")]
        if need:
            print(f"Fetching {len(need)} descriptions ...", file=sys.stderr)
            ats.fill_details(need)
    jobs = [j for j in jobs if len(j.get("description") or "") > 200]
    if not jobs:
        print("No postings with descriptions to count.", file=sys.stderr)
        return 1
    resume = yaml.safe_load(paths.resume_yaml().read_text()) if paths.resume_yaml().exists() else {}
    if ((resume or {}).get("header") or {}).get("name") == "Jordan Lee":
        resume = {}                  # still the fictional template: compare against the inventory only
    bullets = " ".join(str(b.get("text") if isinstance(b, dict) else b) for sec in ("experience", "projects")
                       for it in resume.get(sec) or [] for b in it.get("bullets") or [])
    bullets += " " + " ".join(str(it.get("org") or "") for it in resume.get("projects") or [])
    skills = " ".join(str(v) for v in (resume.get("skills") or {}).values())
    inventory = claimable(paths.inventory().read_text()) if paths.inventory().exists() else ""
    lines = [f"Counted across {len(jobs)} postings. A term you never used stays off the resume, however often it's asked for.", ""]
    lines += ["| Term | Postings | Share | Your resume |", "|---|---|---|---|"]
    for name, n, rx in count(jobs)[:45]:
        lines.append(f"| {name} | {n} | {100 * n // len(jobs)}% | {_where(rx, bullets, skills, inventory)} |")
    out = paths.workspace() / "keywords.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nSaved to {out}", file=sys.stderr)
    return 0
