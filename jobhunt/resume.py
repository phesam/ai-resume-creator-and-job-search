"""Render resume YAML -> HTML -> one-page PDF (headless Chrome), auto-fit to fill the page, then check it.

python3 -m jobhunt resume --variant general          # usual entry point (workspace paths filled in)
python3 -m jobhunt.resume workspace/resume.yaml --variant general --out /tmp/Jordan_Lee_Resume.pdf

Fit loop: a single density knob t in [0, 1] scales font size, line height and spacing between
compact and roomy presets. We binary-search the roomiest layout that still fits on one page, so the
page ends up full (no big empty band at the bottom) without shrinking text more than needed.
If even the most compact layout overflows, or the roomiest leaves a gap, we say so instead of hiding it.

Checks on every build (ship only when status is ok and lint and short_last_lines are empty):
  status            ok: one full page. overflow: too long. underfull: blank space at the bottom. Only an ok build is
                    written to the final path; the others go to .overflow.pdf or .underfull.pdf, so a page with a gap
                    can't be sent by accident. Body text stays 10.5-10.9pt: thin content fails, it doesn't get bigger.
  lint              the text an ATS extracts: odd Unicode, contact details, every bullet verbatim, reading order
  short_last_lines  a stranded word on a last line, or a bullet running to three lines
  style             advisory: weak openers, too much bold, no number or stated purpose, overused keywords,
                    first person, banned phrases and internal jargon you listed in resume.yaml
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import yaml

from .terms import technical_terms

PAGE_H = 792.0  # letter, points
PAGE_W = 612.0

_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_chrome() -> str | None:
    """CHROME_PATH, then the usual install locations, then anything Chrome-like on PATH."""
    if os.environ.get("CHROME_PATH") and Path(os.environ["CHROME_PATH"]).exists():
        return os.environ["CHROME_PATH"]
    for c in _CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome"):
        hit = shutil.which(name)
        if hit:
            return hit
    return None


# compact -> roomy presets (font pt, line-height, bullet gap pt, entry gap pt, section gap pt, margin in)
# The bullet and entry gaps are deliberately generous: with 0.6-2.4pt gaps, bullets ran together into one block that
# read as a wall of text. The fit loop pays for the gaps with slightly smaller text.
# Body text stays between 10.5 and 11pt: that is what a page of real content looks like. There is deliberately no bigger
# preset. Growing the text to 12pt and widening the margins is how a thin resume ends up looking thin; thin content has to
# fail the build instead, so it gets more content.
PRESET_LO = dict(font=10.5, lh=1.12, bullet=3.2, entry=5.0, section=5.0, margin_tb=0.45, margin_lr=0.55, name=19.0)
PRESET_HI = dict(font=10.9, lh=1.16, bullet=3.8, entry=6.0, section=7.0, margin_tb=0.5, margin_lr=0.6, name=20.0)
FILL_TOLERANCE_PT = 7.0  # a finished page ends within this of the bottom margin: about half a line
MAX_STRETCH_PT = 0.8     # the most added per bullet gap to close the last line or so (entries get 1.5x, sections 2x)


def lerp(t: float, stretch: float = 0.0) -> dict:
    p = {k: PRESET_LO[k] + (PRESET_HI[k] - PRESET_LO[k]) * t for k in PRESET_LO}
    p["bullet"] += stretch
    p["entry"] += 1.5 * stretch
    p["section"] += 2 * stretch
    return p


# ----------------------------------------------------------------------------- data
def load_resume(path: Path, variant: str | None, wording: str | None = None) -> dict:
    """`wording` picks a named alternative text for bullets that define one (`alt: {name: "..."}`)."""
    data = yaml.safe_load(path.read_text())
    variant = variant or data.get("default_variant", "general")
    v = (data.get("variants") or {}).get(variant, {})
    out = {k: data[k] for k in ("header", "education", "style") if k in data}
    out["variant"] = variant
    out["section_order"] = v.get("section_order") or data.get("section_order") or ["experience", "projects", "education", "skills"]

    def pick(items, order_key, drop_key):
        order = v.get(order_key)
        drop = set(v.get(drop_key) or [])
        items = [dict(i) for i in items if i.get("id") not in drop and variant not in (i.get("exclude_variants") or [])]
        if order:
            by = {i.get("id"): i for i in items}
            items = [by[k] for k in order if k in by] + [i for i in items if i.get("id") not in order]
        return items

    out["experience"] = pick(data.get("experience", []), "experience_order", "drop_experience")
    out["projects"] = pick(data.get("projects", []), "projects_order", "drop_projects")
    for coll in (out["experience"], out["projects"]):
        for item in coll:
            bullets = []
            for b in item.get("bullets", []):
                if isinstance(b, str):
                    bullets.append(b)
                elif variant in (b.get("variants") or [variant]) and variant not in (b.get("exclude_variants") or []):
                    bullets.append((b.get("alt") or {}).get(wording) or b["text"])
            item["bullets"] = bullets
    out["skills"] = v.get("skills") or data.get("skills")
    if v.get("contact_extra"):
        out["header"] = dict(out["header"])
        out["header"]["contact"] = list(out["header"]["contact"]) + list(v["contact_extra"])
    out["projects_heading"] = v.get("projects_heading") or data.get("projects_heading") or "Projects"
    return out


# ----------------------------------------------------------------------------- html
def _inline(s: str) -> str:
    """Escape, allow **bold**, and keep hyphenated words on one line.

    Chrome breaks lines after ASCII hyphens ("config-|driven"), which can extract as "config- driven".
    Wrapping the word in a nowrap span keeps a plain ASCII hyphen (never U+2011, which breaks ATS search).
    """
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"(?<![\w/.])(\w+(?:-\w+)+)(?![\w/])", r'<span class="nw">\1</span>', s)


def _contact_item(x: str) -> str:
    """Header contact text as written. Email, LinkedIn and GitHub are also clickable in the PDF; the visible text
    (what a parser extracts) is unchanged."""
    shown = f'<span class="nw">{_inline(x)}</span>'  # a contact item never breaks across lines (it must parse whole)
    plain = re.sub(r"\*\*", "", x).strip()
    if re.fullmatch(r"[\w.+-]+@[\w-]+\.[\w.]+", plain):
        return f'<a href="mailto:{html.escape(plain, quote=True)}">{shown}</a>'
    if re.match(r"(?:www\.)?(?:linkedin|github|gitlab)\.com/", plain) or re.match(r"[\w-]+\.[a-z]{2,}(?:/\S*)?$", plain):
        return f'<a href="https://{html.escape(plain, quote=True)}">{shown}</a>'
    return shown


def render_html(r: dict, t: float, stretch: float = 0.0) -> str:
    p = lerp(t, stretch)
    h = r["header"]
    accent = (r.get("style") or {}).get("accent", "#1d4f91")
    contact = " | ".join(_contact_item(x) for x in h["contact"])
    parts = []

    def entry_block(item: dict) -> str:
        right1 = _inline(item.get("dates", ""))
        right2 = _inline(item.get("location", ""))
        title = _inline(item.get("title", ""))
        org = _inline(item.get("org", ""))
        link = ""
        if item.get("link"):  # visible plain text (what a parser extracts) that is also clickable in the PDF
            url = html.escape(item["link"], quote=True)
            link = f' · <a href="https://{url}">{url}</a>'
        line1 = f'<div class="row"><span class="l"><b>{title}</b>{link}{(" — " + org) if item.get("inline_org") else ""}</span><span class="r">{right1}</span></div>'
        line2 = ""
        if org and not item.get("inline_org"):
            line2 = f'<div class="row sub"><span class="l"><i>{org}</i></span><span class="r"><i>{right2}</i></span></div>'
        bl = "".join(f"<li>{_inline(b)}</li>" for b in item.get("bullets", []))
        return f'<div class="entry">{line1}{line2}<ul>{bl}</ul></div>'

    for sec in r["section_order"]:
        if sec == "experience" and r.get("experience"):
            parts.append('<section><h2>Experience</h2>' + "".join(entry_block(e) for e in r["experience"]) + "</section>")
        elif sec == "projects" and r.get("projects"):
            parts.append(f'<section><h2>{_inline(r["projects_heading"])}</h2>' + "".join(entry_block(e) for e in r["projects"]) + "</section>")
        elif sec == "education" and r.get("education"):
            items = []
            for e in r["education"]:
                detail = f'<div class="row sub"><span class="l">{_inline(e.get("detail", ""))}</span><span class="r">{_inline(e.get("location", ""))}</span></div>' if e.get("detail") else ""
                lines = "".join(f'<div class="row sub"><span class="l">{_inline(x)}</span></div>' for x in e.get("lines") or [])
                items.append(f'<div class="entry"><div class="row"><span class="l"><b>{_inline(e["school"])}</b></span><span class="r">{_inline(e.get("dates", ""))}</span></div>{detail}{lines}</div>')
            parts.append('<section><h2>Education</h2>' + "".join(items) + "</section>")
        elif sec == "skills" and r.get("skills"):
            rows = "".join(f'<div class="skill"><b>{_inline(k)}:</b> {_inline(v)}</div>' for k, v in r["skills"].items())
            parts.append(f'<section><h2>Skills</h2>{rows}</section>')

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(h['name'])} Resume</title>
<meta name="author" content="{html.escape(h['name'])}">
<style>
@page {{ size: letter; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ font-family: "Times New Roman", Times, serif; font-size: {p['font']:.2f}pt; line-height: {p['lh']:.3f};
       color: #000; padding: {p['margin_tb']:.3f}in {p['margin_lr']:.3f}in; font-variant-ligatures: none;
       font-kerning: none; font-feature-settings: "kern" 0, "liga" 0; text-rendering: optimizeSpeed;
       -webkit-font-smoothing: antialiased; }}
h1 {{ font-size: {p['name']:.1f}pt; text-align: center; margin: 0 0 1pt 0; letter-spacing: 0.6pt; font-weight: bold;
      text-transform: uppercase; color: {accent}; }}
.contact {{ text-align: center; margin-bottom: {p['section'] * 0.4:.2f}pt; font-size: {min(p['font'], 11.0):.2f}pt; }}
h2 {{ font-size: {p['font'] + 1.0:.2f}pt; text-transform: uppercase; letter-spacing: 0.6pt; margin: {p['section']:.2f}pt 0 {p['entry'] * 0.45:.2f}pt 0;
      border-bottom: 0.8pt solid {accent}; padding-bottom: 1pt; font-weight: bold; color: {accent}; }}
section:first-of-type h2 {{ margin-top: {p['section'] * 0.5:.2f}pt; }}
.entry {{ margin-top: {p['entry']:.2f}pt; }}
.entry:first-of-type {{ margin-top: 0; }}
.row {{ display: flex; justify-content: space-between; gap: 12pt; }}
.row .r {{ white-space: nowrap; text-align: right; font-style: italic; }}
ul {{ margin: {p['bullet'] * 0.6:.2f}pt 0 0 0; padding-left: 14pt; }}
li {{ margin: 0 0 {p['bullet']:.2f}pt 0; padding-left: 1pt; }}
li:last-child {{ margin-bottom: 0; }}
.skill {{ margin-bottom: {p['bullet']:.2f}pt; }}
a {{ color: inherit; text-decoration: none; }}
.nw {{ white-space: nowrap; }}
</style></head><body>
<h1>{_inline(h['name'])}</h1>
<div class="contact">{contact}</div>
{''.join(parts)}
</body></html>"""


