"""Where everything lives. Paths are computed on each call, so JOBHUNT_WORKSPACE can change at runtime (tests do).

Shared, committed with the repo:
  data/companies.yaml       company -> applicant tracking system registry
  templates/                starting files that `jobhunt init` copies into a workspace

Personal, never committed (workspace/ is in .gitignore):
  workspace/inventory.md    every fact about you; the only source of truth for the resume
  workspace/profile.yaml    eligibility, locations, preferences, referrals, ranking weights
  workspace/resume.yaml     resume content and role-family variants
  workspace/decisions.md    resume decisions and rejected wording, so they are not argued again
  workspace/applications.csv, email_import/, picks.yaml, watchlist.yaml, runs/, cache/, resume/
"""

from __future__ import annotations

import os
from pathlib import Path

from . import ROOT


def workspace() -> Path:
    env = os.environ.get("JOBHUNT_WORKSPACE")
    return Path(env).expanduser().resolve() if env else ROOT / "workspace"


def runs() -> Path:
    return workspace() / "runs"


def cache() -> Path:
    return workspace() / "cache"


def profile() -> Path:
    return workspace() / "profile.yaml"


def inventory() -> Path:
    return workspace() / "inventory.md"


def resume_yaml() -> Path:
    return workspace() / "resume.yaml"


def resume_dir() -> Path:
    return workspace() / "resume"


def decisions() -> Path:
    return workspace() / "decisions.md"


def applications() -> Path:
    return workspace() / "applications.csv"


def email_dir() -> Path:
    return workspace() / "email_import"


def picks() -> Path:
    return workspace() / "picks.yaml"


def watchlist() -> Path:
    return workspace() / "watchlist.yaml"


def registry() -> Path:
    return ROOT / "data" / "companies.yaml"


def templates() -> Path:
    return ROOT / "templates"


def rubrics() -> Path:
    return ROOT / "jobhunt" / "rubrics"
