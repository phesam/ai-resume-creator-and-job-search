"""Resume builder: style checks, file naming, the real PDF build of the template resume, and the privacy scan."""

import shutil
from pathlib import Path

import pytest
import yaml

from jobhunt import privacy, resume

ROOT = Path(__file__).resolve().parents[1]


def _r(*bullets, skills=None):
    return {"experience": [{"title": "Software Engineer", "bullets": list(bullets)}], "projects": [],
            "skills": skills or {"Languages": "TypeScript, Python"}}


def test_style_flags_what_the_case_study_rejected():
    out = resume.lint_style(_r(
        "Helped with various frontend tasks using React",                        # weak opener, banned word, no purpose, short
        "Built the **React** dashboard and the **GraphQL** service that clinic staff use to change schedules in ~2 minutes",
        "I set up dashboards and alerts for our services on Kubernetes and owned the on-call rotation for both of them",
    ), {"jargon": ["GMS"], "banned_phrases": ["increasing developer velocity"]})
    text = "\n".join(out)
    assert "weak opener" in text and "'various'" in text and "no number and no stated purpose" in text
    assert "more than one bold" in text
    assert "first person" in text


def test_style_passes_a_bullet_that_says_what_and_why():
    good = ("Built the Node.js/GraphQL service that lets clinic staff change their own schedules (~2M requests/day), so a "
            "schedule change takes **~2 minutes instead of a support ticket and a next-day release**")
    assert resume.lint_style(_r(good)) == []


def test_style_counts_keyword_stuffing():
    b = "Built a GraphQL service for clinic staff with GraphQL subscriptions, GraphQL caching and GraphQL federation, used by 4 teams"
    out = resume.lint_style(_r(b, skills={"Tools": "GraphQL, React"}), {"max_keyword_repeats": 3})
    assert any("'GraphQL' appears in 4" in x for x in out)


def test_internal_names_are_flagged():
    out = resume.lint_style(_r("Built GMS Content so 4 teams can publish pages without a release, replacing a 2-day wait"),
                            {"jargon": ["GMS"]})
    assert any("internal name 'GMS'" in x for x in out)


def test_pdf_name():
    assert resume.pdf_name({"header": {"name": "Jordan Lee"}}) == "Jordan_Lee_Resume.pdf"
    assert resume.pdf_name({"header": {"name": "Ana María O'Neil"}}) == "Ana_Mar_a_O_Neil_Resume.pdf"
    assert resume.pdf_name({}) == "Resume.pdf"


def test_emphasize_never_adds_a_skill():
    r = {"skills": {"Languages": "TypeScript, Python"}}
    resume.emphasize_skills(r, ["Go", "Python"])
    assert r["skills"]["Languages"] == "Python, TypeScript"


@pytest.mark.skipif(not resume.find_chrome() or not shutil.which("pdftotext"), reason="needs Chrome and poppler")
def test_template_resume_builds_clean(tmp_path):
    rep = resume.build(ROOT / "templates" / "resume.yaml", tmp_path / "Jordan_Lee_Resume.pdf", "general")
    assert rep["status"] == "ok", rep
    assert rep["lint"] == [] and rep["short_last_lines"] == [], rep
    assert rep["style"] == [], rep["style"]          # the example must follow its own rules
    assert rep["measure"]["pages"] == 1


def test_template_resume_claims_are_all_fictional():
    data = yaml.safe_load((ROOT / "templates" / "resume.yaml").read_text())
    contact = " ".join(data["header"]["contact"])
    assert "555" in contact and "example" in contact


def test_privacy_scan_finds_terms_emails_and_phones(tmp_path):
    f = tmp_path / "notes.md"
    email, phone = "jane" + "@realmail.com", "(415) 555-" + "2671"  # built at runtime so this file passes its own scan
    f.write_text(f"Jane Q. Example worked at Initrode.\nmail {email} or {phone}\nsafe: jordan.lee@example.com, (555) 010-0199\n")
    hits = privacy.scan(["Initrode"], [f])
    assert any("term 'Initrode'" in h for h in hits)
    assert any(email in h for h in hits)
    assert any(phone in h for h in hits)
    assert not any("example.com" in h or "010-0199" in h for h in hits)
