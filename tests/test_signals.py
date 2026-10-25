"""Regression tests for the deterministic layer, using real wording from many companies and ATS formats.

Run: python3 -m pytest tests -q
Rule of thumb: when a run surfaces a misclassification at a new company, add the example here first, then fix.
"""

import pytest

from jobhunt.analyze import explicitly_non_us, extract_clearance, extract_yoe, location_class, title_level  # noqa: E402
from jobhunt.screen import parse_compact  # noqa: E402
from jobhunt.tracker import match  # noqa: E402


# --------------------------------------------------------------------------- locations (structural non-US check)
@pytest.mark.parametrize("locs,expected", [
    (["Sydney, New South Wales, Australia"], True),            # Greenhouse
    (["London, England, United Kingdom"], True),
    (["Toronto, Ontario, Canada"], True),
    (["Abu Dhabi, United Arab Emirates"], True),
    (["United States-Florida-Melbourne"], False),               # Workday (NG): Melbourne, FL
    (["Melbourne, FL"], False),
    (["Dublin, CA"], False),
    (["London"], False),                                         # city only: not explicit -> leave to the screener
    (["Remote"], False),
    (["Costa Mesa, California, United States", "Sydney, New South Wales, Australia"], False),  # any US location keeps it
    (["US-CA-Irvine"], False),                                   # iCIMS format
    ([], False),
])
def test_explicitly_non_us(locs, expected):
    assert explicitly_non_us(locs) is expected


@pytest.mark.parametrize("loc,expected", [
    # region keys and city lists come from templates/profile.yaml (home = Southern California)
    ("Costa Mesa, California, United States", "home"),
    ("Hawthorne, CA", "home"),
    ("United States-California-Redondo Beach", "home"),
    ("Irvine, California, United States of America", "home"),
    ("Ontario, California, United States", "home_outer"),
    ("United States-California-Palmdale", "home_outer"),
    ("Toronto, Ontario, Canada", "non_us"),
    ("San Jose, CA", "bay_area"),
    ("Remote - US", "remote_us"),
    ("Lancaster, PA", "other_us"),
    ("Seattle, Washington, United States", "other_us"),
])
def test_location_class_fallback(loc, expected):
    assert location_class([loc], None)["best"] == expected


# --------------------------------------------------------------------------- title levels across ladders
@pytest.mark.parametrize("title,expected", [
    ("2026 Early Career Software Engineer", "entry"),            # Anduril
    ("Associate Software Engineer / Software Engineer", "entry"),  # Northrop
    ("Software Engineer Asc", "unspecified"),                     # Lockheed abbreviation: left to the screener/review
    ("Software Development Engineer II", "mid"),                  # Amazon
    ("Software Engineer III, Google Cloud", "senior"),            # Google
    ("Software Engineer 2/3", "mid"),                             # Northrop dual level
    ("Software Engineer, Level 4", "senior+"),
    ("Senior Software Engineer", "senior"),
    ("Staff Software Engineer", "staff+"),
    ("Principal Software Engineer", "staff+"),
    ("Engineering Manager, Platform", "manager"),
    ("Software Engineer, Vehicle Software, V&V", "unspecified"),  # "V&V" is not a roman numeral
    ("Software Engineer (I&T)", "unspecified"),
    ("Software Engineer Intern - Summer 2027", "intern"),
    ("Internal Tools Engineer", "unspecified"),                   # "Internal" is not "intern"
    ("New Graduate Engineer, Software - '26/'27 (Starlink)", "entry"),  # SpaceX
])
def test_title_level(title, expected):
    assert title_level(title) == expected