# ----------------------------------------------------------------------------- pdf
def chrome_pdf(html_path: Path, pdf_path: Path, timeout: float = 45) -> None:
    """Print with headless Chrome. Chrome sometimes writes the PDF but never exits, so we wait
    for the file to appear and stop changing, then terminate the process."""
    if pdf_path.exists():
        pdf_path.unlink()
    chrome = find_chrome()
    if not chrome:
        raise FileNotFoundError("No Chrome, Chromium or Edge found. Install one, or set CHROME_PATH to its executable.")
    prof = tempfile.mkdtemp(prefix="jh-chrome-")
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
           "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={prof}",
           f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start, last_size, stable = time.time(), -1, 0
    try:
        while time.time() - start < timeout:
            if proc.poll() is not None and pdf_path.exists():
                break
            if pdf_path.exists():
                size = pdf_path.stat().st_size
                stable = stable + 1 if size == last_size and size > 0 else 0
                last_size = size
                if stable >= 3:
                    break
            time.sleep(0.2)
        else:
            raise TimeoutError("Chrome did not produce a PDF in time")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(prof, ignore_errors=True)


def measure(pdf_path: Path) -> dict:
    """Pages, and how far down page 1 the last text line reaches (fraction of usable height)."""
    out = subprocess.run(["pdftotext", "-bbox-layout", str(pdf_path), "-"], capture_output=True, text=True).stdout
    pages = out.count("<page ")
    first_page = out.split("</page>")[0]
    ys = [float(m) for m in re.findall(r'<line xMin="[\d.]+" yMin="[\d.]+" xMax="[\d.]+" yMax="([\d.]+)"', first_page)]
    ymins = [float(m) for m in re.findall(r'<line xMin="[\d.]+" yMin="([\d.]+)"', first_page)]
    bottom = max(ys) if ys else 0.0
    top = min(ymins) if ymins else 0.0
    return {"pages": pages, "bottom_pt": round(bottom, 1), "top_pt": round(top, 1),
            "bottom_gap_pt": round(PAGE_H - bottom, 1)}


