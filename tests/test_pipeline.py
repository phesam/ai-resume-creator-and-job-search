"""Offline end-to-end tests: fetch (faked) -> universal checks -> screen -> screen-apply -> review -> rank -> apply list.

They run in the throwaway workspace from conftest.py, with a fake hiring system, so they never touch the network
or real data. Run: python3 -m pytest tests -q
"""

import json
from types import SimpleNamespace

from jobhunt import __main__ as cli
from jobhunt import applylist, ats, rank, resolve, tracker
from jobhunt.common import make_job
from jobhunt.config import load_profile

DESC_OK = """About the role
Build web services for clinic staff.
REQUIRED QUALIFICATIONS
• 1+ years of experience with TypeScript and React
• Eligible to obtain and maintain an active U.S. Secret security clearance
PREFERRED QUALIFICATIONS
• Kubernetes
US Salary Range $120,000 - $150,000 USD"""

DESC_SENIOR = """REQUIRED QUALIFICATIONS
• 8+ years of experience building distributed systems"""

DESC_THREE = """REQUIRED QUALIFICATIONS
• 3+ years of professional software engineering experience with Go"""


def J(company, **k):
    return make_job(company=company, ats="fake", **k)


def fake_testco_jobs(cfg):
    return [
        J("Testco", id="1", title="Software Engineer, Platform", url="https://x/1", locations=["Irvine, California, United States"],
          posted_at="2026-09-30T00:00:00+00:00", description=DESC_OK),
        J("Testco", id="2", title="Senior Software Engineer", url="https://x/2", locations=["Irvine, California, United States"],
          posted_at="2026-09-30T00:00:00+00:00", description=DESC_SENIOR),
        J("Testco", id="3", title="Mechanical Design Engineer", url="https://x/3", locations=["Irvine, California, United States"],
          posted_at="2026-09-30T00:00:00+00:00", description=DESC_OK),
        J("Testco", id="4", title="Software Engineer Intern", url="https://x/4", locations=["Irvine, California, United States"],
          description=DESC_OK),
        J("Testco", id="5", title="Backend Engineer", url="https://x/5", locations=["London, England, United Kingdom"], description=DESC_OK),
    ]


def fake_other_jobs(cfg):
    return [
        J("Otherco", id="10", title="Full Stack Engineer", url="https://y/10", locations=["Seattle, Washington, United States"],
          posted_at="2026-09-29T00:00:00+00:00", description=DESC_OK),
        J("Otherco", id="11", title="Frontend Engineer", url="https://y/11", locations=["Santa Monica, CA"],
          posted_at="2026-09-29T00:00:00+00:00", description=DESC_OK),
        J("Otherco", id="12", title="Platform Engineer", url="https://y/12", locations=["Temecula Valley Office, California"],
          posted_at="2026-09-29T00:00:00+00:00", description=DESC_THREE),
    ]


def setup_fakes(monkeypatch):
    ats.register("fake", lambda cfg: fake_testco_jobs(cfg) if cfg["name"] == "Testco" else fake_other_jobs(cfg))
    reg = [{"name": "Testco", "ats": "fake"}, {"name": "Otherco", "ats": "fake"}]
    monkeypatch.setattr(resolve, "load_registry", lambda: reg)
    monkeypatch.setattr(resolve, "lookup", lambda name: [e for e in reg if e["name"].lower() == name.lower()])


def gids(run_dir):
    titles = (run_dir / "screen" / "titles_01.md").read_text()
    return {(line.split(" | ")[1], line.split(" | ")[2]): line.split(" | ")[0] for line in titles.splitlines() if line.startswith("G")}


def review(run_dir, rows):
    packets = sorted((run_dir / "review").glob("*batch_*.md"))
    cands = {(c["company"], c["title"]): c for c in json.loads((run_dir / "candidates.json").read_text())}
    out = []
    for (company, title), extra in rows.items():
        c = cands[(company, title)]
        out.append({"key": c["key"], "id": c["id"], "title": title, "skills": 5, "domain": 4, "level_fit": 5, "competition": 0,
                    "dealbreaker": None, "hooks": ["booking flow"], "gaps": [], "why": "Direct match.", "resume_focus": "general",
                    "work_match": 5, "role_type": "software", "career_value": 4, **extra})
    (run_dir / "fit").mkdir(exist_ok=True)
    (run_dir / "fit" / packets[0].name.replace(".md", ".json")).write_text(json.dumps(out))


