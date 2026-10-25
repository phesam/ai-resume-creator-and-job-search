"""Tests for the email-derived application history (jobhunt/email_import.py) and duplicate matching.

Company names here are fictional. Run: python3 -m pytest tests -q
"""

import json
from datetime import date

from jobhunt import email_import, tracker

TODAY = date(2026, 10, 2)


def ev(day, company, title, kind, msg_id=None):
    return {"date": day, "company": company, "title": title, "kind": kind, "msg_id": msg_id or f"{day}{company}{title}{kind}"}


def test_same_company_is_whole_word():
    assert tracker.same_company("Acme", "Acme Robotics")
    assert tracker.same_company("Globex", "Globex Corporation")
    assert tracker.same_company("Initech Technologies", "Initech")
    assert not tracker.same_company("Vortex", "VortexAI")
    assert not tracker.same_company("Box", "Dropbox")
    assert not tracker.same_company("Applied Widgets", "Applied Materials")
    assert not tracker.same_company("", "Acme")


def test_reapplying_to_the_same_title_opens_a_new_application():
    t = "Software Engineer (Platform Team)"
    rows = email_import.build_rows([ev("2026-05-28", "Vortex", t, "applied"), ev("2026-06-13", "Vortex", t, "rejected"),
                                    ev("2026-06-15", "Vortex", t, "applied"), ev("2026-09-18", "Vortex", t, "applied")])
    assert [(r["date_applied"], r["status"], r["status_date"]) for r in rows] == [
        ("2026-05-28", "rejected", "2026-06-13"), ("2026-06-15", "applied", "2026-06-15"), ("2026-09-18", "applied", "2026-09-18")]


def test_events_are_ordered_and_deduplicated(tmp_path):
    t = "Full Stack Software Engineer - Top Secret Clearance"
    lines = [ev("2026-06-27", "Vortex", t, "rejected", "m2"),
             ev("2026-06-27", "Vortex", t, "applied", "m1"),
             ev("2026-06-27", "Vortex", t, "applied", "m1"),  # seen twice
             {"date": "June 27", "company": "Vortex", "kind": "applied"}]  # bad date: skipped
    (tmp_path / "a.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n")
    events = email_import.load_events(tmp_path)
    assert [e["kind"] for e in events] == ["applied", "rejected"]  # same day: the application comes first
    rows = email_import.build_rows(events)
    assert len(rows) == 1 and rows[0]["status"] == "rejected"


def test_two_confirmations_for_one_title_on_one_day_are_one_application():
    t = "Full Stack Software Engineer, Data"
    rows = email_import.build_rows([ev("2026-07-12", "Vortex", t, "applied", "a"), ev("2026-07-12", "Vortex", t, "applied", "b")])
    assert len(rows) == 1 and "2 confirmation emails" in rows[0]["_auto"][0]


def test_untitled_rejection_goes_to_the_application_in_interviews():
    rows = email_import.build_rows([
        ev("2026-06-12", "Acme", "Tactical Software Engineer, Cloud", "applied"),
        ev("2026-07-12", "Acme", "2026 Early Career Software Engineer", "applied"),
        ev("2026-07-27", "Acme Robotics", "", "interview"),
        ev("2026-09-09", "Acme", "", "rejected"),
    ])
    by_title = {r["title"]: r for r in rows}
    assert by_title["Tactical Software Engineer, Cloud"]["status"] == "applied"
    early = by_title["2026 Early Career Software Engineer"]
    assert (early["status"], early["status_date"]) == ("rejected", "2026-09-09")
    assert "rejected after interviews" in early["_auto"]


def test_rejection_names_the_role_a_confirmation_left_out():
    rows = email_import.build_rows([ev("2026-08-23", "Globex", "", "applied"),
                                    ev("2026-08-27", "Globex", "[EVERGREEN]Backend Software Engineer", "rejected")])
    assert len(rows) == 1 and rows[0]["status"] == "rejected" and "Backend" in rows[0]["title"]