# ----------------------------------------------------------------------------- lint
BAD_CHARS = {
    "\u202f": "narrow no-break space", "\u2009": "thin space", "\u2007": "figure space", "\u2060": "word joiner",
    "\ufeff": "byte-order mark",
    "‑": "non-breaking hyphen", " ": "no-break space", "ﬁ": "fi ligature", "ﬂ": "fl ligature",
    "​": "zero-width space", "‐": "unicode hyphen", "−": "minus sign", "­": "soft hyphen",
    "→": "arrow", "●": "black circle bullet", "•": "bullet char in text",
}


def _pdf_lines(pdf_path: Path) -> list[dict]:
    out = subprocess.run(["pdftotext", "-bbox-layout", str(pdf_path), "-"], capture_output=True, text=True).stdout
    lines = []
    for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', out, re.S):
        words = re.findall(r"<word[^>]*>(.*?)</word>", m.group(5))
        text = html.unescape(" ".join(words))
        lines.append({"x0": float(m.group(1)), "x1": float(m.group(3)), "y": float(m.group(2)), "text": text})
    return lines


def _norm_txt(s: str) -> str:
    return re.sub(r"\s+", "", s.replace("**", ""))


def short_last_lines(pdf_path: Path, resume: dict, min_ratio: float = 0.12) -> list[str]:
    """Bullets with a stranded word or two on their last line, or that run to three lines. A last line that merely runs
    short is fine and wanted: bullets that all fill both lines read as one block. Returns fix suggestions."""
    lines = _pdf_lines(pdf_path)
    if not lines:
        return []
    full_w = max(l["x1"] - l["x0"] for l in lines)
    issues = []
    i = 0
    bullets = [b for coll in (resume.get("experience", []), resume.get("projects", [])) for it in coll for b in it["bullets"]]
    for b in bullets:
        target = _norm_txt(b)
        # find the line where this bullet starts
        start = next((k for k in range(i, len(lines)) if target.startswith(_norm_txt(lines[k]["text"])[:25]) and _norm_txt(lines[k]["text"])), None)
        if start is None:
            continue
        acc, k = "", start
        while k < len(lines) and len(acc) < len(target):
            acc += _norm_txt(lines[k]["text"])
            k += 1
        used = lines[start:k]
        i = k
        if len(used) >= 2:
            last = used[-1]
            ratio = (last["x1"] - last["x0"]) / full_w
            if ratio < min_ratio or len(last["text"].split()) <= 2:
                issues.append(f"stranded word on the last line: reword to lose ~{len(last['text']) + 2} characters (don't pad "
                              f"to fill the line) -> '{b[:70]}...'")
        if len(used) >= 3:
            issues.append(f"runs to {len(used)} lines; two is the limit: cut its least important part -> '{b[:70]}...'")
    return issues