# --------------------------------------------------------------------------- years of experience
@pytest.mark.parametrize("text,req", [
    ("REQUIRED QUALIFICATIONS\n• 3+ years of experience building backend services", 3.0),
    ("REQUIRED QUALIFICATIONS\n• 3 months - 2 years of technical work to include technical internship", 0.0),
    # Degree tiers: the candidate holds a bachelor's, so the bachelor's number is the one that binds
    ("Basic Qualifications\n- Bachelor's degree with 2 years of experience, or Master's degree with 0 years", 2.0),
    ("Basic Qualifications\n• Bachelor’s degree with 5 years of professional experience – OR – Master’s degree with 3 years of "
     "professional experience – OR – PhD with 1 year of professional experience. Will consider an additional 4+ years of "
     "experience in lieu of degree.", 5.0),                                                    # Northrop level 3
    ("Basic Qualifications\n• Bachelors degree in science, engineering, or related discipline with 2 years of experience, or 0 "
     "years of experience with a Masters degree\n• An additional 4 years of relevant experience can be considered in lieu of "
     "Bachelors degree", 2.0),                                                                  # Northrop level 2
    ("Basic Qualifications\n• Master's Degree with 0 years of experience; OR a Bachelor's Degree with 2 years of experience; OR "
     "an Associate's Degree with 4 years of experience; OR a High School Diploma (or equivalent) with 6 years of experience "
     "is required", 2.0),
    ("Basic Qualifications for Level 2:\n• Bachelor's degree with 2 years of experience; Master's with 0 years\n"
     "Basic Qualifications for Level 3:\n• Bachelor's degree with 5 years of experience; Master's with 3 years", 2.0),
    ("BASIC QUALIFICATIONS:\n• Bachelor’s degree and 6+ years of experience working in one or more of the following; or 10+ "
     "years of experience working in one or more of the following:", 6.0),                      # SpaceX senior
    ("BASIC QUALIFICATIONS:\n• Advanced degree; or bachelor’s degree and 2+ years of experience working in one or more of the "
     "following; or 6+ years of experience working in one or more of the following:", 2.0),
    ("BASIC QUALIFICATIONS:\n• Bachelor's degree; OR high school diploma/equivalency certificate and 3+ years of professional "
     "business development, operations, engineering, or account management experience", None),
    ("BASIC QUALIFICATIONS:\n• Bachelor’s degree in an engineering or STEM discipline; OR 4+ years of professional leadership "
     "experience in a manufacturing environment", None),
    ("REQUIRED QUALIFICATIONS\n• 0-2 years of relevant experience & Bachelor's degree in Computer Science, Engineering, "
     "Mathematics, Physics, or related technical field (or equivalent experience)", 0.0),       # Anduril
    ("REQUIRED QUALIFICATIONS\n• 5+ years of experience in a relevant Science or Engineering field, or equivalent advanced "
     "academic experience (e.g., MS, Ph.D.)", 5.0),
    ("Requirements\n- Master's degree with 3+ years of experience or PhD with 1+ years", 1.0),   # no bachelor's route listed
    # DoorDash: the years apply whichever degree you hold
    ("What you'll need\n• 5+ years of industry experience building and shipping production machine learning systems with "
     "measurable business impact (Bachelor's, Master's, or PhD).", 5.0),
    ("Requirements\n- Bachelor's degree in CS. 3+ years of experience building backend services and 1+ years of Go", 3.0),
    ("Requirements\n- Master's degree and 3 years of experience; or 8+ years of experience", 8.0),  # the candidate has no master's
    ("REQUIRED QUALIFICATIONS\n• BS/MS or higher degree in Electrical Engineering or equivalent, with 7+ years of experience "
     "designing, testing, and troubleshooting complex board designs.", 7.0),                    # Anduril
    ("Requirements\n- Bachelor's or Master's degree in Computer Science with 3+ years of experience", 3.0),
    ("Basic Qualifications\n• Minimum of 2 years of direct relevant experience with B.S degree; Minimum of 0 years of direct "
     "relevant experience with Masters degree", 2.0),                                           # Northrop: years first
    ("Basic Qualifications\n• 5 years of relevant experience with Bachelor's degree; 3 years of relevant experience with "
     "Master's degree; 1 year of relevant experience with PhD; an additional 4 years of experience may be considered in lieu "
     "of degree\n• 8 years of relevant experience with Bachelor's degree; 6 years of relevant experience with Master's degree; "
     "4 years of relevant experience with PhD", 5.0),                                           # Northrop level 3/4
    ("BASIC QUALIFICATIONS:\n• Bachelor’s degree in computer science, computer engineering, or other STEM discipline and 7+ of "
     "years professional network engineering experience; OR 10+ years of professional network engineering experience in lieu "
     "of a degree", 7.0),                                                                       # SpaceX typo, as posted
    # Northrop: how recent the clearance investigation must be is not years of experience
    ("Basic Qualifications\n• Bachelor’s Degree and 2 years of related experience; OR a Master’s degree and 0 years\n"
     "• Must have an active US Government Top Secret clearance (with a background investigation completed within the last 6 "
     "years or currently enrolled into Continuous Evaluation).", 2.0),
    ("Minimum Qualifications\n- Minimum of five (5) years of professional software development experience", 5.0),
    ("Requirements\n- 8+ years building backend and distributed systems in Go", 8.0),
    ("What you'll need\n- 2-4 years of industry experience\n- 5+ years with C++ is a plus", 5.0),
    ("About us\nFor over 30 years we have built aircraft.\nRequirements\n- Strong Python skills", None),
    # SpaceX: years "in lieu of a degree" replace the degree; they are not a requirement on top of it
    ("BASIC QUALIFICATIONS:\n• Bachelor's degree in computer science, engineering, math, or scientific discipline; "
     "OR 2+ years of professional experience building software in lieu of a degree\n"
     "• 1+ years of experience in full stack development", 1.0),
    ("BASIC QUALIFICATIONS:\n• Bachelor’s degree in computer science, engineering or other STEM discipline OR 2+ years of "
     "professional experience in software development in lieu of a degree.\n• Software development experience in C, C++, or Rust.", None),
    ("BASIC QUALIFICATIONS:\n• Bachelor's degree in computer science, engineering, math, or science discipline OR 2+ years "
     "of experience in software development in lieu of degree\n• 1+ years of software development experience in C/C++", 1.0),
    ("Requirements\n- Bachelor's degree and 5+ years of experience, or 9+ years of experience in lieu of a degree", 5.0),
    # Mach Industries: "<degree list>, or 3+ years of equivalent practical experience" is the route without a degree
    ("Required Qualifications\n• Bachelor’s, Master’s, or PhD in Computer Science, Robotics, Aerospace, Electrical "
     "Engineering, Machine Learning, or a related field, or 3+ years of equivalent practical experience as a software "
     "engineer.\n• Strong software engineering skills in modern C++ on Linux and Python.", None),
    ("Required Qualifications\n• Bachelor's degree in Computer Science or 4+ years of relevant work experience", None),
    ("Required Qualifications\n• Bachelor's degree in Computer Science or related field and 3+ years of experience", 3.0),    # Anduril GNC: "N or more years" is the same as "N+ years"
    ("Who you are\n• Bachelor's degree in Aerospace Engineering\n• 3 or more years of experience in Guidance, Navigation & "
     "Control engineering or related technical experience", 3.0),
])
def test_extract_yoe(text, req):
    assert extract_yoe(text)["required_min"] == req