def test_merge_keeps_manual_details_and_is_repeatable():
    existing = [
        {"date_applied": "2026-07", "company": "Acme Robotics", "title": "2026 Early Career Software Engineer", "job_id": "1000201",
         "url": "https://boards.greenhouse.io/acme/jobs/1000201", "status": "rejected", "source": "manual", "notes": "final round"},
        {"date_applied": "2026-10-01", "company": "Initech", "title": "Software Engineer", "status": "applied", "source": "manual"},
    ]
    events = [ev("2026-09-18", "Vortex", "Software Engineer (Platform Team)", "applied"),
              ev("2026-07-12", "Acme", "2026 Early Career Software Engineer", "applied"),
              ev("2026-07-27", "Acme", "", "interview")]
    events.sort(key=lambda e: e["date"])
    merged = email_import.merge(existing, email_import.build_rows(events), "2026-10-02")
    find = lambda company, word: next(r for r in merged if tracker.same_company(r["company"], company) and word in r["title"])  # noqa: E731
    assert find("Vortex", "Platform")["source"] == "email"
    early = find("Acme", "Early Career")
    assert (early["status"], early["job_id"], early["source"], early["date_applied"]) == ("rejected", "1000201", "email+manual", "2026-07-12")
    assert "final round" in early["notes"]
    assert find("Initech", "Software")["source"] == "manual"  # manual logs with no email stay as they are

    again = email_import.merge(merged, email_import.build_rows(events), "2026-10-03")
    core = lambda rows: sorted((r["company"], r["title"], r["date_applied"], r["status"], r.get("job_id") or "", r["source"]) for r in rows)  # noqa: E731
    assert core(again) == core(merged)
    assert "final round" in next(r for r in again if "Early Career" in r["title"])["notes"]


def test_match_reports_the_outcome_that_matters():
    t = "Full Stack Software Engineer (Components)"
    job = {"company": "Vortex", "id": "1000203", "title": t}
    rejected = {"company": "Vortex", "title": t, "status": "rejected", "date_applied": "2026-06-27", "status_date": "2026-07-03", "source": "email"}
    assert tracker.match(job, [rejected], TODAY).startswith("DUPLICATE?: rejected 2026-07-03 (applied 2026-06-27)")
    reapplied = dict(rejected, status="applied", date_applied="2026-07-12", status_date="2026-07-12")
    assert tracker.match(job, [rejected, reapplied], TODAY).startswith("DUPLICATE?: applied 2026-07-12")  # the open one wins
    old = dict(rejected, date_applied="2026-02-28", status_date="2026-03-02")
    assert tracker.match(job, [old], TODAY).startswith("applied before:")  # over 6 months: not a blocker
    assert tracker.match(job, [dict(rejected, company="VortexAI")], TODAY) is None


def test_import_can_be_run_again(tmp_path):
    folder = tmp_path / "events"
    folder.mkdir()
    (folder / "a.jsonl").write_text(json.dumps(ev("2026-09-11", "Umbrella Space", "", "applied")) + "\n")
    tracker.save([{"date_applied": "2026-09-11", "company": "Umbrella Space", "title": "Software Engineer I", "job_id": "77",
                   "status": "applied", "source": "manual"}])
    email_import.run(folder)
    first = tracker.load()
    email_import.run(folder)
    assert tracker.load() == first
    row = next(r for r in first if r["company"] == "Umbrella Space")
    assert (row["title"], row["status"], row["source"], row["job_id"]) == ("Software Engineer I", "applied", "email+manual", "77")
    assert email_import.last_import(folder)["events"] == 1


def test_bracket_tags_do_not_hide_a_repeat_title():
    assert tracker.same_title("[EVERGREEN]Backend Software Engineer", "Backend Software Engineer")
    assert tracker.similar_title("[EVERGREEN]Backend Software Engineer", "All Levels: Backend Software Engineer")
    assert tracker.same_title("[2026] Software Engineer, Early Career", "Software Engineer, Early Career")


def test_level_i_and_level_ii_are_different_postings():
    assert not tracker.same_title("Software Engineer I", "Software Engineer II")
    assert tracker.same_title("Software Engineer", "Software Engineer II")  # emails often drop the level


def test_manual_log_names_the_role_an_untitled_confirmation_left_out():
    """The email said only "Thanks for applying"; the manual log has the role and job id."""
    events = [ev("2026-10-02", "Parallax Rail", "", "applied")]
    manual = {"date_applied": "2026-10-02", "company": "Parallax Rail", "title": "Full Stack Software Engineer I",
              "job_id": "1000202", "url": "https://x/1000202", "location": "Los Angeles, CA", "status": "applied",
              "status_date": "", "source": "manual", "resume": "", "notes": "chosen on Oct 2"}
    rows = email_import.merge([manual], email_import.build_rows(events), "2026-10-03")
    assert len(rows) == 1
    assert (rows[0]["title"], rows[0]["job_id"], rows[0]["source"]) == ("Full Stack Software Engineer I", "1000202", "email+manual")
    again = email_import.merge(rows, email_import.build_rows(events), "2026-10-04")  # a later import keeps the name
    assert len(again) == 1 and again[0]["title"] == "Full Stack Software Engineer I" and again[0]["job_id"] == "1000202"
    # an application years earlier at the same company is a different one
    old = email_import.merge([manual], email_import.build_rows([ev("2023-06-23", "Parallax Rail", "", "applied")]), "2026-10-03")
    assert len(old) == 2
