"""Regression tests for problems an independent review reproduced: month-only dates, odd reviewer scores, status
updates, newer reviews, regional sweeps hiding older runs, malformed picks."""

import json
import time
from datetime import date

from jobhunt import applylist, email_import, rank, resume, tracker
from jobhunt.config import load_profile, month_date, normalize


def test_month_only_dates_are_accepted():
    assert month_date("2024-07") == date(2024, 7, 1)
    assert month_date(date(2024, 7, 15)) == date(2024, 7, 15)
    assert month_date("July 2024") is None and month_date("") is None
    assert rank.candidate_yoe({"fulltime_start": "2024-07"}) > 0
    assert email_import._days("2026-07", "2026-07-12") == 11
    assert email_import._days("2026-07", "soon") == 10_000


def test_applied_add_updates_without_losing_the_application_date():
    tracker.add("Acme", "Software Engineer", job_id="77", url="https://x/77", when="2026-09-01")
    tracker.add("Acme", "Software Engineer", job_id="77", status="interview", when="2026-09-20")
    rows = tracker.load()
    assert len(rows) == 1
    assert (rows[0]["date_applied"], rows[0]["status"], rows[0]["status_date"]) == ("2026-09-01", "interview", "2026-09-20")
    # an outcome with no id or url updates the latest application with that title
    tracker.add("Acme", "Software Engineer", status="rejected", when="2026-10-01")
    assert len(tracker.load()) == 1 and tracker.load()[0]["status"] == "rejected"
    # the checkbox page logs by url: the same url twice is one application
    tracker.add("Globex", "Frontend Engineer", url="https://y/1", when="2026-09-02")
    tracker.add("Globex", "Frontend Engineer", url="https://y/1", when="2026-09-03")
    assert sum(1 for r in tracker.load() if r["company"] == "Globex") == 1
    # a new application to a title that rejected you is a new row
    tracker.add("Acme", "Software Engineer", job_id="99", when="2026-10-10")
    assert len([r for r in tracker.load() if r["company"] == "Acme"]) == 2


def _job():
    return {"id": "1", "title": "Software Engineer", "company": "Testco", "ats": "lever", "description": "",
            "signals": {"yoe": {"required_min": 1.0, "preferred_min": None, "mentions": []}, "level": "unspecified",
                        "seniority_phrases": [], "salary": {}, "family": "core", "age_days": 0, "us_person_required": False,
                        "clearance": {"status": "none_mentioned", "polygraph": False},
                        "location": {"best": "home", "all": ["home"]}}}


def test_odd_reviewer_scores_do_not_stop_a_ranking():
    profile = normalize({"regions": [{"key": "home", "weight": 1.1}]})
    good = rank.score_job(_job(), {"skills": 5, "domain": 4, "level_fit": 5, "competition": 0, "work_match": 5}, profile, 2)
    strings = rank.score_job(_job(), {"skills": "5", "domain": "4", "level_fit": "5", "competition": "0", "work_match": "5"}, profile, 2)
    nulls = rank.score_job(_job(), {"skills": None, "domain": "n/a", "level_fit": None, "competition": None,
                                    "work_match": None, "career_value": "high"}, profile, 2)
    assert strings["score"] == good["score"]
    assert nulls["score"] >= 0 and nulls["tier"] in "ABCD"


def test_a_newer_review_of_the_same_posting_wins(tmp_path):
    fit = tmp_path / "fit"
    fit.mkdir()
    (fit / "p1_batch_01.json").write_text(json.dumps([{"key": "J001", "id": "1", "work_match": 2}]))
    time.sleep(0.02)
    (fit / "p2_batch_01.json").write_text(json.dumps([{"key": "J001", "id": "1", "work_match": 5},
                                                       {"key": "J001", "id": "9", "work_match": 1}]))
    (fit / "p3_batch_02.json").write_text("[{half written")
    fits = rank.load_fits(tmp_path)
    assert fits["J001|1"]["work_match"] == 5 and fits["J001|9"]["work_match"] == 1


def _run(workspace, name, meta, jobs):
    d = workspace / "runs" / name
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps(meta))
    (d / "candidates.json").write_text(json.dumps(jobs))
    (d / "ranked.json").write_text(json.dumps(jobs))
    return d


def _ranked(company, jid, title, region, score=60.0):
    j = _job()
    j.update({"id": jid, "title": title, "company": company, "url": f"https://{company}/{jid}", "locations": [region],
              "posted_at": "2026-10-01T00:00:00+00:00"})
    j["fit"] = {"work_match": 5, "why": "fits", "resume_focus": "general"}
    j["rank"] = {"score": score, "tier": "A", "fit_tier": "A", "unblocked_tier": None,
                 "parts": {"seen_x": 1.0, "competition_x": 1.0}, "notes": {"location": region}}
    return j


def test_a_regional_sweep_only_replaces_an_older_run_inside_its_regions(workspace):
    _run(workspace, "acme-2026-10-01", {"kind": "company", "company": "Acme", "companies": ["Acme"],
                                        "fetched_at": "2026-10-01T09:00:00"},
         [_ranked("Acme", "1", "Frontend Engineer", "home"), _ranked("Acme", "2", "Platform Engineer", "other_us")])
    _run(workspace, "sweep-la-2026-10-05", {"kind": "sweep", "companies": ["Acme"], "regions": ["home"],
                                            "fetched_at": "2026-10-05T09:00:00"},
         [_ranked("Acme", "3", "Backend Engineer", "home")])
    out = applylist.build(load_profile(), rerank=False)
    md = (workspace / "APPLY_LIST.md").read_text()
    assert "Backend Engineer" in md          # the sweep's current home-region role
    assert "Platform Engineer" in md         # outside the sweep's regions: the older run still counts
    assert "Frontend Engineer" not in md     # inside them: the newer sweep says it's gone
    assert out["total"] == 2


def test_malformed_picks_are_reported_not_crashed_on(workspace):
    (workspace / "picks.yaml").write_text("picks:\n  - title: No company here\n    work: 4\n  - company: Acme\n    title: No link\n    work: 3\n    job_id: '5'\n")
    out = applylist.build(load_profile(), rerank=False)
    assert len(out["left_off"]["bad_picks"]) == 2
    assert "missing a company, url or job_id" in (workspace / "APPLY_LIST.md").read_text()


def test_build_flags_narrow_no_break_spaces():
    assert " " in resume.BAD_CHARS and "‑" in resume.BAD_CHARS and " " in resume.BAD_CHARS
