"""The consent-based source finder: what it lists, what it never touches, and how it reads documents."""

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from jobhunt import gather

ROOT = Path(__file__).resolve().parents[1]


def _touch(p, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _repo(d, email, commits=3):
    d.mkdir(parents=True)
    env = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": email,
           "HOME": str(d), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
    _touch(d / "README.md", "# Trail app")
    _touch(d / "src" / "app.ts", "export {}")
    _touch(d / "package.json", "{}")
    for i in range(commits):
        _touch(d / f"f{i}.py", str(i))
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", f"c{i}"], check=True, env=env)


def test_scan_lists_work_documents_and_skips_private_paperwork(tmp_path):
    root = tmp_path / "Documents"
    _touch(root / "Jordan_Lee_Resume_2024.pdf")
    _touch(root / "old" / "CV final.docx")
    _touch(root / "Self Review 2025.docx")
    _touch(root / "brag doc.md")
    _touch(root / "Cover Letter - Acme.pdf")
    _touch(root / "2025 Tax Return.pdf")                 # private: never listed
    _touch(root / "Resume for apartment lease.pdf")      # private, even with "resume" in the name
    _touch(root / "vacation.pdf")                        # not work history
    _touch(root / "node_modules" / "resume.pdf")         # never entered
    _touch(root / ".hidden" / "resume.pdf")
    out = gather.scan([root], depth=5, repos=False)
    names = {p["path"].split("/")[-1]: p["kind"] for p in out["documents"]}
    assert names == {"Jordan_Lee_Resume_2024.pdf": "resume", "CV final.docx": "resume", "Self Review 2025.docx": "review",
                     "brag doc.md": "brag", "Cover Letter - Acme.pdf": "cover_letter"}
    assert out["skipped_sensitive_files"] == 1   # the lease "resume"; the tax return was never a candidate at all


def test_excluded_folders_are_never_entered(tmp_path):
    root = tmp_path / "Desktop"
    _touch(root / "keep" / "resume.pdf")
    _touch(root / "private" / "resume.pdf")
    out = gather.scan([root], exclude=[root / "private"], repos=False)
    assert [d["path"] for d in out["documents"]] == [str(root / "keep" / "resume.pdf")]


@pytest.mark.skipif(not shutil.which("git"), reason="needs git")
def test_repos_report_commits_by_you_and_the_stack(tmp_path):
    root = tmp_path / "code"
    _repo(root / "trailmix", "jordan@example.com", commits=3)
    _repo(root / "someone-elses", "other@example.com", commits=2)
    out = gather.scan([root], files=False, emails=["jordan@example.com"])
    by = {r["path"].split("/")[-1]: r for r in out["repos"]}
    assert by["trailmix"]["my_commits"] == 3 and by["someone-elses"]["my_commits"] == 0
    assert out["repos"][0]["path"].endswith("trailmix")          # your work first
    assert by["trailmix"]["languages"].get("Python") == 3 and "TypeScript" in by["trailmix"]["languages"]
    assert by["trailmix"]["manifests"] == ["package.json"] and by["trailmix"]["readme"].endswith("README.md")


def test_docx_text_and_sensitive_refusal(tmp_path):
    p = tmp_path / "CV.docx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("word/document.xml", '<w:document><w:body><w:p><w:r><w:t>Built the booking flow &amp; API</w:t></w:r></w:p>'
                                        '<w:p><w:r><w:t>Second line</w:t></w:r></w:p></w:body></w:document>')
    assert gather.extract_text(p).splitlines() == ["Built the booking flow & API", "Second line"]
    with pytest.raises(PermissionError):
        gather.extract_text(_touch(tmp_path / "bank statement.txt"))