def test_company_run_end_to_end(monkeypatch, workspace):
    setup_fakes(monkeypatch)
    assert cli.cmd_find(SimpleNamespace(company="Testco", ats=None, out=None)) == 3  # screen needed
    run_dir = next((workspace / "runs").glob("testco-*"))
    brief = (run_dir / "screen" / "BRIEF.md").read_text()
    assert "`home`: Southern California" in brief and "remote_us" in brief
    titles = (run_dir / "screen" / "titles_01.md").read_text()
    # the intern and the posting abroad were removed structurally; the senior 8+ years posting by evidence
    assert "Intern" not in titles and "Backend Engineer" not in titles and "Senior Software Engineer" not in titles
    g = gids(run_dir)
    (run_dir / "screen" / "screen_01.txt").write_text(
        f"{g[('Testco', 'Software Engineer, Platform')]} keep software\n{g[('Testco', 'Mechanical Design Engineer')]} drop mechanical design\n"
        "L Irvine, California, United States => home\n")
    assert cli.cmd_screen_apply(SimpleNamespace(run_dir=str(run_dir))) == 0
    # applied decision files move aside: a later screen-prep numbers new titles from G0001 again
    assert not list((run_dir / "screen").glob("screen*.txt")) and list((run_dir / "screen" / "applied").glob("*/screen_01.txt"))
    cands = json.loads((run_dir / "candidates.json").read_text())
    assert [c["title"] for c in cands] == ["Software Engineer, Platform"]
    assert cands[0]["signals"]["location"] == {"best": "home", "all": ["home"], "source": "screened"}
    triage_md = (run_dir / "triage.md").read_text()
    assert "Mechanical Design Engineer (mechanical design)" in triage_md  # every exclusion is listed with its reason

    review(run_dir, {("Testco", "Software Engineer, Platform"): {}})
    profile = load_profile()
    ranked = rank.rank_and_report(run_dir, profile)
    assert ranked[0]["rank"]["tier"] in ("A", "B")
    report = (run_dir / "REPORT.md").read_text()
    assert "Strong matches" in report and "Software Engineer, Platform" in report and "No applications to Testco" in report
    assert (run_dir / "report.html").exists()

    # Re-running the same folder (after a rule fix) keeps the reviews already there.
    assert cli.cmd_screen_apply(SimpleNamespace(run_dir=str(run_dir))) == 0
    assert json.loads((run_dir / "meta.json").read_text())["review_batches"] == []


def test_reviews_carry_over_to_a_later_run(monkeypatch, workspace):
    setup_fakes(monkeypatch)
    old = workspace / "runs" / "testco-2026-10-01"
    assert cli.cmd_find(SimpleNamespace(company="Testco", ats=None, out=str(old))) == 3
    g = gids(old)
    (old / "screen" / "screen_01.txt").write_text(
        f"{g[('Testco', 'Software Engineer, Platform')]} keep software\n{g[('Testco', 'Mechanical Design Engineer')]} drop mech\n"
        "L Irvine, California, United States => home\n")
    cli.cmd_screen_apply(SimpleNamespace(run_dir=str(old)))
    review(old, {("Testco", "Software Engineer, Platform"): {"work_match": 4}})
    new = workspace / "runs" / "testco-2026-10-09"
    assert cli.cmd_find(SimpleNamespace(company="Testco", ats=None, out=str(new))) == 0  # titles and places cached: no screen
    meta = json.loads((new / "meta.json").read_text())
    assert meta["reviews_carried_over"] == 1 and meta["review_batches"] == []
    carried = json.loads((new / "fit" / "carried_over.json").read_text())
    assert carried[0]["work_match"] == 4 and carried[0]["carried_from"] == "testco-2026-10-01"
    assert meta["new_since_last_run"] == []  # same postings as last time


