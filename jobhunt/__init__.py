"""jobhunt: find every job at a company (or across many), triage it, rank it by callback odds, build the resume,
and track applications.

Run from the repository root:  python3 -m jobhunt --help
Your own files (inventory, profile, resume, history, runs) live in the workspace folder, `workspace/` by default
or wherever JOBHUNT_WORKSPACE points. See jobhunt/paths.py.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