# --------------------------------------------------------------------------- clearance wording
@pytest.mark.parametrize("text,status", [
    ("REQUIRED QUALIFICATIONS\n• Eligible to obtain and maintain an active U.S. Secret security clearance", "eligibility"),
    ("REQUIRED QUALIFICATIONS\n• Currently possesses and is able to maintain an active U.S. Top Secret SCI security clearance.", "active_required"),
    ("Basic Qualifications\n• Active U.S. Government Secret clearance required at the time of application.", "active_required"),
    ("PREFERRED QUALIFICATIONS\n• Active Secret clearance or higher", "active_preferred"),
    ("Basic Qualifications\n• Hold or able to obtain a DoD Secret clearance\nCLEARANCE REQUIRED FOR START: No", "eligibility"),
    ("Basic Qualifications\n• Python\nCLEARANCE REQUIRED FOR START: Yes\nCLEARANCE TYPE: Secret", "active_required"),
    ("Requirements\n• U.S. Citizenship is required for all positions with a government clearance and certain other restricted positions.", "eligibility"),
    ("Experience with creepage/clearance management on high-voltage PCBs", "none_mentioned"),
    # RTX: the status field says when the clearance must be held; "Qualifications We Prefer" is the preferred list
    ("Security Clearance Status:\nActive and existing security clearance required after day 1\nWhat You Will Do\n• Write radar software\n"
     "Qualifications You Must Have\n• The ability to obtain and maintain a U.S. government issued security clearance is required.\n"
     "Qualifications We Prefer\n• Active DoD Secret clearance\n• Radar fundamentals.", "active_preferred"),
    ("Security Clearance Status:\nActive and existing security clearance required on day 1\nWhat You Will Do\n• Write radar software\n"
     "Qualifications You Must Have\n• Bachelor's degree in a STEM field", "active_required"),
    ("Security Clearance Status:\nAbility to obtain INTERIM U.S. government issued security clearance is required prior to start date\n"
     "Qualifications You Must Have\n• Clearance: Must be able to obtain DoD Secret Clearance;", "eligibility"),
    ("Security Clearance Status:\nActive and existing security clearance required after day 1\nWhat You Will Do\n• Design embedded software\n"
     "Qualifications You Must Have\n• Bachelor's degree in a STEM field. Degree must be obtained by start date.", "eligibility"),
    ("Must be a U.S. Person due to required access to U.S. export controlled information or facilities; "
     "U.S. clearance eligibility may be required depending on program.", "eligibility"),
])
def test_extract_clearance(text, status):
    assert extract_clearance(text)["status"] == status


