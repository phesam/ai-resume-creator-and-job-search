"""Scan the files git tracks (or would track) for your personal terms before you commit or publish.

    python3 -m jobhunt privacy-check [--terms FILE]

Terms come from workspace/privacy_terms.txt (one per line; # starts a comment), which lives in the ignored
workspace folder, so the list itself is never committed. Put in your name, email, phone number, LinkedIn and GitHub
handles, employers, project names, school, and anything else you would not want public. The scan also flags
anything that looks like an email address or a US phone number outside the allowlist below.

Exit code 1 means something was found: fix it before committing. Git history keeps what was committed, so a term
removed in a later commit is still public.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from . import ROOT, paths

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
ALLOWED_EMAILS = {"noreply@anthropic.com", "jordan.lee@example.com", "you@example.com"}
ALLOWED_PHONES = {"(555) 010-0199", "555-010-0199"}
EXAMPLE_DOMAIN = re.compile(r"@(?:[\w-]+\.)*example\.(?:com|org|net|edu)$", re.I)  # reserved for documentation
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2"}


def tracked_files() -> list[Path]:
    """Files git would commit: tracked plus untracked-but-not-ignored."""
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return [ROOT / line for line in out.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and "workspace" not in p.parts and ".git" not in p.parts]


def load_terms(path: Path | None) -> list[str]:
    path = path or paths.workspace() / "privacy_terms.txt"
    if not path.exists():
        return []
    return [t.strip() for t in path.read_text().splitlines() if t.strip() and not t.strip().startswith("#")]


def scan(terms: list[str], files: list[Path] | None = None) -> list[str]:
    hits = []
    rx = [(t, re.compile(re.escape(t), re.I)) for t in terms]
    for f in files or tracked_files():
        if f.suffix.lower() in SKIP_SUFFIXES or not f.is_file():
            continue
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        rel = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
        for n, line in enumerate(text.splitlines(), 1):
            for t, r in rx:
                if r.search(line):
                    hits.append(f"{rel}:{n}: term '{t}'")
            for m in EMAIL.findall(line):
                if m.lower() not in ALLOWED_EMAILS and not EXAMPLE_DOMAIN.search(m) \
                        and not re.search(r"\.(png|jpg|svg|js|py|md)$", m):
                    hits.append(f"{rel}:{n}: email-like '{m}'")
            for m in PHONE.findall(line):
                if m not in ALLOWED_PHONES and not m.startswith(("555", "(555")):
                    hits.append(f"{rel}:{n}: phone-like '{m}'")
    return hits


def run(terms_file: str | None = None) -> int:
    terms = load_terms(Path(terms_file) if terms_file else None)
    if not terms:
        print("No terms listed. Add your personal terms to workspace/privacy_terms.txt (one per line) and run again; "
              "only the email and phone patterns were checked.", file=sys.stderr)
    hits = scan(terms)
    for h in hits:
        print(h)
    print(f"{len(hits)} finding(s) in {len(tracked_files())} files.", file=sys.stderr)
    return 1 if hits else 0