def test_sweep_keeps_only_postings_in_the_regions_asked_for(monkeypatch, workspace):
    setup_fakes(monkeypatch)
    a = SimpleNamespace(regions="home,home_outer", companies=None, category=None, name="socal", workers=1, limit=None, out=None)
    assert cli.cmd_sweep(a) == 3
    run_dir = next((workspace / "runs").glob("sweep-socal-*"))
    meta = json.loads((run_dir / "meta.json").read_text())
    assert meta["kind"] == "sweep" and meta["total_fetched"] == 8
    g = gids(run_dir)
    assert ("Otherco", "Full Stack Engineer") not in g          # Seattle only: outside the regions
    assert ("Otherco", "Frontend Engineer") in g                # Santa Monica: home
    assert ("Otherco", "Platform Engineer") in g                # Temecula: home_outer by the city hint; 3 years is within the limit
    locs = (run_dir / "screen" / "locations.md").read_text()
    lines = [f"{g[k]} keep software" for k in g if k[1] in ("Frontend Engineer", "Software Engineer, Platform")]
    lines += [f"{g[k]} drop not software" for k in g if k[1] not in ("Frontend Engineer", "Software Engineer, Platform")]
    lines += ["L Irvine, California, United States => home", "L Santa Monica, CA => home"]
    if "Temecula Valley Office" in locs:
        lines.append("L Temecula Valley Office, California => home_outer")
    (run_dir / "screen" / "screen_01.txt").write_text("\n".join(lines) + "\n")
    assert cli.cmd_screen_apply(SimpleNamespace(run_dir=str(run_dir))) == 0
    cands = json.loads((run_dir / "candidates.json").read_text())
    assert sorted((c["company"], c["title"]) for c in cands) == [("Otherco", "Frontend Engineer"), ("Testco", "Software Engineer, Platform")]
    review(run_dir, {("Otherco", "Frontend Engineer"): {}, ("Testco", "Software Engineer, Platform"): {"work_match": 4}})
    ranked = rank.rank_and_report(run_dir, load_profile())
    assert {j["company"] for j in ranked} == {"Otherco", "Testco"}
    report = (run_dir / "REPORT.md").read_text()
    assert "**Otherco** ·" in report and "**Testco** ·" in report


def test_apply_list_orders_groups_and_explains_what_it_left_off(monkeypatch, workspace):
    setup_fakes(monkeypatch)
    a = SimpleNamespace(regions="home,home_outer", companies=None, category=None, name="socal", workers=1, limit=None, out=None)
    cli.cmd_sweep(a)
    run_dir = next((workspace / "runs").glob("sweep-socal-*"))
    g = gids(run_dir)
    lines = [f"{v} keep software" for k, v in g.items() if k[1] != "Mechanical Design Engineer"]
    lines += [f"{v} drop mech" for k, v in g.items() if k[1] == "Mechanical Design Engineer"]
    lines += ["L Irvine, California, United States => home", "L Santa Monica, CA => home",
              "L Temecula Valley Office, California => home_outer"]
    (run_dir / "screen" / "screen_01.txt").write_text("\n".join(lines) + "\n")
    cli.cmd_screen_apply(SimpleNamespace(run_dir=str(run_dir)))
    cands = {(c["company"], c["title"]) for c in json.loads((run_dir / "candidates.json").read_text())}
    rows = {k: {} for k in cands}
    review(run_dir, rows)
    tracker.add("Testco", "Software Engineer, Platform", job_id="1", url="https://x/1")  # already sent: must drop off
    (workspace / "profile.yaml").write_text((workspace / "profile.yaml").read_text().replace(
        "referrals: []", 'referrals:\n  - {company: "Otherco", contact: "Sam"}').replace("max_required_years: 3", "max_required_years: 2"))
    out = applylist.build(load_profile(), rerank=True)
    md = (workspace / "APPLY_LIST.md").read_text()
    assert out["referral"] == 1 and "| Sam |" in md
    assert "Software Engineer, Platform" not in md.split("## Not on this list")[0]   # already applied
    assert "1 role you already applied to" in md
    assert ("Otherco", "Platform Engineer") in cands
    assert "1 role asking for more than 2 years" in md                 # 3+ years asked, above the new limit of 2
    assert (workspace / "apply_list.html").read_text().count("Frontend Engineer") >= 1