# --------------------------------------------------------------------------- screener compact output
def test_parse_compact():
    d = parse_compact("G0001 keep software\nG0002 keep adjacent\nG0003 drop mechanical design\n"
                      "L Costa Mesa, California, United States => home\nnoise line\n")
    assert d["titles"]["G0001"] == {"keep": True, "family": "software", "reason": ""}
    assert d["titles"]["G0002"]["family"] == "adjacent"
    assert d["titles"]["G0003"]["keep"] is False and "mechanical" in d["titles"]["G0003"]["reason"]
    assert d["locations"]["Costa Mesa, California, United States"] == "home"


# --------------------------------------------------------------------------- duplicate-application matching
def test_tracker_match_same_title_vs_similar():
    rows = [{"company": "Acme", "title": "Mission Software Engineer Radar", "status": "applied",
             "date_applied": "2026-09-30", "source": "manual"}]
    dup = match({"company": "Acme Robotics", "id": "1", "title": "Mission Software Engineer, Radar"}, rows)
    sim = match({"company": "Acme Robotics", "id": "2", "title": "Mission Software Engineer"}, rows)
    other = match({"company": "Vortex", "id": "3", "title": "Mission Software Engineer, Radar"}, rows)
    assert dup and dup.startswith("DUPLICATE")
    assert sim and sim.startswith("similar role")
    assert other is None


def test_tracker_match_subset_title_is_similar():
    rows = [{"company": "Globex", "title": "Backend Software Engineer", "status": "applied",
             "date_applied": "2026-08-22", "source": "manual"}]
    m = match({"company": "Globex", "id": "9", "title": "All Levels: Backend Software Engineer"}, rows)
    assert m and m.startswith("similar role")


