"""Find what the user already has about their own work: old resumes, CVs, cover letters, self-reviews, brag documents,
local code repositories and their GitHub activity. Run only after the user agrees (the gather-sources skill asks).

    python3 -m jobhunt gather [--roots ~/Desktop,~/Documents] [--depth 5] [--no-files] [--no-repos] [--no-github]
                              [--email you@example.com] [--exclude ~/Documents/Taxes]
    python3 -m jobhunt gather text <file>       # the text of one document (PDF, DOCX, DOC/RTF/Pages on macOS, TXT, MD, TEX)

The scan reads names, sizes, dates and git metadata only; it never opens a document. It writes
workspace/sources/manifest.json and manifest.md, which the agent shows the user before reading anything. Folders that
hold secrets or unrelated personal life (keychains, SSH keys, password managers, mail, photos, app data) are never
entered, and files whose names look like taxes, banking, medical or identity documents are never listed.
Everything stays in workspace/, which git ignores.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from . import paths

HOME = Path.home()

# Where people keep documents and code. Only the ones that exist are scanned.
DEFAULT_ROOTS = ["~/Desktop", "~/Documents", "~/Downloads", "~/Projects", "~/projects", "~/code", "~/Code", "~/dev",
                 "~/src", "~/repos", "~/git", "~/GitHub", "~/workspace", "~/Developer", "~/School", "~/OneDrive",
                 "~/Dropbox", "~/Google Drive", "~/Library/Mobile Documents/com~apple~CloudDocs"]

# Never entered, whatever the roots say.
SKIP_DIRS = {"node_modules", ".venv", "venv", "env", "__pycache__", ".git", ".hg", ".svn", "dist", "build", "target",
             ".next", ".cache", ".gradle", ".idea", ".vscode", "Pods", "DerivedData", ".tox", ".mypy_cache",
             "site-packages", "vendor", ".terraform", "coverage", ".ssh", ".gnupg", ".aws", ".kube", ".docker",
             "Keychains", "Mail", "Messages", "Photos Library.photoslibrary", "Application Support", "Containers",
             "Group Containers", "Caches", "Logs", "Cookies", "1Password", "Bitwarden", ".password-store",
             "Library", "Applications", "Music", "Movies", "Pictures", ".Trash", "workspace_private"}
# Names that look like private paperwork rather than work history: never listed, never read.
SENSITIVE = re.compile(r"tax|w-?2\b|1099|1040|lease|rental|mortgage|bank|statement|paystub|pay ?stub|payslip|salary|"
                       r"offer[ _-]?letter|medical|health|insurance|passport|license|ssn|social[ _-]?security|"
                       r"birth[ _-]?cert|visa|i-?9|immigration|divorce|court|loan|credit|invoice|receipt|password|"
                       r"secret|credential|\.env\b|private[ _-]?key|id[ _-]?card|transcript", re.I)
DOC_EXT = {".pdf", ".docx", ".doc", ".pages", ".rtf", ".odt", ".tex", ".md", ".txt"}
KINDS = [
    ("resume", re.compile(r"r[eé]sum[eé]|\bcv\b|curriculum[ _-]?vitae|vitae", re.I)),
    ("cover_letter", re.compile(r"cover[ _-]?letter", re.I)),
    ("review", re.compile(r"self[ _-]?(?:review|assessment|eval)|performance[ _-]?review|perf[ _-]?review|promo(?:tion)?[ _-]?"
                          r"(?:packet|doc|case)|annual[ _-]?review|year[ _-]?in[ _-]?review|feedback", re.I)),
    ("brag", re.compile(r"brag|accomplishment|achievement|wins\b|impact[ _-]?(?:doc|log)|work[ _-]?log|portfolio", re.I)),
    ("linkedin", re.compile(r"linkedin|profile\.pdf$", re.I)),
]


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p)).resolve()


def default_roots() -> list[Path]:
    """The default folders that exist, once each (macOS treats ~/Projects and ~/projects as the same folder)."""
    out = []
    for r in (_expand(x) for x in DEFAULT_ROOTS):
        if r.is_dir() and not any(os.path.samefile(r, o) for o in out):
            out.append(r)
    return out


def _walk(roots: list[Path], depth: int, exclude: list[Path]):
    """(dirpath, filenames, is_repo) under each root, depth-limited, skipping SKIP_DIRS, hidden dirs and exclusions.
    A repository is yielded but not descended into: its contents are code, read through git instead."""
    seen = set()
    for root in roots:
        base = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            d = Path(dirpath)
            if d in seen or any(d == e or e in d.parents for e in exclude):
                dirnames[:] = []
                continue
            seen.add(d)
            is_repo = ".git" in dirnames or ".git" in filenames  # a .git file: a worktree or submodule
            if is_repo or len(d.parts) - base >= depth:
                dirnames[:] = []
            else:
                dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS and not n.startswith(".")]
            yield d, filenames, is_repo


def scan(roots: list[Path], depth: int = 5, exclude: list[Path] | None = None, files: bool = True,
         repos: bool = True, emails: list[str] | None = None) -> dict:
    exclude = exclude or []
    docs, repo_dirs, skipped_sensitive = [], [], 0
    for d, filenames, is_repo in _walk(roots, depth, exclude):
        if is_repo:
            if repos:
                repo_dirs.append(d)
            continue
        if not files:
            continue
        for name in filenames:
            p = d / name
            if p.suffix.lower() not in DOC_EXT:
                continue
            kind = next((k for k, rx in KINDS if rx.search(name)), None)
            if not kind:
                continue
            if SENSITIVE.search(name):
                skipped_sensitive += 1
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            docs.append({"path": str(p), "kind": kind, "size_kb": round(st.st_size / 1024),
                         "modified": datetime.fromtimestamp(st.st_mtime).date().isoformat()})
    docs.sort(key=lambda x: (x["kind"], x["modified"]), reverse=True)
    emails = [e.lower() for e in (emails or []) + [_git_email()] if e]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:  # bounded per repo; a slow repo never holds up the rest
        repo_info = [r for r in pool.map(lambda d: repo_summary(d, emails), repo_dirs) if r]
    repo_info.sort(key=lambda r: (r["my_commits"] > 0, r["last_commit"] or ""), reverse=True)
    return {"roots": [str(r) for r in roots], "documents": docs, "repos": repo_info,
            "skipped_sensitive_files": skipped_sensitive, "emails_matched": sorted(set(emails))}


GIT_TIMEOUT = 15  # seconds per git command


class SlowRepo(Exception):
    pass


def _git(d: Path, *args: str, timeout: int = GIT_TIMEOUT) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    try:
        return subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True, timeout=timeout,
                              env=env).stdout.strip()
    except subprocess.TimeoutExpired:
        raise SlowRepo
    except OSError:
        return ""


def _git_email() -> str:
    try:
        return subprocess.run(["git", "config", "--global", "user.email"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


_LANG = {".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".py": "Python",
         ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".c": "C", ".h": "C/C++",
         ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".scala": "Scala",
         ".sql": "SQL", ".lua": "Lua", ".dart": "Dart", ".m": "Objective-C", ".vue": "Vue", ".svelte": "Svelte",
         ".ex": "Elixir", ".hs": "Haskell", ".ml": "OCaml", ".r": "R", ".jl": "Julia", ".tf": "Terraform"}
_MANIFESTS = ("package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
              "Gemfile", "Podfile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml", "serverless.yml")


def repo_summary(d: Path, emails: list[str]) -> dict | None:
    """What a repository says about the user's work, from git metadata: remote, dates, commits they authored, languages
    by file count, the manifests that name the stack, and the README path. No source file is read."""
    try:
        if not _git(d, "rev-parse", "--git-dir"):
            return None
        remote = _git(d, "remote", "get-url", "origin")
        # The checked-out branch's history only: `--all` reads every object, which is slow when the repository's files
        # live in iCloud or OneDrive and haven't been downloaded.
        authors = _git(d, "log", "HEAD", "--max-count=20000", "--format=%ae|%ad", "--date=short").splitlines()
        files = _git(d, "ls-files").splitlines()
    except SlowRepo:
        return {"path": str(d), "remote": "", "commits_total": 0, "my_commits": 0, "my_first": None, "my_last": None,
                "first_commit": None, "last_commit": None, "languages": {}, "manifests": [], "readme": None, "files": 0,
                "slow": "git took too long here; its files may be stored in iCloud or OneDrive and not downloaded "
                        "(open the folder once to download it, then scan again)"}
    mine = [a.split("|")[1] for a in authors if "|" in a and a.split("|")[0].lower() in emails]
    langs: dict[str, int] = {}
    for f in files:
        lang = _LANG.get(Path(f).suffix.lower())
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    readme = next((f for f in files if Path(f).name.lower() in ("readme.md", "readme", "readme.rst", "readme.txt")
                   and "/" not in f), None)
    all_dates = sorted(a.split("|")[1] for a in authors if "|" in a)
    return {"path": str(d), "remote": remote,
            "commits_total": len(authors), "my_commits": len(mine),
            "my_first": min(mine) if mine else None, "my_last": max(mine) if mine else None,
            "first_commit": all_dates[0] if all_dates else None, "last_commit": all_dates[-1] if all_dates else None,
            "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])[:6]),
            "manifests": sorted({Path(f).name for f in files if Path(f).name in _MANIFESTS})[:10],
            "readme": str(d / readme) if readme else None, "files": len(files)}


def github() -> dict:
    """The signed-in user's GitHub repositories and pull requests, through the gh CLI. Empty with a reason when gh is
    missing or not signed in. Merge status comes from GitHub at the time of the scan; check it again before claiming
    'merged' on a resume."""
    if not shutil.which("gh"):
        return {"error": "gh (GitHub CLI) is not installed; install it and run `gh auth login`, or give your GitHub username"}

    def gh(*args: str) -> str:
        try:
            r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(str(e))
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:200])
        return r.stdout
    try:
        login = json.loads(gh("api", "user"))["login"]
        repos = json.loads(gh("repo", "list", login, "--limit", "300", "--json",
                              "nameWithOwner,description,primaryLanguage,stargazerCount,isFork,isPrivate,pushedAt,url,homepageUrl"))
        fields = "repository,title,state,url,createdAt,closedAt,number"
        prs = json.loads(gh("search", "prs", "--author", "@me", "--limit", "300", "--json", fields))
        merged = {p["url"] for p in json.loads(gh("search", "prs", "--author", "@me", "--merged", "--limit", "300", "--json", "url"))}
    except (RuntimeError, ValueError, KeyError) as e:
        return {"error": f"gh could not read your account ({e}); run `gh auth login`"}
    for p in prs:
        p["merged"] = p["url"] in merged
        p["repository"] = (p.get("repository") or {}).get("nameWithOwner")
    outside = [p for p in prs if p["repository"] and not p["repository"].lower().startswith(login.lower() + "/")]
    return {"login": login,
            "repos": [{"name": r["nameWithOwner"], "description": r.get("description") or "",
                       "language": (r.get("primaryLanguage") or {}).get("name"), "stars": r.get("stargazerCount", 0),
                       "fork": r.get("isFork"), "private": r.get("isPrivate"), "pushed": (r.get("pushedAt") or "")[:10],
                       "url": r.get("url"), "homepage": r.get("homepageUrl") or ""} for r in repos],
            "prs_to_other_projects": sorted(outside, key=lambda p: p.get("createdAt") or "", reverse=True)}


# ----------------------------------------------------------------------------- reading one document
def extract_text(path: str | Path) -> str:
    """Plain text of one document. PDF via pdftotext; DOCX and ODT unzipped (no extra packages); DOC, RTF and Pages
    via macOS textutil when present; everything else read as text."""
    p = _expand(str(path))
    if SENSITIVE.search(p.name):
        raise PermissionError(f"{p.name} looks like private paperwork, not work history; not reading it")
    suf = p.suffix.lower()
    if suf == ".pdf":
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext (poppler) is needed to read PDFs")
        return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=60).stdout
    if suf in (".docx", ".odt"):
        part = "word/document.xml" if suf == ".docx" else "content.xml"
        with zipfile.ZipFile(p) as z:
            xml = z.read(part).decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>|</text:p>|<w:br/>|<w:tab/>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", xml)
        import html
        return re.sub(r"\n{3,}", "\n\n", html.unescape(text)).strip()
    if suf in (".doc", ".rtf", ".pages"):
        if shutil.which("textutil"):
            return subprocess.run(["textutil", "-convert", "txt", "-stdout", str(p)], capture_output=True, text=True,
                                  timeout=60).stdout
        raise RuntimeError(f"can't read {suf} here; export it as PDF or DOCX")
    return p.read_text(errors="ignore")


# ----------------------------------------------------------------------------- output
def write_manifest(result: dict) -> Path:
    out = paths.workspace() / "sources"
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(result, indent=1))
    md = [f"# Sources found {datetime.now():%Y-%m-%d %H:%M}", "",
          "Names and metadata only; nothing below has been opened yet. Tell the agent which to read (or \"all\"), and "
          "anything to leave out.", ""]
    docs = result.get("documents") or []
    md += [f"## Documents ({len(docs)})", ""]
    if not docs:
        md.append("(none found)")
    # Grouped by folder, newest first. A folder of many tailored copies shows its newest few; manifest.json has all.
    folders: dict[tuple, list] = {}
    for d in docs:
        folders.setdefault((d["kind"], str(Path(d["path"]).parent)), []).append(d)
    for (kind, folder), items in sorted(folders.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
        items.sort(key=lambda d: d["modified"], reverse=True)
        md.append(f"**{kind} in {folder}** ({len(items)}; {items[-1]['modified']} to {items[0]['modified']})")
        md += [f"- {Path(d['path']).name} ({d['size_kb']} KB, modified {d['modified']})" for d in items[:8]]
        if len(items) > 8:
            md.append(f"- ... and {len(items) - 8} more here (all listed in manifest.json)")
        md.append("")
    if result.get("skipped_sensitive_files"):
        md.append(f"\n{result['skipped_sensitive_files']} files with names like taxes, banking, medical or ID papers were "
                  "skipped and not listed.")
    repos = result.get("repos") or []
    mine = [r for r in repos if r["my_commits"]]
    md += ["", f"## Local code repositories ({len(repos)}; {len(mine)} with commits by you)", ""]
    for r in repos:
        if r.get("slow"):
            md.append(f"- {r['path']}: not read ({r['slow']})")
            continue
        langs = ", ".join(r["languages"]) or "-"
        when = f"{r['my_first']} to {r['my_last']}" if r["my_commits"] else f"last commit {r['last_commit']}"
        md.append(f"- {r['path']}: {r['my_commits']}/{r['commits_total']} commits by you, {when}; {langs}"
                  + (f"; {r['remote']}" if r["remote"] else ""))
    if not repos:
        md.append("(none found)")
    gh = result.get("github")
    if gh is not None:
        md += ["", "## GitHub", ""]
        if gh.get("error"):
            md.append(gh["error"])
        else:
            own = [r for r in gh["repos"] if not r["fork"]]
            md.append(f"Signed in as {gh['login']}: {len(own)} repositories of your own, "
                      f"{len(gh['prs_to_other_projects'])} pull requests to other projects.")
            md += ["", "Pull requests to other projects:"]
            md += [f"- {p['repository']} #{p['number']}: {p['title']} ({'merged' if p['merged'] else p['state']}) {p['url']}"
                   for p in gh["prs_to_other_projects"][:60]] or ["- (none)"]
            md += ["", "Your repositories (newest push first):"]
            md += [f"- {r['name']}{' (private)' if r['private'] else ''}: {r['description'] or 'no description'}; "
                   f"{r['language'] or '-'}; {r['stars']} stars; pushed {r['pushed']}"
                   for r in sorted(own, key=lambda r: r["pushed"], reverse=True)[:60]]
    (out / "manifest.md").write_text("\n".join(md) + "\n")
    return out / "manifest.md"


def run(args) -> int:
    if args.action == "text":
        if not args.target:
            print("usage: python3 -m jobhunt gather text <file>", file=sys.stderr)
            return 2
        try:
            print(extract_text(args.target))
        except (OSError, RuntimeError, PermissionError, zipfile.BadZipFile, KeyError) as e:
            print(f"could not read {args.target}: {e}", file=sys.stderr)
            return 1
        return 0
    roots = [_expand(r) for r in args.roots.split(",")] if args.roots else default_roots()
    roots = [r for r in roots if r.is_dir()]
    exclude = [_expand(e) for e in (args.exclude or "").split(",") if e.strip()]
    print("Scanning names and git metadata only (no document is opened) in:", file=sys.stderr)
    for r in roots:
        print(f"  {r}", file=sys.stderr)
    result = scan(roots, args.depth, exclude, files=not args.no_files, repos=not args.no_repos,
                  emails=[e.strip() for e in (args.email or "").split(",") if e.strip()])
    if not args.no_github:
        result["github"] = github()
    md = write_manifest(result)
    gh = result.get("github") or {}
    print(json.dumps({"manifest": str(md), "documents": len(result["documents"]), "repos": len(result["repos"]),
                      "repos_with_your_commits": sum(1 for r in result["repos"] if r["my_commits"]),
                      "repos_too_slow_to_read": sum(1 for r in result["repos"] if r.get("slow")),
                      "github": gh.get("login") or gh.get("error") or "skipped",
                      "github_prs_to_other_projects": len(gh.get("prs_to_other_projects") or []),
                      "skipped_sensitive_files": result["skipped_sensitive_files"]}, indent=1))
    return 0