def lint_pdf(pdf_path: Path, resume: dict) -> list[str]:
    """Check the text an ATS would extract: odd characters, contact details, reading order."""
    problems = []
    text = subprocess.run(["pdftotext", "-raw", str(pdf_path), "-"], capture_output=True, text=True).stdout
    for ch, name in BAD_CHARS.items():
        if ch in text:
            problems.append(f"extracted text contains {name} (U+{ord(ch):04X})")
    flat = re.sub(r"\s+", " ", text)
    for c in resume["header"]["contact"]:
        plain = re.sub(r"\*\*", "", c)
        if plain not in flat:
            problems.append(f"contact item not found verbatim in extracted text: {plain!r}")
    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", flat):
        problems.append("no email address found in extracted text")
    heads = [h for h in ("EXPERIENCE", "EDUCATION", "SKILLS") if h.lower() in [s for s in resume["section_order"]]]
    pos = [flat.upper().find(h) for h in heads]
    if any(p < 0 for p in pos):
        problems.append(f"section heading missing from extracted text: {heads}")
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if resume["header"]["name"].lower() not in first_line.lower():
        problems.append(f"name is not the first extracted line (got {first_line!r})")
    # Text fidelity: every bullet, title and skills line must extract word-for-word (catches dropped spaces
    # like "forAction" / "onAWS" that break ATS keyword search).
    flat_cmp = re.sub(r"\s+", " ", text).replace("- ", "-")
    expected = []
    for coll in (resume.get("experience", []), resume.get("projects", [])):
        for item in coll:
            expected += [item.get("title", ""), item.get("link", "")] + list(item["bullets"])
    expected += [f"{k}: {v}" for k, v in (resume.get("skills") or {}).items()]
    for e in expected:
        plain = re.sub(r"\s+", " ", e.replace("**", "")).strip()
        if plain and plain not in flat_cmp:
            words = plain.split(" ")
            bad = next((w for i, w in enumerate(words) if " ".join(words[: i + 1]) not in flat_cmp), words[0])
            problems.append(f"text does not extract verbatim near '{bad}': {plain[:70]}...")
    lines = _pdf_lines(pdf_path)
    names = {"EXPERIENCE", "EDUCATION", "PROJECTS", "SKILLS", str(resume.get("projects_heading") or "").upper()}
    first_head = next((l for l in lines if l["text"].strip().upper() in names), None)
    if first_head and len({round(l["y"]) for l in lines if l["y"] < first_head["y"] - 1}) > 2:
        problems.append("the contact line wraps onto a second row; drop an item so it fits on one")
    # Skills stay on one line each: a wrapped skills line is a list that has grown past what anyone reads.
    skill_rows = list((resume.get("skills") or {}).items())
    head = next((l for l in lines if l["text"].strip().upper() == "SKILLS"), None)
    if head and skill_rows and resume["section_order"][-1] == "skills":
        rows = len({round(l["y"]) for l in lines if l["y"] > head["y"] + 1})
        if rows > len(skill_rows):
            problems.append(f"a skills line wraps onto a second line; cut it to one line each ({len(skill_rows)} rows take {rows} lines)")
    long_bullets = []
    for coll in (resume.get("experience", []), resume.get("projects", [])):
        for item in coll:
            for b in item["bullets"]:
                if len(b) > 230:
                    long_bullets.append(b[:60] + "...")
    if long_bullets:
        problems.append(f"{len(long_bullets)} bullet(s) likely run past two lines: {long_bullets[:3]}")
    return problems