@pytest.mark.parametrize("title,desc,expect_penalty", [
    ("2027 - Associate Software Engineer - McClellan CA", "STEM degree: has completed their degree", True),   # Northrop campus req
    ("2027 Early Career Software Engineer", "Must be pursuing or have recently completed a bachelor's", True),  # Anduril
    ("New Graduate Engineer, Software - '26/'27 (Starlink)", "", True),                                        # SpaceX
    ("2026 Early Career Software Engineer", "3 months - 2 years of technical work; able to start full time in 2026", False),
    ("Software Engineer II", "3+ years of experience", False),
    ("Flight Software Engineer", "We are seeking a Software Engineer, Flight Software (new grad to senior)", False),  # Mach: all levels
    ("December 2026 New Graduate Engineer, Software / GNC", "Graduating with a bachelor's degree by end of December 2026", True),
])
def test_program_window(title, desc, expect_penalty):
    from jobhunt.rank import program_window_multiplier
    mult, _ = program_window_multiplier({"title": title, "description": desc}, {"graduation": "2025-06"})
    assert (mult < 1.0) is expect_penalty


# --------------------------------------------------------------------------- resume: per-job skills reordering
def test_emphasize_moves_whole_skill_names_only():
    from jobhunt.resume import emphasize_skills
    r = {"skills": {"Languages": "TypeScript, JavaScript, Python, C++, C, SQL",
                    "Frameworks": "React, Node.js, GraphQL, Next.js, Electron, Flask, PyTorch",
                    "Infrastructure": "Kubernetes, Docker, AWS, CI/CD"}}
    emphasize_skills(r, ["TypeScript", "React", "Electron", "CI"])
    assert r["skills"]["Languages"] == "TypeScript, JavaScript, Python, C++, C, SQL"  # "C" is not part of "TypeScript"
    assert r["skills"]["Frameworks"] == "React, Electron, Node.js, GraphQL, Next.js, Flask, PyTorch"
    assert r["skills"]["Infrastructure"] == "CI/CD, Kubernetes, Docker, AWS"
    emphasize_skills(r, ["C", "node"])
    assert r["skills"]["Languages"].startswith("C, TypeScript")  # exactly "C", not "C++"
    assert r["skills"]["Frameworks"].startswith("Node.js, React")


# --------------------------------------------------------------------------- ranking: location and referrals
from jobhunt.config import normalize  # noqa: E402

PROFILE = normalize({
    "regions": [{"key": "home", "weight": 1.1}, {"key": "home_outer", "weight": 1.0}, {"key": "bay_area", "weight": 1.0}],
    "remote_weight": 1.1, "elsewhere_weight": 0.85, "unknown_weight": 0.9,
    "referrals": [{"company": "Acme", "contact": "A"}, {"company": "Globex", "contact": "D", "job_id": "77"},
                  {"company": "Globex", "contact": "D", "title": "Software Engineer, Web"}]})


@pytest.mark.parametrize("regions,expected", [
    (["bay_area", "remote_us"], ("remote_us", 1.1)),   # remote lets you live at home, so it beats a Bay Area office
    (["home", "remote_us"], ("home", 1.1)),            # equal weights: the region listed first wins
    (["bay_area", "home_outer"], ("home_outer", 1.0)),
    (["other_us", "non_us"], ("other_us", 0.85)),      # a non-US site never wins
    (["non_us"], ("non_us", 0.9)),
    ([], ("unknown", 0.9)),
])
def test_best_region_follows_profile(regions, expected):
    from jobhunt.rank import best_region
    assert best_region(regions, PROFILE) == expected


def test_region_order_is_read_from_the_profile():
    from jobhunt.rank import region_order
    assert region_order(PROFILE) == ["home", "remote_us", "home_outer", "bay_area", "unknown", "other_us"]
    assert region_order(normalize({"regions": [{"key": "home", "weight": 1.0}, {"key": "bay_area", "weight": 1.3}]}))[0] == "bay_area"


