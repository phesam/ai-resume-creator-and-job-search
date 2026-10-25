"""Load workspace/profile.yaml with defaults, and turn its `regions` list into what the rest of the code uses.

Regions are yours to define. Each one has a key, a label, a plain-English `covers` line the AI location screener
reads, optional `hint_places` (city names the offline regex hint matches), an optional `broad_match` regex for
strings worth sending to the screener in a sweep (for example "california|\\bca\\b"), and a `weight` that
multiplies a posting's score. Four keys are built in and need no definition:

  remote_us   remote within the US          weight: remote_weight
  other_us    any other US location         weight: elsewhere_weight
  unknown     the posting gives no usable location
  non_us      outside the US (postings only abroad are dropped)
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import yaml

from . import paths

BUILTIN = ("remote_us", "other_us", "unknown", "non_us")

DEFAULTS: dict = {
    "name": "",
    "summary": "",
    "target_roles": "Software engineering roles: software, full-stack, frontend, backend, platform, infrastructure, "
                    "data or ML engineering, embedded and firmware software, and new-grad or early-career software programs.",
    "citizenship": "",
    "clearance": "none",
    "fulltime_start": None,
    "graduation": None,
    "eligibility": {
        "max_required_years": 3,
        "exclude_employment_types": ["contract", "temporary", "part-time", "part time", "intern"],
    },
    "regions": [],
    "remote_weight": 1.0,
    "elsewhere_weight": 0.8,
    "elsewhere_great_company_weight": None,
    "unknown_weight": 0.8,
    "posting_age": {},
    "role_preferences": {"software": 1.0, "software_physical": 1.0, "forward_deployed": 0.95, "systems_engineering": 0.9,
                         "other": 0.8, "operations": 0.7, "test": 0.7, "analyst": 0.65},
    "work_match_multipliers": {5: 1.0, 4: 0.85, 3: 0.6, 2: 0.35, 1: 0.15, 0: 0.05},
    "career_value_min_multiplier": 0.7,
    "company_volume_multipliers": [[1, 1.0], [3, 1.0], [7, 1.0], [None, 1.0]],
    "apply_cap": {"large_company": 8, "startup": 8, "large_company_min_postings": 200},
    "referrals": [],
    "pay": {},
    "resume_variants": {"general": {"label": "full-stack, product and platform roles", "default": True}},
    "company_rules": [],
    "apply_list": {
        "per_company_max": 8,
        "referral_roles_per_company": 3,
        "local_table": [],
        "uncapped_companies": [],
        "old_posting_days": 120,
        "recent_applications_days": 90,
    },
}


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def normalize(raw: dict | None) -> dict:
    """Defaults + derived fields. Safe to call on an already-normalized profile."""
    p = _merge(DEFAULTS, raw or {})
    p["work_match_multipliers"] = {int(k): float(v) for k, v in p["work_match_multipliers"].items()}
    # The triage code reads this older shape.
    p["triage"] = {"max_required_yoe": p["eligibility"].get("max_required_years", 3),
                   "exclude_employment_types": p["eligibility"].get("exclude_employment_types")}
    regions = []
    for r in p.get("regions") or []:
        key = str(r.get("key") or "").strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in BUILTIN:
            raise ValueError(f"profile.yaml regions: bad or reserved key {key!r} (use lowercase letters, digits, _)")
        regions.append({"key": key, "label": r.get("label") or key, "covers": r.get("covers") or "",
                        "hint_places": [str(x).lower() for x in (r.get("hint_places") or [])],
                        "broad_match": r.get("broad_match") or "", "weight": float(r.get("weight", 1.0))})
    p["regions"] = regions
    mults = {r["key"]: r["weight"] for r in regions}
    mults.update({"remote_us": float(p["remote_weight"]), "other_us": float(p["elsewhere_weight"]),
                  "unknown": float(p["unknown_weight"])})
    mults.update({k: float(v) for k, v in (raw or {}).get("location_multipliers", {}).items()})  # explicit override
    p["location_multipliers"] = mults
    if p.get("elsewhere_great_company_weight") is not None:
        p["other_us_great_company"] = float(p["elsewhere_great_company_weight"])
    p["region_tie_order"] = [r["key"] for r in regions] + ["remote_us", "other_us", "unknown"]
    return p


def region_labels(profile: dict) -> dict:
    labels = {r["key"]: r["label"] for r in profile.get("regions") or []}
    labels.update({"remote_us": "Remote (US)", "other_us": "Elsewhere in the US", "unknown": "Location unclear",
                   "non_us": "Outside the US"})
    return labels


def region_keys(profile: dict) -> tuple:
    return tuple(r["key"] for r in profile.get("regions") or []) + BUILTIN


_CACHE: dict = {}


def load_profile(path: Path | None = None) -> dict:
    """The workspace profile, normalized. Falls back to the template so tools still run before `jobhunt init`."""
    path = Path(path) if path else paths.profile()
    if not path.exists():
        path = paths.templates() / "profile.yaml"
    key = (str(path), path.stat().st_mtime if path.exists() else 0)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = normalize(yaml.safe_load(path.read_text()) if path.exists() else {})
    return copy.deepcopy(_CACHE[key])


def region_hints(profile: dict | None = None) -> list[tuple[str, re.Pattern]]:
    """(key, regex) per user region, most preferred first, for the offline location hint."""
    profile = profile if profile is not None else load_profile()
    out = []
    for r in profile.get("regions") or []:
        if r["hint_places"]:
            out.append((r["key"], re.compile(r"\b(?:" + "|".join(re.escape(n) for n in r["hint_places"]) + r")\b", re.I)))
    return out


def broad_matchers(profile: dict) -> list[re.Pattern]:
    return [re.compile(r["broad_match"], re.I) for r in profile.get("regions") or [] if r.get("broad_match")]


def candidate_brief(profile: dict) -> str:
    """The short text screeners and reviewers read about the candidate before the rubric."""
    lines = [f"# Candidate brief: {profile.get('name') or 'the candidate'}", ""]
    if profile.get("summary"):
        lines += [profile["summary"].strip(), ""]
    lines += ["## Roles to keep at the title screen", "", (profile.get("target_roles") or "").strip(), ""]
    lines += ["## Location regions (classify every location string into exactly one key)", ""]
    for r in profile.get("regions") or []:
        lines.append(f"- `{r['key']}`: {r['label']}" + (f". Covers: {r['covers']}" if r["covers"] else ""))
    lines += ["- `remote_us`: remote within the US, or US-wide.",
              "- `other_us`: any other US location, including Hawaii, Alaska and territories.",
              "- `non_us`: outside the US.",
              "- `unknown`: genuinely ambiguous strings (\"Multiple Locations\", \"Hybrid\").", ""]
    variants = profile.get("resume_variants") or {}
    if variants:
        lines += ["## Resume variants (for `resume_focus`)", ""]
        lines += [f"- `{k}`: {v.get('label', '')}" for k, v in variants.items()]
        lines.append("")
    return "\n".join(lines)