# ----------------------------------------------------------------------------- style (advisory)
WEAK_OPENERS = re.compile(r"^(?:helped|assisted|worked on|working on|responsible for|participated|involved in|tasked with|"
                          r"utilized|leveraged|spearheaded|duties included|in charge of)\b", re.I)
DEFAULT_BANNED = ["various", "etc.", "team player", "results-driven", "passionate", "synergy", "cutting-edge",
                  "state-of-the-art", "best-in-class", "world-class", "seamless", "robust solutions", "dynamic"]
PURPOSE = re.compile(r"\d|\benabl|\bso\b|\breplac|\binstead of\b|\bused\b|\badopted\b|\blet(?:s|ting)?\b|\ballow|\bhelp|"
                     r"\bfor (?:\w+ ){0,3}(?:users|teams|customers|operators|engineers|sellers|clients|students|patients)\b|"
                     r"\bto (?:help|let|catch|cut|reduce|speed|stop|prevent|keep|make|give|find|track|show|standardize)\b|"
                     r"\bwhich\b|\bwon\b|\bshipped\b|\bcutting\b|\breducing\b|\bsaving\b|\bfixing\b|\bpreventing\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:I|me|my|we|our)\b")
QUOTED = re.compile(r"""(?<!\w)['"‘“].*?['"’”](?!\w)""")
MIN_BULLET_CHARS = 150    # under this a bullet is a one-liner: one line for what, one for why needs about two
MIN_TERMS_PER_BULLET = 2  # a strong page shows about three distinct technical terms per bullet; a plain one about one
FULL_BULLET_CHARS = 205   # about two full lines. Past 60% of the page at this length, it reads as one block