def test_referral_scope():
    from jobhunt.rank import referral_for
    assert referral_for({"company": "Acme Robotics", "id": "1", "title": "Mission Software Engineer"}, PROFILE) == ("A", "company")
    assert referral_for({"company": "Globex", "id": "77", "title": "Backend Engineer"}, PROFILE) == ("D", "job")
    assert referral_for({"company": "Globex", "id": "5", "title": "Software Engineer, Web"}, PROFILE) == ("D", "job")
    assert referral_for({"company": "Globex", "id": "6", "title": "Backend Engineer"}, PROFILE) is None  # only named roles
    assert referral_for({"company": "Vortex", "id": "1", "title": "X"}, PROFILE) is None


def test_other_us_is_milder_for_a_top_rated_role():
    from jobhunt.rank import best_region
    prof = normalize({"regions": [{"key": "home", "weight": 1.1}, {"key": "bay_area", "weight": 0.85}],
                      "remote_weight": 1.1, "elsewhere_weight": 0.65, "elsewhere_great_company_weight": 0.85})
    assert best_region(["other_us"], prof) == ("other_us", 0.65)
    assert best_region(["other_us"], prof, great=True) == ("other_us", 0.85)
    assert best_region(["other_us", "bay_area"], prof, great=True) == ("bay_area", 0.85)  # a tie goes to your named region
    assert best_region(["other_us", "home"], prof, great=True) == ("home", 1.1)


def test_posting_age_curve_can_be_tuned_in_the_profile():
    from jobhunt.rank import freshness
    job = {"title": "Software Engineer", "ats": "lever"}
    sig = {"age_days": 10, "us_person_required": False, "clearance": {"status": "none_mentioned"}}
    assert freshness(job, sig)[0] == 0.48                       # default curve: 8-14 days
    assert freshness(job, sig, {"curve": [[30, 1.0]]})[0] == 1.0  # profile override
    assert freshness(dict(job, ats="greenhouse"), sig)[0] == 0.72  # 10 days counts as ~6.7 on an AI-ranked system
    assert freshness(job, dict(sig, age_days=None))[0] == 0.45


# --------------------------------------------------------------------------- ranking: work match and unstated years
def _job(required_min=None, level="unspecified"):
    return {"id": "1", "title": "Mission Software Engineer", "company": "Testco", "ats": "lever", "description": "",
            "signals": {"yoe": {"required_min": required_min, "preferred_min": None, "mentions": []}, "level": level,
                        "seniority_phrases": [], "salary": {}, "family": "core", "age_days": 0, "us_person_required": False,
                        "clearance": {"status": "none_mentioned", "polygraph": False},
                        "location": {"best": "home", "all": ["home"]}}}


def test_meeting_the_minimum_list_is_not_a_match():
    """A posting can accept one of your languages while the team's real work is new to you."""
    from jobhunt.rank import score_job
    fit = {"skills": 5, "domain": 3, "level_fit": 5, "competition": 0, "role_type": "software", "career_value": 5}
    same_kind = score_job(_job(1.0), dict(fit, work_match=5), PROFILE, 1.25)
    half_new = score_job(_job(1.0), dict(fit, work_match=3), PROFILE, 1.25)
    other_kind = score_job(_job(1.0), dict(fit, work_match=2), PROFILE, 1.25)
    assert same_kind["tier"] == "A"
    assert round(half_new["score"] / same_kind["score"], 2) == 0.6
    assert round(other_kind["score"] / same_kind["score"], 2) == 0.35 and other_kind["tier"] in ("C", "D")
    assert "different kind of engineering" in other_kind["notes"]["work_match"]
    # An older review without work_match is not a full match: estimate it from the requirements score.
    unassessed = score_job(_job(1.0), fit, PROFILE, 1.25)
    assert unassessed["parts"]["work_match_x"] == 0.81 and "not assessed" in unassessed["notes"]["work_match"]
    assert score_job(_job(1.0), dict(fit, skills=3), PROFILE, 1.25)["parts"]["work_match_x"] == 0.36
    assert score_job(_job(1.0), None, PROFILE, 1.25)["parts"]["work_match_x"] == 1.0  # never reviewed: neutral


