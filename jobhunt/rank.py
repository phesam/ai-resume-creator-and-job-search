"""Combine deterministic signals + reviewer fit scores into a callback-likelihood ranking."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import tracker

EVERGREEN_RX = re.compile(r"early career|new grad|new graduate|university|talent (?:community|pool)|general (?:application|interest)|future opportunit|pipeline", re.I)


def candidate_yoe(profile: dict) -> float:
    start = profile.get("fulltime_start")
    if isinstance(start, str):
        start = date.fromisoformat(start)
    if not start:
        return 0.0
    return round((date.today() - start).days / 365.25, 2)


# ----------------------------------------------------------------------------- components
# The model is probability-shaped: callback ~ match quality x eligibility multipliers x chance of being seen.
# The evidence for each multiplier is in docs/JOB_SEARCH.md and docs/EVIDENCE.md; freshness follows Ashby data
# (2.5-3x as many applications arrive in a posting's first week as in any later week).

NON_INTERN_RX = re.compile(r"non-?internship|excluding internships|post-?graduat\w* experience|full[- ]time (?:professional|industry) experience", re.I)


def experience_multiplier(sig: dict, cand: float, text: str = "") -> tuple[float, str]:
    yoe = sig["yoe"]
    req = yoe["required_min"]
    highs = [m["high"] for m in yoe["mentions"] if m.get("high") is not None and m["section"] != "preferred"]
    if req is None:
        base = {"entry": 1.0, "any": 0.95, "mid": 0.85, "unspecified": 0.8, "senior": 0.25, "senior+": 0.1}.get(sig["level"], 0.75)
        return base, f"no years stated; title level '{sig['level']}'"
    if highs and max(highs) <= 2 and cand > max(highs) + 0.25:
        return 0.6, f"asks {req:g}-{max(highs):g} yrs; at {cand:g} yrs you may be past the early-career window"
    strict = bool(NON_INTERN_RX.search(text))
    if req <= max(1.0, cand):
        mult = 1.0
    elif req <= 2:
        mult = 0.75
    elif req <= 3:
        mult = 0.25 if strict else 0.4
    elif req <= 4:
        mult = 0.15
    else:
        mult = 0.05
    gap = req - cand
    label = f"asks {req:g}+ yrs; you have {cand:g}" + (" (non-internship wording)" if strict and req > cand else "")
    if gap > 0:
        label += " — stretch" if mult < 0.75 else " — small gap"
    return mult, label


def clearance_multiplier(sig: dict) -> tuple[float, str]:
    clr = sig["clearance"]
    st = clr["status"]
    notes = []
    if st == "active_required":
        mult = 0.0
        notes.append("active clearance required")
    elif st == "active_preferred":
        mult = 0.85
        notes.append("active clearance preferred (cleared applicants have an edge)")
    else:
        mult = 1.0
    if sig["us_person_required"] or st == "eligibility":
        mult *= 1.05
        notes.append("U.S.-person/clearance-eligible only: smaller pool, you qualify")
    if clr["polygraph"] and st != "active_required":
        mult *= 0.8
        notes.append("polygraph mentioned")
    return mult, "; ".join(notes) or "no clearance angle"


LOCATION_MULT = {"remote_us": 1.0, "other_us": 0.8, "unknown": 0.8}  # your regions come from profile.yaml


def _location_mults(profile: dict, great: bool = False) -> dict:
    mults = {**LOCATION_MULT, **(profile.get("location_multipliers") or {})}
    if great and profile.get("other_us_great_company") is not None:
        # "Elsewhere would have to be a great company": a role rated 5/5 for career value gets a milder cut.
        mults["other_us"] = max(mults["other_us"], float(profile["other_us_great_company"]))
    return mults


def region_order(profile: dict, great: bool = False) -> list[str]:
    """Regions from most to least preferred: by weight, ties in the order profile.yaml lists them."""
    mults = _location_mults(profile, great)
    tie_list = profile.get("region_tie_order") or [*(k for k in profile.get("location_multipliers") or {}), "remote_us", "other_us", "unknown"]
    tie = {r: i for i, r in enumerate(tie_list)}
    return sorted(mults, key=lambda r: (-mults[r], tie.get(r, len(tie))))


def best_region(regions: list[str], profile: dict, great: bool = False) -> tuple[str, float]:
    """A posting open in several places counts as its best one for you (highest weight in profile.yaml).
    `great` = the reviewer rated the role 5/5 for career value (strong brand, broad growth)."""
    mults = _location_mults(profile, great)
    order = region_order(profile, great)
    known = [r for r in regions or [] if r in mults]
    if not known:
        return (regions[0] if regions else "unknown"), mults.get("unknown", 0.9)
    best = min(known, key=order.index)
    return best, mults[best]


# How much a posting's age counts (profile.yaml -> posting_age overrides any of these).
POSTING_AGE = {
    "floor": 0.45,            # an old posting still keeps this share of its score
    "curve": [[1, 1.0], [3, 0.9], [7, 0.72], [14, 0.48], [21, 0.33], [30, 0.22], [60, 0.12]],  # [age in days up to, freshness]
    "older": 0.06,            # freshness past the last step
    "evergreen": 0.6,         # program / always-open postings
    "unknown": 0.45,          # the employer's system gives no date
    "ai_ranked_ats_stretch": 1.5,  # Greenhouse and Ashby rank by match, so strong applicants surface later
    "small_pool_stretch": 1.5,     # U.S.-person / clearance-eligible roles draw fewer applicants
}


def freshness(job: dict, sig: dict, cfg: dict | None = None) -> tuple[float, str]:
    """0..1 likelihood the application is reviewed while the req is still actively screened."""
    cfg = {**POSTING_AGE, **(cfg or {})}
    age = sig.get("age_days")
    src = job.get("posted_at_source") or ""
    if EVERGREEN_RX.search(job.get("title", "")):
        return cfg["evergreen"], "evergreen/program posting (screened continuously)"
    if age is None:
        return cfg["unknown"], "posting date unknown"
    if "30+" in src:
        age = max(age, 30)
    stretch = 1.0
    if job.get("ats") in ("greenhouse", "ashby"):
        stretch *= cfg["ai_ranked_ats_stretch"]
    if sig["us_person_required"] or sig["clearance"]["status"] == "eligibility":
        stretch *= cfg["small_pool_stretch"]
    a = age / stretch
    f = cfg["older"]
    for limit, val in cfg["curve"]:
        if a <= limit:
            f = val
            break
    note = f"posted {age:g} days ago"
    upd = sig.get("updated_age_days")
    if age > 30 and upd is not None and upd <= 7 and f < 0.33:
        f = 0.33
        note += f" (edited {upd:g} days ago: likely still active)"
    elif age > 60:
        note += " (stale: may be evergreen, filled, or a ghost posting)"
    return f, note


RECENT_GRAD_RX = re.compile(r"recently completed|recent(?:ly)? graduat|graduated within|"
                            r"new grad(?:uate)?s?\b(?!\s*(?:to|through|-|–)\s*(?:senior|staff|principal|experienced|mid))|class of 20\d\d|"
                            r"graduating (?:in|between)|graduation date between|university graduate", re.I)
ANALYST_OPS_RX = re.compile(r"\banalyst\b|\boperations\b|technician|specialist|administrator|coordinator", re.I)


CAMPUS_TITLE_RX = re.compile(r"(?:^|\s|')(?:20)?(2[6-9]|3\d)\b(?:\s*[-–/']\s*(?:20)?(?:2[6-9]|3\d))?.*\b(associate|early career|new grad|graduate|entry|university|college|campus|rotational)"
                             r"|\b(associate|early career|new grad|graduate|entry|university|college|campus)\b.*(?:^|\s|')(?:20)?(2[6-9]|3\d)\b", re.I)


def program_window_multiplier(job: dict, profile: dict) -> tuple[float, str]:
    """New-grad/campus programs aimed at recent graduates: lower odds once you're well past graduation.
    Triggered by explicit wording ("recently completed", "new grad") or a future-year campus title
    ("2027 - Associate Software Engineer", "New Graduate Engineer '26/'27")."""
    title = job.get("title") or ""
    text = title + "\n" + (job.get("description") or "")
    campus = bool(CAMPUS_TITLE_RX.search(title)) and bool(re.search(r"20(2[6-9]|3\d)|'(2[6-9]|3\d)", title))
    if not RECENT_GRAD_RX.search(text) and not campus:
        return 1.0, ""
    if not RECENT_GRAD_RX.search(text):
        # Campus-style title, but the posting states an experience range that covers the candidate
        # (e.g. "3 months - 2 years of technical work") -> it's an experience window, not a grad window.
        from .analyze import extract_yoe
        cand = candidate_yoe(profile)
        highs = [m["high"] for m in extract_yoe(job.get("description") or "")["mentions"] if m.get("high") is not None]
        if highs and max(highs) >= cand:
            return 1.0, ""
    grad = str(profile.get("graduation") or "")
    try:
        gy, gm = int(grad[:4]), int(grad[5:7] or 6)
    except ValueError:
        return 1.0, ""
    months_since = (date.today().year - gy) * 12 + (date.today().month - gm)
    start_year = re.search(r"start(?:ing)? full[- ]time in (20\d\d)|(20\d\d) (?:early career|new grad)|^(20\d\d)\b", text, re.I)
    sy = int(next(g for g in start_year.groups() if g)) if start_year else date.today().year
    months_at_start = months_since + max(0, (sy - date.today().year) * 12 - date.today().month + 6)
    if months_at_start <= 12:
        return 1.0, ""
    if months_at_start <= 18:
        return 0.65, f"program targets recent grads; you'd be ~{months_at_start} months past graduation at start (most windows are ~12)"
    return 0.5, f"program targets recent grads; you'd be ~{months_at_start} months past graduation at start (most windows are ~12)"


def salary_level_multiplier(job: dict, baseline: float | None) -> tuple[float, str]:
    """Pay band as a level signal (relative to this company's own entry-level band)."""
    sal = job["signals"]["salary"]
    if not baseline or not sal.get("min") or job["signals"]["yoe"]["required_min"] is not None:
        return 1.0, ""
    ratio = sal["min"] / baseline
    if ratio >= 1.6:
        return 0.35, f"pay band starts {ratio:.1f}x this company's entry-level band (senior-level pay)"
    if ratio >= 1.3:
        return 0.6, f"pay band starts {ratio:.1f}x this company's entry-level band (mid/senior pay)"
    return 1.0, ""


def role_alignment_multiplier(job: dict) -> tuple[float, str]:
    fam = job["signals"]["family"]
    title = job.get("title") or ""
    if fam == "core" and not ANALYST_OPS_RX.search(title):
        return 1.0, ""
    if ANALYST_OPS_RX.search(title):
        return 0.7, "analyst/operations role, not software engineering"
    if fam == "adjacent":
        return 0.85, "engineering-adjacent role (systems/test/integration), not pure software"
    return 0.8, "role family unclear"


def entry_salary_baseline(jobs: list[dict]) -> float | None:
    mins = sorted(j["signals"]["salary"]["min"] for j in jobs
                  if j["signals"]["salary"].get("min") and j["signals"]["level"] == "entry"
                  and j["signals"]["salary"]["min"] >= 40000)
    if len(mins) < 2:
        return None
    return mins[len(mins) // 2]


# ----------------------------------------------------------------------------- grouping
def _desc_hash(job: dict) -> str:
    txt = re.sub(r"\s+", " ", (job.get("description") or "")[:4000]).lower()
    return hashlib.md5(txt.encode()).hexdigest()[:10]


def group_duplicates(jobs: list[dict], profile: dict | None = None) -> list[dict]:
    """Same title + same description = one opening posted in several places. Keep the best location."""
    pref = region_order(profile or {}) + ["non_us_remote", "non_us"]
    groups: dict[tuple, list[dict]] = {}
    for j in jobs:
        k = (re.sub(r"\W+", " ", j["title"].lower()).strip(), _desc_hash(j))
        groups.setdefault(k, []).append(j)
    out = []
    for members in groups.values():
        members.sort(key=lambda j: (pref.index(j["rank"]["notes"]["location"]) if j["rank"]["notes"]["location"] in pref else len(pref),
                                    j["signals"].get("age_days") or 9999))
        lead = members[0]
        lead["duplicates"] = [{"id": m["id"], "url": m["url"], "locations": m["locations"]} for m in members[1:]]
        out.append(lead)
    return out


# ----------------------------------------------------------------------------- scoring
def referral_for(job: dict, profile: dict) -> tuple[str, str] | None:
    """profile.yaml -> referrals: [{company: Acme, contact: 'Name', job_id: '123' | title: '...'}].

    Returns (contact, scope). scope is "job" when the entry names this posting, and "company" when the
    entry names only the company: the contact can refer you to whichever role you pick there."""
    found = None
    for r in profile.get("referrals") or []:
        if not tracker.same_company(r.get("company", ""), job.get("company") or ""):
            continue
        contact = r.get("contact") or "yes"
        if r.get("job_id") and str(r["job_id"]) == str(job.get("id")):
            return contact, "job"
        if r.get("title") and tracker._tokens(r["title"]) == tracker._tokens(job.get("title")):
            return contact, "job"
        if not r.get("job_id") and not r.get("title"):
            found = (contact, "company")
    return found


# How much of the job's day-to-day work you have already done (reviewer's work_match, 0-5). A posting can
# list minimum qualifications you meet while the team's actual work is something you have never done; that is
# not a match, so this multiplies the whole score. Judgment calls; profile.yaml -> work_match_multipliers.
WORK_MATCH_MULT = {5: 1.0, 4: 0.85, 3: 0.6, 2: 0.35, 1: 0.15, 0: 0.05}
WORK_MATCH_NOTE = {3: "about half of this job is work you haven't done before",
                   2: "a different kind of engineering from your work so far",
                   1: "almost all of this job would be new to you",
                   0: "a different profession"}
# A review with no work_match (a reviewer skipped it) must not count as a full match: that would rank roles nobody
# assessed above roles that were. Estimate it from the requirements score instead. Across 159 roles scored both ways
# in the case study, the mean work-match multiplier was 0.81 at skills 5, 0.53 at 4, 0.36 at 3 and 0.21 at 2.
WORK_MATCH_ESTIMATE = {5: 0.81, 4: 0.53, 3: 0.36, 2: 0.21, 1: 0.15, 0: 0.05}
# Each extra application to one company converts worse. Huntr Q1 2026: 6.07% of applications drew a response when the
# applicant sent one to that company, 4.64% for 2-3, 3.34% for 4-7 and 1.91% for 8 or more. Correlational, and the
# only published numbers on this, so treat it as a guide. The next application would be number prior+1; its score
# is scaled by that bucket's rate over the single-application rate. profile.yaml -> company_volume_multipliers.
COMPANY_VOLUME_MULT = [(1, 1.0), (3, 0.76), (7, 0.55), (None, 0.31)]


def company_volume_multiplier(prior_apps: int, profile: dict) -> float:
    table = profile.get("company_volume_multipliers") or COMPANY_VOLUME_MULT
    for upto, mult in table:
        if upto is None or prior_apps + 1 <= upto:
            return float(mult)
    return float(table[-1][1])


def applications_past_year(company: str, today: date | None = None) -> int:
    """Applications to this company in the last 365 days."""
    since = ((today or date.today()) - timedelta(days=365)).isoformat()
    return sum(1 for h in tracker.for_company(company) if (h.get("date_applied") or "") >= since)


# When a posting states no years, the reviewer's level_fit (scope wording and pay band) stands in for them.
LEVEL_FIT_MULT = {5: 1.0, 4: 0.85, 3: 0.6, 2: 0.35, 1: 0.15, 0: 0.05}


def _step(table: dict, value: float) -> float:
    table = {int(k): float(v) for k, v in table.items()}
    return table[max(0, min(5, int(round(value))))]


def score_job(job: dict, fit: dict | None, profile: dict, cand: float, baseline: float | None = None,
              prior_apps: int = 0) -> dict:
    sig = job["signals"]
    notes = {}
    e_mult, notes["experience"] = experience_multiplier(sig, cand, job.get("description") or "")
    lvl = (fit or {}).get("level_fit")
    if sig["yoe"]["required_min"] is None and isinstance(lvl, (int, float)):
        # The reviewer read the scope wording and saw the pay band; that beats guessing from the title or pay alone.
        e_mult = _step(LEVEL_FIT_MULT, lvl)
        notes["experience"] = f"no years stated; the scope and pay band read as level fit {lvl:g}/5"
    else:
        if sig["yoe"]["required_min"] is None and sig.get("seniority_phrases"):
            e_mult = min(e_mult, 0.55)
            notes["experience"] += f"; posting asks for '{sig['seniority_phrases'][0]}'"
        s_mult, s_note = salary_level_multiplier(job, baseline)
        if s_note:
            e_mult = min(e_mult, s_mult)
            notes["experience"] += f"; {s_note}"
    wm = (fit or {}).get("work_match")
    if isinstance(wm, (int, float)):
        m_mult = _step(profile.get("work_match_multipliers") or WORK_MATCH_MULT, wm)
        notes["work_match"] = WORK_MATCH_NOTE.get(max(0, min(5, int(round(wm)))), "")
    elif fit and isinstance(fit.get("skills"), (int, float)):
        m_mult = _step(WORK_MATCH_ESTIMATE, fit["skills"])
        notes["work_match"] = "work match not assessed; estimated from the requirements score"
    else:
        m_mult, notes["work_match"] = 1.0, ""  # not reviewed at all
    w_mult, w_note = program_window_multiplier(job, profile)
    rtype = (fit or {}).get("role_type")
    prefs = profile.get("role_preferences") or {}
    if rtype and rtype in prefs:
        r_mult = float(prefs[rtype])
        r_note = "" if r_mult >= 1.0 else f"{rtype.replace('_', ' ')} role (your preference weight {r_mult:g})"
    else:
        r_mult, r_note = role_alignment_multiplier(job)
    cv = (fit or {}).get("career_value")
    lo = float(profile.get("career_value_min_multiplier", 0.8))
    cv_mult = lo + (1 - lo) * (max(0, min(5, cv)) / 5) if isinstance(cv, (int, float)) else lo + (1 - lo) * 0.6
    if isinstance(cv, (int, float)) and cv <= 2:
        r_note = (r_note + "; " if r_note else "") + "narrow/niche experience (low career value)"
    notes["program_window"], notes["role_alignment"] = w_note, r_note
    base = (profile.get("pay") or {}).get("current_base")
    sal = sig["salary"]
    if base and sal.get("max") and sal["max"] < base:
        notes["pay"] = f"pays up to ${sal['max']:,.0f}, below your ${base:,.0f} base"
    c_mult, notes["eligibility"] = clearance_multiplier(sig)
    regions = sig["location"].get("all") or [sig["location"]["best"]]
    said = (fit or {}).get("region")
    if said in _location_mults(profile):
        # The reviewer read the posting and its text contradicts the location label ("remote", but East Coast only).
        regions = [said]
        notes["location_note"] = "location taken from the posting's text, which is narrower than its label"
    best, l_mult = best_region(regions, profile, great=isinstance(cv, (int, float)) and cv >= 5)
    notes["location"] = best
    age_cfg = {**POSTING_AGE, **(profile.get("posting_age") or {})}
    f, notes["freshness"] = freshness(job, sig, age_cfg)
    seen = age_cfg["floor"] + (1 - age_cfg["floor"]) * f
    if fit:
        skills = max(0, min(5, fit.get("skills", 0))) / 5
        domain = max(0, min(5, fit.get("domain", 0))) / 5
        level = max(0, min(5, fit.get("level_fit", 3))) / 5
        comp = max(-2, min(2, fit.get("competition", 0)))
        quality = 0.6 * skills + 0.25 * domain + 0.15 * level
        k_mult = 1 + 0.08 * comp
    else:
        quality, k_mult = 0.5, 1.0
    ref = referral_for(job, profile)
    boost = 1.0
    if ref and c_mult > 0:
        # A referred application gets read whatever the posting's age, and outside the cold pile.
        seen, k_mult = 1.0, max(k_mult, 1.0)
        if ref[1] == "job":
            boost = 3.0  # ~40% of referred candidates reach an interview vs ~3% of cold applicants (Ashby)
            notes["referral"] = f"referral: {ref[0]}"
        else:
            # Usable on any role here, so it shouldn't lift them all equally: rank by fit and preference instead.
            notes["referral_company"] = ref[0]
    v_mult = 1.0
    if prior_apps and not ref:  # a referred application is not one more cold one
        v_mult = company_volume_multiplier(prior_apps, profile)
        if v_mult < 1.0:
            notes["volume"] = (f"you sent {prior_apps} application{'s' if prior_apps != 1 else ''} here in the past year; "
                               "each further cold one converts worse")
    raw = quality * m_mult * e_mult * c_mult * l_mult * seen * k_mult * w_mult * r_mult * cv_mult * v_mult * boost
    score = round(min(100.0, 100 * raw), 1)
    dealbreaker = (fit or {}).get("dealbreaker")

    def tier_of(s: float) -> str:
        if dealbreaker or c_mult == 0:
            return "X"
        return "A" if s >= 55 else "B" if s >= 42 else "C" if s >= 30 else "D"

    tier = tier_of(score)
    # A role dropped for one stated requirement (say "MS or PhD") can still be worth raising with a referrer or
    # recruiter, so keep the tier it would have had without that line.
    unblocked = None
    if dealbreaker and c_mult > 0:
        s0 = min(100.0, 100 * raw / v_mult) if v_mult < 1.0 else score
        unblocked = "A" if s0 >= 55 else "B" if s0 >= 42 else "C" if s0 >= 30 else "D"
    # How the role fits before counting earlier applications to this company: the report groups by this, so the
    # best roles to raise with a referrer stay visible even where another cold application is a poor bet.
    fit_tier = tier_of(min(100.0, 100 * raw / v_mult)) if v_mult < 1.0 else tier
    parts = {"match_quality": round(quality, 2), "work_match_x": m_mult, "experience_x": e_mult, "clearance_x": round(c_mult, 2),
             "location_x": l_mult, "seen_x": round(seen, 2), "competition_x": round(k_mult, 2),
             "program_window_x": w_mult, "role_alignment_x": r_mult, "career_x": round(cv_mult, 2),
             "company_volume_x": v_mult}
    return {"score": score, "tier": tier, "fit_tier": fit_tier, "unblocked_tier": unblocked, "parts": parts,
            "notes": notes, "reviewed": bool(fit)}


def load_fits(run_dir: Path) -> dict:
    """Reviewer rows by key (unique within a run) and by (company, id) through the run's candidates."""
    fits = {}
    for p in sorted((run_dir / "fit").glob("*.json")):
        data = json.loads(p.read_text())
        for row in data if isinstance(data, list) else data.get("jobs", []):
            if isinstance(row, dict) and row.get("key"):
                fits.setdefault(f"key:{row['key']}", row)
    return fits


def rank_run(run_dir: Path, profile: dict) -> list[dict]:
    candidates = json.loads((run_dir / "candidates.json").read_text())
    fits = load_fits(run_dir)
    cand = candidate_yoe(profile)
    applied = tracker.load()
    by_company: dict[str, list[dict]] = {}
    for j in candidates:
        by_company.setdefault(j["company"], []).append(j)
    baselines = {c: entry_salary_baseline(js) for c, js in by_company.items()}
    prior = {c: applications_past_year(c) for c in by_company}
    from .triage import dup_key
    by_dup = {}
    for j in candidates:
        f = fits.get(f"key:{j.get('key')}")
        if f and str(f.get("id")) == str(j["id"]):
            by_dup.setdefault(dup_key(j), f)
    for j in candidates:
        fit = fits.get(f"key:{j.get('key')}")
        if fit and str(fit.get("id")) != str(j["id"]):
            fit = None  # a key from an older numbering: never pin one posting's review on another
        if not fit:
            fit = by_dup.get(dup_key(j))  # identical posting elsewhere was reviewed
        j["fit"] = fit
        j["rank"] = score_job(j, fit, profile, cand, baselines.get(j["company"]), prior.get(j["company"], 0))
        j["applied"] = tracker.match(j, applied)
    grouped = group_duplicates(candidates, profile)
    grouped.sort(key=lambda j: (j["rank"]["tier"] == "X", -j["rank"]["score"]))
    (run_dir / "ranked.json").write_text(json.dumps(grouped, indent=1, default=str))
    return grouped


def rank_and_report(run_dir: Path, profile: dict, resume: str | None = None, advice: str | None = None) -> list[dict]:
    """Score a run's candidates and rewrite its REPORT.md / report.html. No network; safe to repeat."""
    meta = json.loads((run_dir / "meta.json").read_text())
    if resume:
        meta["resume"] = resume
    if advice is not None:
        meta["advice"] = advice
    elif (run_dir / "advice.md").exists():
        meta["advice"] = (run_dir / "advice.md").read_text()  # the file is the current text; meta keeps a copy
    meta.setdefault("resume", "")
    ranked = rank_run(run_dir, profile)
    meta["apply_caps"] = {c: company_cap(c, meta, profile) for c in {j["company"] for j in ranked}}
    write_report(run_dir, meta.get("label") or meta.get("company") or "Run", ranked, meta, profile)
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return ranked


# ----------------------------------------------------------------------------- report
TIER_LABEL = {
    "A": "A — Apply first (best odds)",
    "B": "B — Strong fit",
    "C": "C — Reasonable shot",
    "D": "D — Long shot",
    "X": "Not recommended after reading the posting",
}


def company_cap(company: str, meta: dict, profile: dict) -> int:
    """Suggested applications per quarter at this company (profile.yaml apply_cap; a guideline, not a proven limit)."""
    caps = profile.get("apply_cap") or {}
    n = (meta.get("per_company_fetched") or {}).get(company, meta.get("total_fetched") or 0)
    big = n >= int(caps.get("large_company_min_postings", 200))
    return int(caps.get("large_company", 8) if big else caps.get("startup", 8))


def _loc_short(j: dict, profile: dict | None = None) -> str:
    from .config import load_profile
    from .screen import load_locations, region_for
    profile = profile or load_profile()
    cache = load_locations()
    order = region_order(profile) + ["non_us"]

    def where(l: str) -> int:
        best = region_for({"locations": [l]}, cache, profile)["best"]
        return order.index(best) if best in order else 99
    locs = sorted(j.get("locations") or [], key=where)
    s = "; ".join(l.replace(", United States", "") for l in locs[:3])
    if len(locs) > 3:
        s += f" (+{len(locs) - 3})"
    if j.get("duplicates"):
        s += f" — also posted ×{len(j['duplicates'])}"
    return s


def pick_apply_now(ranked: list[dict], cap: int) -> list[dict]:
    """Top roles to apply to right away: best scores, not already applied, spread across teams."""
    chosen, seen_titles, team_count = [], set(), {}
    if cap <= 0:
        return chosen
    for j in ranked:
        if j["rank"]["tier"] not in ("A", "B") or (j.get("applied") and j["applied"].startswith("DUPLICATE")):
            continue
        t = re.sub(r"\W+", " ", j["title"].lower()).strip()
        team = (j.get("team") or j.get("department") or "").lower()
        if t in seen_titles or team_count.get(team, 0) >= 2:
            continue
        chosen.append(j)
        seen_titles.add(t)
        team_count[team] = team_count.get(team, 0) + 1
        if len(chosen) >= cap:
            break
    return chosen


def history_block(company: str, today: date | None = None) -> list[str]:
    """Markdown lines: what applications.csv knows about this company, and whether the inbox was checked."""
    from .email_import import last_import
    today = today or date.today()
    stamp = last_import()
    checked = (f"inbox checked {stamp['imported']}, covering {stamp['first']} to {stamp['last']}" if stamp
               else "email not cross-checked yet")
    history = tracker.for_company(company)
    if not history:
        return [f"**No applications to {company} on record** ({checked})."]
    groups = {"In process": [], "No reply yet": [], "Rejected": [], "Other": []}
    for h in sorted(history, key=lambda h: h.get("date_applied") or "", reverse=True):
        status = h.get("status") or "applied"
        name = h.get("title") or "(role not named in the email)"
        if status == "rejected":
            after = " after interviews" if "after interviews" in (h.get("notes") or "") else ""
            groups["Rejected"].append(f"{name}, {tracker.describe(h)}{after}")
        elif status == "applied":
            groups["No reply yet"].append(f"{name}, {tracker.describe(h)}")
        elif status in tracker.LIVE:
            groups["In process"].append(f"{name}, {tracker.describe(h)}")
        else:
            groups["Other"].append(f"{name}, {tracker.describe(h)}")
    out = [f"**Your applications to {company} on record ({len(history)}; {checked}):**"]
    out += [f"- {label} ({len(items)}): " + "; ".join(items) for label, items in groups.items() if items]
    year_ago = (today - timedelta(days=365)).isoformat()
    last_year = [h for h in history if (h.get("date_applied") or "") >= year_ago]
    if len(last_year) >= 8:
        rejected = sum(1 for h in last_year if h.get("status") == "rejected")
        out.append(f"- **Volume check:** {len(last_year)} applications to {company} in the past year, {rejected} rejected. "
                   "In Huntr's data, people who sent 8 or more applications to one company converted about 1.9% of them, "
                   "against about 6.1% for a single application. More cold applications here are unlikely to help; "
                   "a referral is the lever that changes the odds.")
    return out


def company_line(company: str, today: date | None = None) -> str:
    """One line of history for a sweep report."""
    today = today or date.today()
    history = tracker.for_company(company)
    if not history:
        return ""
    rejected = sum(1 for h in history if h.get("status") == "rejected")
    live = [h for h in history if (h.get("status") or "applied") in tracker.LIVE]
    cooling = [h for h in history if h.get("status") == "rejected" and "after interviews" in (h.get("notes") or "")
               and (tracker._age_days(h, today) or 0) <= tracker.STALE_DAYS]
    text = f"{len(history)} application(s) on record, {rejected} rejected, {len(live)} open"
    if cooling:
        text += f"; turned down after interviews on {cooling[0].get('status_date')}, so ask about a waiting period first"
    return text


def suggest_variant(ranked: list[dict], top_n: int = 8) -> str:
    votes: dict = {}
    for j in ranked[:top_n]:
        v = (j.get("fit") or {}).get("resume_focus")
        if v:
            votes[v] = votes.get(v, 0) + j["rank"]["score"]
    return max(votes, key=votes.get) if votes else "general"


def _slots(company: str, cap: int, referred: bool, today: date) -> tuple[int, list[dict]]:
    """Every application sent here in the last 90 days counts against the cap, whatever its outcome: a recruiter
    still sees it on your candidate profile."""
    recent = [h for h in tracker.for_company(company) if (h.get("date_applied") or "") >= (today - timedelta(days=90)).isoformat()]
    slots = max(0, cap - len(recent))
    if referred:
        slots = min(max(slots, 1), 2)  # a referral goes to one role: star the best one and one alternative
    return slots, recent


def write_report(run_dir: Path, label: str, ranked: list[dict], meta: dict, profile: dict | None = None) -> None:
    from .config import load_profile
    profile = profile or load_profile()
    today = date.today()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    reviewed = sum(1 for j in ranked if j.get("fit"))
    companies = sorted({j["company"] for j in ranked})
    multi = meta.get("kind") == "sweep" or len(companies) > 1
    caps = meta.get("apply_caps") or {c: company_cap(c, meta, profile) for c in companies}
    referrer = {c: next((j["rank"]["notes"]["referral_company"] for j in ranked if j["company"] == c
                         and j["rank"]["notes"].get("referral_company")), None) for c in companies}
    apply_now, slot_info = [], {}
    for c in companies:
        slots, recent = _slots(c, caps.get(c, 8), bool(referrer[c]), today)
        slot_info[c] = (slots, recent)
        apply_now += pick_apply_now([j for j in ranked if j["company"] == c], slots)
    meta["apply_now_ids"] = [[j["company"], j["id"]] for j in apply_now]
    picks = {(j["company"], j["id"]) for j in apply_now}

    md = [
        f"# {label}: ranked openings",
        "",
        f"Generated {now}. {meta.get('total_fetched', '?')} open postings fetched from {meta.get('source', '?')}; "
        + (f"{meta.get('in_regions')} in the regions asked for; " if multi and meta.get("in_regions") is not None else "")
        + f"{meta.get('candidates', len(ranked))} survived triage; {len(ranked)} unique after merging duplicate postings; "
        f"{reviewed} were read in full and fit-scored.",
        "",
    ]
    if meta.get("resume"):
        md += [f"Resume to use: **{meta['resume']}**", ""]
    if multi and meta.get("fetch_errors"):
        md += [f"**{meta['fetch_errors']} hiring-system boards could not be fetched** (see fetch_errors.json); their postings "
               "are missing from this report.", ""]
    used = ""
    if not multi:
        c = companies[0] if companies else (meta.get("company") or label)
        history = history_block(c)
        if referrer.get(c):
            history.append(f"- **Referral on file: {referrer[c]}.** A referral is used on one role, so the scores below leave out "
                           "posting age and applicant-pool pressure and rank by fit and your preferences. About 40% of referred "
                           "candidates reach an interview, against about 3% of cold applicants. Send your referrer the job ID "
                           "of the role you pick.")
        meta["history_md"] = "\n".join(history)
        md += [meta["history_md"], ""]
        slots, recent = slot_info.get(c, (caps.get(c, 8), []))
        cap = caps.get(c, 8)
        n = len(recent)
        if referrer.get(c):
            used = (f"You have a referral here, so use it on your best role (★) rather than sending cold applications. "
                    f"You've sent {n} application{'s' if n != 1 else ''} to {c} in the last 90 days.")
        elif not recent:
            used = f"Pick up to {cap}."
        elif slots == 0:
            used = (f"You've sent {n} application{'s' if n != 1 else ''} to {c} in the last 90 days, which is at or over that "
                    "guideline, so hold off on new cold applications here unless a posting from this week fits clearly better "
                    "than what you've already sent, or you get a referral.")
        else:
            used = f"{n} of your ~{cap} at {c} are already used (applications in the last 90 days), so pick up to {slots}."
        cooling = [h for h in tracker.for_company(c) if h.get("status") == "rejected"
                   and "after interviews" in (h.get("notes") or "") and (tracker._age_days(h, today) or 0) <= tracker.STALE_DAYS]
        if cooling:
            used += (f" You were turned down here after interviews on {cooling[0].get('status_date')}. Companies usually expect "
                     "about 6 months before a new application, so treat the ★ picks as roles to raise with a recruiter or a "
                     "referrer, not as cold applications.")
    else:
        lines = [f"- **{c}:** {company_line(c)}" + (f" Referral on file: {referrer[c]}." if referrer[c] else "")
                 for c in companies if company_line(c) or referrer[c]]
        if lines:
            md += ["## Your history at these companies", "", *lines, ""]
        meta["history_md"] = "\n".join(lines)
        used = "★ marks the best roles at each company, up to that company's suggested number of applications."
    meta["slots_note"] = used
    if meta.get("advice"):
        md += [meta["advice"], ""]
    vol = min((j["rank"]["parts"].get("company_volume_x", 1.0) for j in ranked), default=1.0)
    md += ["## How to use this list", "",
           "Every role below passed triage and was read in full against your inventory. The suggested number of "
           "applications per company each quarter is a guideline, not a proven limit (see docs/JOB_SEARCH.md). "
           f"{used} Choose whichever you prefer from the strong matches.", ""]

    def head(j):
        return f"**{j['company']}** · " if multi else ""

    def detailed(rows, start_i=1):
        out = []
        for i, j in enumerate(rows, start_i):
            fit = j.get("fit") or {}
            sig = j["signals"]
            posted = (j.get("posted_at") or "")[:10] or "?"
            star = "★ " if (j["company"], j["id"]) in picks else ""
            applied = ""
            if j.get("applied"):
                applied = f" **⚠ {j['applied']}**" if j["applied"].startswith("DUPLICATE") else f" _(ℹ {j['applied']})_"
            out.append(f"{i}. {star}{head(j)}**[{j['title']}]({j['url']})** — {_loc_short(j, profile)} · posted {posted} · "
                       f"score {j['rank']['score']} · resume: {fit.get('resume_focus', 'general')}{applied}")
            if fit.get("why"):
                out.append(f"   - Why: {fit['why']}")
            if fit.get("hooks"):
                out.append(f"   - Lead with: {'; '.join(fit['hooks'])}")
            risks = [n for n in (j["rank"]["notes"].get("work_match"), j["rank"]["notes"].get("program_window"),
                                 j["rank"]["notes"].get("role_alignment")) if n]
            risks += list(fit.get("gaps") or [])
            if risks:
                out.append(f"   - Risks/gaps: {'; '.join(risks)}")
            out.append(f"   - Experience: {j['rank']['notes']['experience']}; {j['rank']['notes']['freshness']}")
            if j["rank"]["notes"].get("referral"):
                out.append(f"   - **{j['rank']['notes']['referral']}**")
            if sig["salary"].get("text"):
                pn = j["rank"]["notes"].get("pay")
                out.append(f"   - Pay: {sig['salary']['text']}" + (f" ({pn})" if pn else ""))
        return out

    def group(j):
        return j["rank"].get("fit_tier") or j["rank"]["tier"]

    strong = [j for j in ranked if group(j) in ("A", "B")]
    look = [j for j in ranked if group(j) == "C"]
    longshot = [j for j in ranked if group(j) == "D"]
    nope = [j for j in ranked if group(j) == "X"]
    title = "Best fits, to raise with a referrer" if vol < 1.0 else "Strong matches: choose from these"
    md += [f"## {title} ({len(strong)})", ""]
    md += detailed(strong) if strong else ["(none this run)"]
    md.append("")
    if any(j.get("ats") == "greenhouse" for j in strong):
        md += ["Tip: Greenhouse lets you mark one application a month as your \"Dream Job\". Use it on your top pick.", ""]
    near = [j for j in nope if j["rank"].get("unblocked_tier") in ("A", "B")]
    if near:
        md += [f"## Strong match except for one stated requirement ({len(near)})", "",
               "These would rank among the strong matches, but each posting states one requirement you don't meet. A cold "
               "application is likely to be filtered on that line, so ask a referrer or the recruiter whether it is firm "
               "before applying.", ""]
        for i, j in enumerate(near, 1):
            fit = j.get("fit") or {}
            posted = (j.get("posted_at") or "")[:10] or "?"
            md.append(f"{i}. {head(j)}**[{j['title']}]({j['url']})** — {_loc_short(j, profile)} · posted {posted} · "
                      f"score without that line {j['rank']['score']}")
            md.append(f"   - The requirement: {fit.get('dealbreaker')}")
            if fit.get("why"):
                md.append(f"   - Why it fits otherwise: {fit['why']}")
        md.append("")
        nope = [j for j in nope if j not in near]
    md += [f"## Also worth a look ({len(look)})", ""]
    md += detailed(look) if look else ["(none)"]
    md.append("")
    for t, rows in ((f"Long shots ({len(longshot)})", longshot), (f"Not recommended after reading the posting ({len(nope)})", nope)):
        md += [f"## {t}", ""]
        for i, j in enumerate(rows, 1):
            fit = j.get("fit") or {}
            posted = (j.get("posted_at") or "")[:10] or "?"
            reason = fit.get("dealbreaker") or (fit.get("gaps") or [j["rank"]["notes"]["experience"]])[0]
            md.append(f"{i}. {head(j)}[{j['title']}]({j['url']}) — {_loc_short(j, profile)} · posted {posted} · "
                      f"score {j['rank']['score']} — {reason}")
        md.append("")
    md += [
        "## How the score works",
        "",
        "score = 100 × match quality (0.6 required qualifications + 0.25 domain hooks + 0.15 level fit) "
        "× work match (how much of the job's day-to-day work you have already done: 1.0, 0.85, 0.6, 0.35, 0.15) "
        "× experience (1.0 at or below your years, 0.75 at 2+, 0.4 at 3+, 0.15 at 4+; the reviewer's level fit when no years are stated) "
        "× clearance/citizenship × location (your region weights) × chance of being seen (posting age; off when you have a referral) "
        "× competition × role preference × career value × repeat applications (off by default). "
        "It is a ranking score, not a probability. Tiers: A ≥55, B ≥42, C ≥30. The weights are in profile.yaml; "
        "the evidence for each is in docs/JOB_SEARCH.md.",
    ]
    (run_dir / "REPORT.md").write_text("\n".join(md) + "\n")
    (run_dir / "report.html").write_text(_html_report(label, ranked, meta, now, multi, picks, profile))


def _html_report(label: str, ranked: list[dict], meta: dict, now: str, multi: bool, picks: set, profile: dict) -> str:
    esc = html.escape
    rows = []
    for j in ranked:
        fit = j.get("fit") or {}
        r = j["rank"]
        risks = [n for n in (r["notes"].get("work_match"),) if n] + list(fit.get("gaps") or [])
        if fit.get("dealbreaker"):
            risks.insert(0, "Dealbreaker: " + fit["dealbreaker"])
        applied = ""
        if j.get("applied"):
            cls = "applied" if j["applied"].startswith("DUPLICATE") else "note"
            applied = f'<span class="{cls}">{esc(j["applied"])}</span>'
        star = "★ " if (j["company"], j["id"]) in picks else ""
        company = f'<td>{esc(j["company"])}</td>' if multi else ""
        rows.append(
            f'<tr class="t{r["tier"]}"><td class="tier">{r["tier"]}</td><td class="score">{r["score"]}</td>{company}'
            f'<td>{star}<a href="{esc(j["url"])}" target="_blank" rel="noreferrer">{esc(j["title"])}</a>{applied}'
            f'<div class="why">{esc(fit.get("why", ""))}</div>'
            f'{"<div class=risk>" + esc("; ".join(risks)) + "</div>" if risks else ""}</td>'
            f'<td>{esc(_loc_short(j, profile))}</td><td class="nowrap">{esc((j.get("posted_at") or "")[:10])}</td>'
            f'<td class="small">{esc(r["notes"]["experience"])}</td></tr>'
        )
    intro = _mini_md(meta.get("advice", ""))
    hist = _mini_md(meta.get("history_md", ""))
    company_th = "<th>Company</th>" if multi else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(label)} openings</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--muted:#6e6e73;--line:#e5e5ea;--a:#e8f5ec;--b:#eef4fb;--c:#fbf7ea;--d:#f6f6f6;--x:#fbeeee}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151516;--fg:#f2f2f7;--muted:#a1a1a6;--line:#2c2c2e;--a:#173022;--b:#172433;--c:#2f2a17;--d:#202022;--x:#331b1b}}}}
body{{font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:24px auto;max-width:1200px;padding:0 16px;background:var(--bg);color:var(--fg)}}
h1{{font-size:22px;margin:0 0 4px}} .meta{{color:var(--muted);margin-bottom:16px}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid var(--line);padding:8px;vertical-align:top;text-align:left}}
.tA{{background:var(--a)}} .tB{{background:var(--b)}} .tC{{background:var(--c)}} .tD{{background:var(--d)}} .tX{{background:var(--x);opacity:.75}}
.tier{{font-weight:700;width:28px}} .score{{width:44px}} .why{{color:var(--muted);margin-top:3px}} .risk{{color:#b3261e;margin-top:3px;font-size:12px}}
.small{{font-size:12px;color:var(--muted);max-width:220px}} .nowrap{{white-space:nowrap}} a{{color:inherit;font-weight:600}}
.applied{{margin-left:8px;font-size:11px;background:#b3261e;color:#fff;border-radius:4px;padding:1px 6px}}
.note{{margin-left:8px;font-size:11px;border:1px solid var(--line);color:var(--muted);border-radius:4px;padding:1px 6px}}
.intro{{border:1px solid var(--line);border-radius:8px;padding:8px 14px;margin-bottom:16px}} .intro li{{margin:4px 0}}
@media (max-width:700px){{td.small,th:last-child{{display:none}}}}
</style></head><body><h1>{esc(label)}: ranked openings</h1>
<div class="meta">Generated {esc(now)} · {esc(str(meta.get('total_fetched', '?')))} postings fetched · {len(ranked)} ranked{(' · resume: ' + esc(meta['resume'])) if meta.get('resume') else ''}</div>
<div class="intro">{hist}{intro}<p>{esc(meta.get('slots_note', ''))} ★ marks suggested picks. Every row was read in full.</p></div>
<div class="scroll"><table><thead><tr><th>Tier</th><th>Score</th>{company_th}<th>Role</th><th>Location</th><th>Posted</th><th>Experience fit</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></body></html>"""


def _mini_md(text: str) -> str:
    """Tiny markdown subset for the advice block: headings, bullets, **bold**, [links](url)."""
    out, in_list = [], False
    for raw in (text or "").splitlines():
        line = html.escape(raw.strip())
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", line)
        line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', line)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("#"):
            out.append(f"<h3>{line.lstrip('#').strip()}</h3>")
        elif line:
            out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)