def lint_style(r: dict, rules: dict | None = None) -> list[str]:
    """Advisory checks from docs/RESUME_PLAYBOOK.md. They never block a build: a person decides.

    A minor entry (a single bullet on anything but the first job) may stay a plain one-liner, and a colon-led list of
    what was set up is an accepted pattern for the production-ownership bullet.
    `rules` comes from resume.yaml `writing:` keys `banned_phrases`, `jargon` (private names an outsider can't read; public
    technical terms are fine) and `max_keyword_repeats` (default 3)."""
    rules = rules or {}
    banned = [b.lower() for b in DEFAULT_BANNED + list(rules.get("banned_phrases") or [])]
    jargon = list(rules.get("jargon") or [])
    out = []
    items = [it for coll in (r.get("experience", []), r.get("projects", [])) for it in coll]
    first = items[0] if items else None
    bullets = [(it.get("title") or it.get("org") or "", b, len(it["bullets"]) == 1 and it is not first)
               for it in items for b in it["bullets"]]
    for where, b, minor in bullets:
        plain = b.replace("**", "")
        short = f"{where}: '{plain[:60]}...'"
        if WEAK_OPENERS.search(plain):
            out.append(f"weak opener (say what you built or changed): {short}")
        if b.count("**") > 4:
            out.append(f"too much bold; bold the one or two things a skimmer should catch: {short}")
        if not minor and not PURPOSE.search(plain) and ":" not in plain:
            out.append(f"no number and no stated purpose: can a reader say what it was for? {short}")
        if not minor and len(plain) < MIN_BULLET_CHARS:
            out.append(f"thin ({len(plain)} chars): a main bullet needs about two lines, what and why. {short}")
        if FIRST_PERSON.search(QUOTED.sub(" ", plain)):
            out.append(f"first person (drop I/my/we): {short}")
        low = plain.lower()
        for phrase in banned:
            if phrase in low:
                out.append(f"phrase on your banned list '{phrase}': {short}")
        for term in jargon:
            if re.search(rf"\b{re.escape(term)}\b", plain):
                out.append(f"private name '{term}' an outsider can't read; say what it does: {short}")
    texts = [b.replace("**", "") for _, b, _ in bullets]
    for rx, shape in ((r",\s+so\b", "', so ...'"), (r"\binstead of\b", "'instead of'")):
        n = sum(1 for t in texts if re.search(rx, t))
        if n >= 3:
            out.append(f"{n} bullets lean on {shape}: the same sentence shape over and over reads as generated. Vary them")
    full = sum(1 for t in texts if len(t) >= FULL_BULLET_CHARS)
    if len(texts) >= 8 and full / len(texts) > 0.6:
        out.append(f"{full} of {len(texts)} bullets fill both lines, so the page reads as one block. Shorten a few where a clause adds the least")
    text = " ".join(texts)
    tech = technical_terms(text + " " + " ".join(str(it.get("org") or "") for it in items))
    if bullets and len(tech) / len(bullets) < MIN_TERMS_PER_BULLET:
        out.append(f"the page reads plain: {len(tech)} distinct technical terms across {len(bullets)} bullets. A strong page shows "
                   "about three per bullet: name the systems, failures and methods an engineer would respect")
    skills = ", ".join((r.get("skills") or {}).values())
    terms = {t.strip() for t in re.split(r",|;", skills) if len(t.strip()) > 2}
    limit = int(rules.get("max_keyword_repeats", 3))
    for t in sorted(terms):
        n = len(re.findall(rf"(?<![\w+#]){re.escape(t)}(?![\w+#])", text))
        if n > limit:
            out.append(f"'{t}' appears in {n} bullets; past {limit} swap the extras for the broader word postings use (service, API, backend)")
    return out