def test_unstated_years_use_the_reviewers_level_fit():
    from jobhunt.rank import score_job
    fit = {"skills": 5, "domain": 5, "competition": 0, "work_match": 5}
    assert score_job(_job(None), dict(fit, level_fit=5), PROFILE, 1.25)["parts"]["experience_x"] == 1.0
    assert score_job(_job(None), dict(fit, level_fit=4), PROFILE, 1.25)["parts"]["experience_x"] == 0.85
    assert score_job(_job(None), dict(fit, level_fit=2), PROFILE, 1.25)["parts"]["experience_x"] == 0.35
    assert score_job(_job(3.0), dict(fit, level_fit=5), PROFILE, 1.25)["parts"]["experience_x"] == 0.4  # stated years win


def test_repeat_cold_applications_to_one_company_score_lower():
    """Huntr 2026: 6.07% response for one application to a company, 4.64% for 2-3, 3.34% for 4-7, 1.91% for 8+."""
    from jobhunt.rank import company_volume_multiplier, score_job
    fit = {"skills": 5, "domain": 4, "level_fit": 5, "competition": 0, "work_match": 5}
    on = dict(PROFILE, company_volume_multipliers=[[1, 1.0], [3, 0.76], [7, 0.55], [None, 0.31]])  # off by default
    assert score_job(_job(1.0), fit, PROFILE, 1.25, prior_apps=14)["parts"]["company_volume_x"] == 1.0
    first = score_job(_job(1.0), fit, on, 1.25)
    fifteenth = score_job(_job(1.0), fit, on, 1.25, prior_apps=14)
    assert first["parts"]["company_volume_x"] == 1.0 and fifteenth["parts"]["company_volume_x"] == 0.31
    assert round(fifteenth["score"] / first["score"], 2) == 0.31 and "14 applications" in fifteenth["notes"]["volume"]
    assert [company_volume_multiplier(n, {}) for n in (0, 1, 2, 3, 6, 7)] == [1.0, 0.76, 0.76, 0.55, 0.55, 0.31]
    referred = dict(on, referrals=[{"company": "Testco", "contact": "a friend"}])
    assert score_job(_job(1.0), fit, referred, 1.25, prior_apps=14)["parts"]["company_volume_x"] == 1.0


def test_reviewer_can_narrow_a_location_the_label_overstates():
    """A posting labelled remote whose text says "East Coast only" counts as other_us once the reviewer says so."""
    from jobhunt.rank import score_job
    fit = {"skills": 5, "domain": 4, "level_fit": 5, "competition": 0, "work_match": 5}
    job = _job(1.0)
    job["signals"]["location"] = {"best": "remote_us", "all": ["remote_us"]}
    as_labelled = score_job(job, fit, PROFILE, 1.25)
    narrowed = score_job(job, dict(fit, region="other_us"), PROFILE, 1.25)
    assert as_labelled["notes"]["location"] == "remote_us" and narrowed["notes"]["location"] == "other_us"
    assert narrowed["score"] < as_labelled["score"] and "posting's text" in narrowed["notes"]["location_note"]
    assert score_job(job, dict(fit, region="mars"), PROFILE, 1.25)["notes"]["location"] == "remote_us"


def test_role_blocked_by_one_stated_requirement_keeps_the_tier_it_would_have_had():
    from jobhunt.rank import score_job
    fit = {"skills": 5, "domain": 5, "level_fit": 5, "competition": 0, "work_match": 5}
    job = _job(1.0)
    open_role = score_job(job, fit, PROFILE, 1.25)
    blocked = score_job(job, dict(fit, dealbreaker="Requires 'MS or PhD'; you hold a B.S."), PROFILE, 1.25)
    assert open_role["tier"] in ("A", "B") and open_role["unblocked_tier"] is None
    assert blocked["tier"] == "X" and blocked["unblocked_tier"] == open_role["tier"]