def test_github_through_gh(monkeypatch):
    calls = {
        ("api", "user"): {"login": "jlee"},
        "repo": [{"nameWithOwner": "jlee/trailmix", "description": "Trail reports", "primaryLanguage": {"name": "TypeScript"},
                  "stargazerCount": 4, "isFork": False, "isPrivate": False, "pushedAt": "2026-03-01T00:00:00Z",
                  "url": "https://github.com/jlee/trailmix", "homepageUrl": ""}],
        "prs": [{"repository": {"nameWithOwner": "ssg/site-gen"}, "title": "Cache unchanged pages", "state": "closed",
                 "url": "https://github.com/ssg/site-gen/pull/7", "number": 7, "createdAt": "2026-03-02", "closedAt": "2026-03-09"},
                {"repository": {"nameWithOwner": "jlee/trailmix"}, "title": "own repo", "state": "closed",
                 "url": "https://github.com/jlee/trailmix/pull/1", "number": 1, "createdAt": "2026-01-01", "closedAt": None}],
        "merged": [{"url": "https://github.com/ssg/site-gen/pull/7"}],
    }

    class R:
        def __init__(self, out):
            self.stdout, self.returncode, self.stderr = json.dumps(out), 0, ""

    def fake_run(cmd, **kw):
        args = cmd[1:]
        if args[:2] == ["api", "user"]:
            return R(calls[("api", "user")])
        if args[0] == "repo":
            return R(calls["repo"])
        return R(calls["merged"] if "--merged" in args else calls["prs"])

    monkeypatch.setattr(gather.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(gather.subprocess, "run", fake_run)
    gh = gather.github()
    assert gh["login"] == "jlee" and gh["repos"][0]["language"] == "TypeScript"
    assert [p["repository"] for p in gh["prs_to_other_projects"]] == ["ssg/site-gen"]   # PRs to your own repos aren't contributions
    assert gh["prs_to_other_projects"][0]["merged"] is True


def test_manifest_is_written_to_the_workspace(workspace, tmp_path):
    _touch(tmp_path / "docs" / "resume.pdf")
    result = gather.scan([tmp_path / "docs"], repos=False)
    result["github"] = {"error": "gh (GitHub CLI) is not installed"}
    md = gather.write_manifest(result)
    assert md == workspace / "sources" / "manifest.md"
    text = md.read_text()
    assert "resume.pdf" in text and "nothing below has been opened yet" in text and "not installed" in text


def test_keywords_marks_what_your_resume_shows(workspace, capsys):
    from types import SimpleNamespace

    from jobhunt import keywords
    run = workspace / "runs" / "acme"
    run.mkdir(parents=True)
    desc = "We use Kafka, Go and Terraform with PostgreSQL. " * 6
    (run / "candidates.json").write_text(json.dumps([{"title": "Backend Engineer", "description": desc}] * 3))
    (workspace / "resume.yaml").write_text('experience:\n  - bullets: ["Built a Kafka consumer in Java"]\nskills:\n  Tools: "Terraform"\n')
    (workspace / "inventory.md").write_text("Used PostgreSQL at my last job.")
    assert keywords.run(SimpleNamespace(run=str(run), companies=None)) == 0
    out = capsys.readouterr().out
    assert "| Kafka | 3 | 100% | in a bullet |" in out
    assert "| Terraform | 3 | 100% | skills line only |" in out
    assert "| PostgreSQL | 3 | 100% | IN INVENTORY, NOT ON RESUME |" in out
    assert "| Go | 3 | 100% | - |" in out


def test_keywords_never_suggests_what_you_said_not_to_claim(workspace, capsys):
    from types import SimpleNamespace

    from jobhunt import keywords
    run = workspace / "runs" / "acme"
    run.mkdir(parents=True)
    desc = "We use Kafka, Terraform, GraphQL and PostgreSQL. " * 6
    (run / "candidates.json").write_text(json.dumps([{"title": "Backend Engineer", "description": desc}] * 3))
    template = (ROOT / "templates" / "inventory.md").read_text()
    (workspace / "inventory.md").write_text(template + "Used PostgreSQL at work.\n**Do not claim:** Terraform\n- Do not list (could not defend): Kafka\n")
    assert keywords.run(SimpleNamespace(run=str(run), companies=None)) == 0
    out = capsys.readouterr().out
    assert "| PostgreSQL | 3 | 100% | IN INVENTORY, NOT ON RESUME |" in out
    assert "| Terraform | 3 | 100% | - |" in out and "| Kafka | 3 | 100% | - |" in out
    assert "| GraphQL | 3 | 100% | - |" in out      # the inventory template's own instructions mention it


def test_keywords_ignores_the_fictional_template_resume(workspace, capsys):
    from types import SimpleNamespace

    from jobhunt import keywords
    run = workspace / "runs" / "acme"
    run.mkdir(parents=True)
    (run / "candidates.json").write_text(json.dumps([{"title": "Engineer", "description": "We use Kubernetes daily. " * 12}]))
    shutil.copy(ROOT / "templates" / "resume.yaml", workspace / "resume.yaml")
    assert keywords.run(SimpleNamespace(run=str(run), companies=None)) == 0
    assert "| Kubernetes | 1 | 100% | - |" in capsys.readouterr().out