def pdf_name(data: dict) -> str:
    """'Jordan_Lee_Resume.pdf': a recruiter's download folder holds hundreds of files named resume.pdf."""
    name = re.sub(r"[^A-Za-z0-9]+", "_", ((data.get("header") or {}).get("name") or "Resume").strip()).strip("_")
    return f"{name}_Resume.pdf" if name and name != "Resume" else "Resume.pdf"


# ----------------------------------------------------------------------------- build
def emphasize_skills(r: dict, terms: list[str]) -> None:
    """Light, safe per-job edit: move skills the posting asks for to the front of each skills line.
    Never adds a skill; only reorders what the resume already claims (research: make minimum
    qualifications visible, but don't regenerate content per job)."""
    if not terms or not r.get("skills"):
        return
    def words(s: str) -> list[str]:
        return re.findall(r"[a-z0-9+#]+", s.lower())

    wanted = [words(t) for t in terms if words(t)]

    def asked_for(skill: str) -> bool:
        # Whole names only: "C" must not match "TypeScript", and "C" is not "C++".
        have = words(skill)
        return any(w == have or (len(w) == 1 and len(w[0]) > 1 and w[0] in have) for w in wanted)

    out = {}
    for k, v in r["skills"].items():
        items = [x.strip() for x in v.split(",")]
        items.sort(key=lambda x: 0 if asked_for(x) else 1)
        out[k] = ", ".join(items)
    r["skills"] = out


def build(yaml_path: Path, out_pdf: Path, variant: str | None = None, target_gap_pt: float | None = None,
          emphasize: list[str] | None = None, wording: str | None = None) -> dict:
    r = load_resume(yaml_path, variant, wording)
    emphasize_skills(r, emphasize or [])
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="jh-resume-"))
    html_path, pdf_tmp = work / "resume.html", work / "resume.pdf"

    def try_t(t: float, stretch: float = 0.0) -> dict:
        html_path.write_text(render_html(r, t, stretch))
        chrome_pdf(html_path, pdf_tmp)
        m = measure(pdf_tmp)
        m["t"] = round(t, 3)
        return m

    def clear_outputs() -> list[str]:
        """Remove every earlier output. An older PDF that no longer matches the source could be sent by mistake."""
        gone = [p for p in (out_pdf, out_pdf.with_suffix(".html")) if p.exists()]
        for p in gone + [out_pdf.with_suffix(x) for x in (".overflow.pdf", ".underfull.pdf")]:
            p.unlink(missing_ok=True)
        return [str(p) for p in gone]

    lo_m = try_t(0.0)
    lo_p = lerp(0.0)
    # How much more fits at the most compact layout, so wordings can be proposed without a test build.
    room_lines = max(0, int((lo_m["bottom_gap_pt"] - lo_p["margin_tb"] * 72) / (lo_p["font"] * lo_p["lh"])))
    if lo_m["pages"] > 1:
        removed = clear_outputs()
        shutil.copy(pdf_tmp, out_pdf.with_suffix(".overflow.pdf"))
        shutil.rmtree(work, ignore_errors=True)
        return {"status": "overflow", "pages": lo_m["pages"], "measure": lo_m,
                "detail": f"Content needs {lo_m['pages']} pages even at the most compact layout. Cut a bullet or project "
                          f"(a minor entry down to one line first, then the weakest project bullet). The over-long render is at "
                          f"{out_pdf.with_suffix('.overflow.pdf')}" + (f"; the outdated PDF was removed: {removed}" if removed else "."),
                "lint": [], "short_last_lines": [], "style": []}
    hi_m = try_t(1.0)
    best_t, best_m = (1.0, hi_m) if hi_m["pages"] == 1 else (0.0, lo_m)
    if hi_m["pages"] > 1:
        lo, hi = 0.0, 1.0
        for _ in range(6):
            mid = (lo + hi) / 2
            m = try_t(mid)
            if m["pages"] == 1:
                lo, best_t, best_m = mid, mid, m
            else:
                hi = mid
    # Line breaks move in whole lines, so the best size can still stop up to a line short of the margin. Spread what is
    # left through the gaps between bullets, entries and sections, so it never sits as a band at the bottom.
    margin_bottom_pt = lerp(best_t)["margin_tb"] * 72
    fits = lambda m: m["pages"] == 1 and m["bottom_gap_pt"] >= margin_bottom_pt  # noqa: E731
    best_s = 0.0
    if try_t(best_t)["bottom_gap_pt"] - margin_bottom_pt > 1:
        if fits(try_t(best_t, MAX_STRETCH_PT)):
            best_s = MAX_STRETCH_PT
        else:
            lo_s, hi_s = 0.0, MAX_STRETCH_PT
            for _ in range(4):
                mid = (lo_s + hi_s) / 2
                if fits(try_t(best_t, mid)):
                    lo_s, best_s = mid, mid
                else:
                    hi_s = mid
    final = try_t(best_t, best_s)
    used = lerp(best_t, best_s)
    usable_gap = round(final["bottom_gap_pt"] - margin_bottom_pt, 1)
    line_pt = used["font"] * used["lh"]
    bullets = [b.replace("**", "") for coll in (r.get("experience", []), r.get("projects", [])) for it in coll for b in it["bullets"]]
    lines_short = max(1, round(usable_gap / line_pt)) if usable_gap > FILL_TOLERANCE_PT else 0
    status, note = "ok", ""
    if final["pages"] != 1:
        status, note = "error", "final render is not one page"
    elif lines_short:
        thin = sum(1 for b in bullets if len(b) < MIN_BULLET_CHARS)
        status = "underfull"
        note = (f"The page ends about {lines_short} line{'s' if lines_short != 1 else ''} short of the bottom margin, leaving "
                f"blank space. A finished page is full. Add real content from the inventory: "
                + (f"bring the {thin} thin bullet{'s' if thin != 1 else ''} up to two full lines (what you did, then why), then " if thin else "")
                + "add the next-strongest bullet or entry. If the inventory has nothing left, interview for more. Never pad.")
    clear_outputs()
    target = out_pdf if status == "ok" else out_pdf.with_suffix(f".{status}.pdf")
    shutil.copy(pdf_tmp, target)
    html_out = out_pdf.with_suffix(".html")
    html_out.write_text(render_html(r, best_t, best_s))
    problems = lint_pdf(target, r)
    widows = short_last_lines(target, r)
    style = lint_style(r, (yaml.safe_load(yaml_path.read_text()) or {}).get("writing") or {})
    report = {"status": status, "note": note, "variant": r["variant"], "density_t": round(best_t, 3), "measure": final,
              "empty_space_above_bottom_margin_pt": usable_gap,
              "fill": {"font_pt": round(used["font"], 2), "bullets": len(bullets),
                       "avg_bullet_chars": round(sum(map(len, bullets)) / max(len(bullets), 1)),
                       "technical_terms": len(technical_terms(" ".join(bullets))),
                       "lines_on_page": len(_pdf_lines(target)), "lines_short": lines_short, "lines_of_room": room_lines},
              "lint": problems, "short_last_lines": widows, "style": style, "pdf": str(target), "html": str(html_out)}
    shutil.rmtree(work, ignore_errors=True)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml", type=Path)
    ap.add_argument("--variant")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--emphasize", help="comma-separated skills from the posting to move first in the skills lines (reorder only)")
    ap.add_argument("--wording", help="use the named alternative text for bullets that define one under `alt:` in the YAML")
    a = ap.parse_args(argv)
    rep = build(a.yaml, a.out, a.variant, emphasize=[x for x in (a.emphasize or "").split(",") if x.strip()], wording=a.wording)
    print(json.dumps(rep, indent=1))
    return 0 if rep["status"] == "ok" and not rep.get("lint") and not rep.get("short_last_lines") else 1


if __name__ == "__main__":
    sys.exit(main())
