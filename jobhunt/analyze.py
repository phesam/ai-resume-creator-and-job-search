"""Deterministic signal extraction from a normalized job record.

Everything here is a *signal* with evidence (snippets), not a verdict. Triage uses these
signals with conservative rules; Claude reviews the evidence for anything borderline.
"""

from __future__ import annotations

import re
from collections import Counter

from .common import days_since

# ----------------------------------------------------------------------------- text sections
_REQ_HDR = re.compile(
    r"^\s*(?:•\s*)?(?:required|minimum|basic|must[- ]have|what you(?:'|’)ll need|what we(?:'|’)re looking for|"
    r"what you bring|who you are|you have|you(?:'|’)ll have|qualifications|requirements|about you|"
    r"your background|skills (?:and|&) experience|experience (?:and|&) skills|key qualifications|"
    r"we(?:'|’)re looking for|what you(?:'|’)ll bring|ideal candidate)\b[^\n]{0,60}$",
    re.I | re.M,
)
_PREF_HDR = re.compile(
    r"^\s*(?:•\s*)?(?:preferred|desired|nice[- ]to[- ]have|bonus|pluses|plus if|additional|"
    r"it(?:'|’)s a plus|extra credit|good to have|would be great|ideally|preferred qualifications|"
    r"we(?:'|’)d love|bonus points)\b[^\n]{0,60}$",
    re.I | re.M,
)
_END_HDR = re.compile(
    r"^\s*(?:•\s*)?(?:benefits|compensation|salary|pay range|us salary range|what we offer|perks|"
    r"equal opportunity|eeo|about (?:us|the company)|why join|our values|life at|the pay|"
    r"total rewards|location|working at)\b[^\n]{0,60}$",
    re.I | re.M,
)


_PREF_IN_HDR = re.compile(r"\bprefer|\bdesired?\b|nice[- ]to[- ]have|\bbonus\b|\ba plus\b", re.I)


def split_sections(text: str) -> dict:
    """Best-effort split into body / required / preferred / tail by header lines."""
    marks = []
    for kind, rx in (("required", _REQ_HDR), ("preferred", _PREF_HDR), ("tail", _END_HDR)):
        for m in rx.finditer(text):
            # "Qualifications We Prefer" (RTX) starts like a requirements header but introduces the preferred list.
            k = "preferred" if kind == "required" and _PREF_IN_HDR.search(m.group(0)) else kind
            marks.append((m.start(), k))
    marks.sort()
    out = {"body": "", "required": "", "preferred": "", "tail": ""}
    if not marks:
        out["body"] = text
        return out
    out["body"] = text[: marks[0][0]]
    for i, (pos, kind) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out[kind] += text[pos:end] + "\n"
    return out


_ABBREV = re.compile(
    r"\b(U\.S|U\.K|e\.g|i\.e|etc|Inc|Corp|Co|Ltd|Sr|Jr|St|No|vs|approx|incl|Dept|Mr|Ms|Mrs|Dr|Ph\.D|B\.S|M\.S|"
    r"B\.A|M\.A|B\.Sc|M\.Sc|a\.m|p\.m|U\.S\.A)\.",
    re.I,
)


def sentences(text: str) -> list[str]:
    protected = _ABBREV.sub(lambda m: m.group(1).replace(".", "<D>") + "<D>", text)
    parts = re.split(r"(?<=[.!?;])\s+|\n+", protected)
    out = []
    for p in parts:
        p = p.replace("<D>", ".").strip(" •-\t")
        if p:
            out.append(p)
    return out


# ----------------------------------------------------------------------------- years of experience
_NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
}
_NUM = r"(\d{1,2}(?:\.\d)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)"
_YOE_RX = re.compile(
    rf"(?:(?:minimum|at least|min\.?|over|more than)\s+(?:of\s+)?)?{_NUM}\s*(?:\(\d+\)\s*)?(?:or\s+(?:more|greater)\s+)?"  # "3 or more years" (Anduril GNC)
    rf"(?:\+|plus)?\s*(?:(?:-|–|—|to)\s*{_NUM}\s*(?:\+)?\s*)?(?:\+\s*)?(?:of\s+)?(?:years?|yrs?)\b",  # "7+ of years" (sic)
    re.I,
)
_EXP_CONTEXT = re.compile(r"experience|exp\b|industry|professional|working|\bwork\b|background|track record|building|developing|"
                          r"designing|writing|programming|shipping|leading|using|hands-on|coding|engineering|in (?:a|an|the)\b", re.I)
_NOT_EXP = re.compile(r"years? (?:old|of age)|anniversary|warranty|years? ago|founded|history|for over \d+ years|\bage\b"
                      r"|background investigation|reinvestigation|continuous evaluation", re.I)  # clearance recency, not experience
_MONTHS_RX = re.compile(r"(\d{1,2})\s*months?\s*(?:-|–|to)\s*(\d{1,2})\s*years?", re.I)
# "Bachelor's degree; OR 2+ years of professional experience in lieu of a degree": the years replace the degree.
_DEGREE_ALT = re.compile(r"\b(?:in lieu of|in place of|instead of)\s+(?:(?:a|an|the)\s+)?(?:[\w'’]+\s+){0,3}?degree", re.I)
# Degree tiers, for bullets such as "Bachelor's with 5 years – OR – Master's with 3 years – OR – PhD with 1 year".
_TIER_RX = re.compile(
    r"(?P<phd>\bph\.?\s?d(?!\w)|\bdoctora(?:l|te)\b)"
    r"|(?P<master>\bmaster(?:'|’)s\b|\bmasters\b|\bmaster\s+(?:of\s+\w+\s+)?degree\b|(?-i:\bM\.?S\.?c?(?!\w))|\bMBA\b"
    r"|\badvanced\s+degree\b|\bgraduate\s+degree\b)"
    r"|(?P<bachelor>\bbachelor(?:'|’)?s?\b|(?-i:\bB\.?S\.?c?(?!\w))|(?-i:\bB\.A\.?(?!\w))|\bundergraduate\s+degree\b)"
    r"|(?P<associate>\bassociate(?:'|’)?s?\s+degree\b)"
    r"|(?P<high_school>\bhigh\s+school\b|\bGED\b)",
    re.I,
)
# What may sit between two degree words that share one years figure: "BS/MS", "Bachelor's or Master's", "B.S., M.S. or".
_DEGREE_LIST_GAP = re.compile(r"^(?:(?!(?-i:OR))[^;:.–—\d]){0,22}$")
# What separates one alternative from the next inside such a bullet ("; OR", "– OR –", ", or Master's ...").
_ALT_SEP = re.compile(
    r";\s*or\b|[–—-]\s*or\s*[–—-]|(?-i:\bOR\b)"
    r"|,?\s*\bor\s+(?=(?:an?\s+)?(?:\d{1,2}\s*\+?\s*(?:years?|yrs?)|master|bachelor|ph\.?\s?d|associate|high\s+school|advanced\s+degree))",
    re.I,
)


def _num(tok: str | None) -> float | None:
    if tok is None:
        return None
    tok = tok.lower()
    if tok in _NUM_WORDS:
        return float(_NUM_WORDS[tok])
    try:
        return float(tok)
    except ValueError:
        return None


def _alt_before(line: str, start: int, s0: int, e0: int) -> bool:
    """True when an alternative separator ("; OR", ", or 3+ years ...") sits between `start` and the years figure at
    s0:e0. The search runs through the figure because ", or" only counts when years or a degree word follow it."""
    m = _ALT_SEP.search(line, start, e0)
    return bool(m and m.start() < s0)


def _degree_line(line: str, in_body: bool) -> dict | None:
    """Read one bullet that ties years of experience to degree tiers, for someone who holds a bachelor's degree.

    Returns None when the bullet has no such structure (the caller then reads it as ordinary sentences). Otherwise
    {kind, low, high}: kind "bachelor" = years asked alongside a bachelor's; "free" = a bachelor's alone is enough
    (the years belong to another route, e.g. "in lieu of a degree"); "lower" = only routes below a bachelor's are
    listed; "higher" = only master's/PhD routes are listed.
    """
    tiers = [(m.start(), m.end(), m.lastgroup) for m in _TIER_RX.finditer(line)]
    if not tiers:
        return None
    valid = []
    for m in _YOE_RX.finditer(line):
        low, high = _num(m.group(1)), _num(m.group(2))
        if low is None or low > 25:
            continue
        window = line[max(0, m.start() - 90): m.end() + 90]
        if _NOT_EXP.search(window) or (in_body and not _EXP_CONTEXT.search(window)):
            continue
        valid.append((m.start(), m.end(), low, high))
    if not valid:
        return None
    by: dict[str, list] = {}
    taken = None  # a degree word already claimed by the previous years figure ("5 years with Bachelors; 3 years with ...")
    for i, (s0, e0, low, high) in enumerate(valid):
        prev_end = valid[i - 1][1] if i else 0
        next_start = valid[i + 1][0] if i + 1 < len(valid) else len(line)
        tier = None
        if _DEGREE_ALT.search(line[e0: min(next_start, e0 + 140)]):
            tier = "none"
        if tier is None:
            before = [t for t in tiers if prev_end <= t[0] and t[1] <= s0 and t is not taken]
            gap = line[before[-1][1]: s0] if before else ""
            if before and ";" not in gap and not _alt_before(line, before[-1][1], s0, e0):
                # "BS/MS", "Bachelor's or Master's degree with 3+ years": a list of degrees shares the figure
                names = [before[-1][2]]
                for a, b in zip(reversed(before[:-1]), reversed(before[1:])):
                    if not _DEGREE_LIST_GAP.match(line[a[1]: b[0]]):
                        break
                    names.append(a[2])
                tier = "bachelor" if "bachelor" in names else before[-1][2]
        taken = None
        if tier is None:
            after = [t for t in tiers if e0 <= t[0] < min(next_start, e0 + 70)]
            if after and not _ALT_SEP.search(line[e0: after[0][0]]):
                tier, taken = after[0][2], after[0]
        if tier is None:
            # Tied to no degree. "Bachelor's degree; OR 4+ years of ..." is a separate route for people without the
            # degree; "5+ years of industry experience (Bachelor's, Master's, or PhD)" applies to everyone.
            earlier = [t for t in tiers if t[1] <= s0]
            tier = "alt" if earlier and _alt_before(line, earlier[-1][1], s0, e0) else "general"
        by.setdefault(tier, []).append((low, high))
    has_bachelor = any(t[2] == "bachelor" for t in tiers)
    bach, general = by.get("bachelor", []), by.get("general", [])
    if bach or (has_bachelor and general):
        picks = [min(x, key=lambda v: v[0]) for x in (bach, general) if x]
        low, high = max(picks, key=lambda v: v[0])
        return {"kind": "bachelor", "low": low, "high": high}
    if has_bachelor:
        return {"kind": "free", "low": None, "high": None}
    lower = by.get("associate", []) + by.get("high_school", []) + by.get("none", []) + by.get("alt", [])
    if lower:
        low, high = min(lower, key=lambda x: x[0])
        return {"kind": "lower", "low": low, "high": high}
    higher = by.get("master", []) + by.get("phd", [])
    if higher:
        low, high = min(higher, key=lambda x: x[0])
        return {"kind": "higher", "low": low, "high": high}
    return None  # years not tied to any degree tier: an ordinary requirement


def extract_yoe(text: str) -> dict:
    """Find 'N+ years of experience' style requirements, read for someone who holds a bachelor's degree.

    Returns {required_min, preferred_min, degree_alt_min, mentions:[{low, high, section, snippet}]}.
    A bullet that ties years to degree tiers ("Bachelor's with 5 years – OR – Master's with 3 years") counts the
    bachelor's number; when several bullets state a bachelor's number (a "Level 2 or 3" posting) the lowest counts.
    Years offered "in lieu of a degree" are an alternative to the degree, not a requirement on top of it, so they
    are reported separately as degree_alt_min and never count toward required_min.
    Across other sentences in the required section, the maximum is binding.
    """
    secs = split_sections(text)
    mentions = []
    degree_alt: list[float] = []
    per_section_sentence_mins: dict[str, list[float]] = {"required": [], "preferred": [], "body": []}
    for sec_name in ("required", "preferred", "body"):
        plain, deg = [], {"bachelor": [], "lower": [], "higher": [], "free": False}
        for line in secs.get(sec_name, "").split("\n"):
            d = _degree_line(line, sec_name == "body") if len(line) <= 700 else None
            if not d:
                plain.append(line)
            elif d["kind"] == "free":
                deg["free"] = True
            else:
                deg[d["kind"]].append(d["low"])
                if d["kind"] != "higher":
                    mentions.append({"low": d["low"], "high": d["high"], "section": sec_name,
                                     "snippet": line.strip(" •-\t")[:220]})
        for s in sentences("\n".join(plain)):
            if len(s) > 600:
                s = s[:600]
            lows = []
            m2 = _MONTHS_RX.search(s)
            if m2 and _EXP_CONTEXT.search(s):
                lows.append(0.0)
                mentions.append({"low": 0.0, "high": float(m2.group(2)), "section": sec_name, "snippet": s[:220]})
            found = list(_YOE_RX.finditer(s))
            for i, m in enumerate(found):
                low, high = _num(m.group(1)), _num(m.group(2))
                if low is None or low > 25:
                    continue
                tail = s[m.end(): found[i + 1].start() if i + 1 < len(found) else m.end() + 140]
                if _DEGREE_ALT.search(tail):
                    degree_alt.append(low)  # asked only of people without the degree; the candidate has one
                    continue
                window = s[max(0, m.start() - 90): m.end() + 90]
                if _NOT_EXP.search(window):
                    continue
                if sec_name == "body" and not _EXP_CONTEXT.search(window):
                    continue
                lows.append(low)
                mentions.append({"low": low, "high": high, "section": sec_name, "snippet": s[:220]})
            if lows:
                per_section_sentence_mins[sec_name].append(min(lows))
        if deg["bachelor"] or deg["lower"]:
            per_section_sentence_mins[sec_name].append(min(deg["bachelor"] + deg["lower"]))
        elif deg["higher"] and not deg["free"]:
            per_section_sentence_mins[sec_name].append(min(deg["higher"]))
    req = per_section_sentence_mins["required"] or per_section_sentence_mins["body"]
    pref = per_section_sentence_mins["preferred"]
    return {
        "required_min": max(req) if req else None,
        "required_source": "required" if per_section_sentence_mins["required"] else ("body" if req else None),
        "preferred_min": max(pref) if pref else None,
        "degree_alt_min": min(degree_alt) if degree_alt else None,
        "mentions": mentions[:8],
    }


# ----------------------------------------------------------------------------- clearance / citizenship
_CLR_SECURITY = re.compile(
    r"security clearance|secret|ts/sci|ts-sci|\bsci\b|clearance eligib|u\.s\. (?:government )?clearance|"
    r"government clearance|dod clearance|active clearance|clearance (?:is )?required|polygraph|public trust|"
    r"\bq clearance|\bl clearance|\bdoe clearance|clearable|clearance level",
    re.I,
)
_CLR_ELIG = re.compile(
    r"eligib|abilit\w* to (?:obtain|get|acquire|receive)|able to (?:obtain|get|acquire|receive)|obtain and maintain|"
    r"\bto obtain\b|willing(?:ness)? to (?:obtain|undergo|submit|apply)|capable of obtaining|obtainable|clearable|"
    r"may be required|sponsor|process of obtaining|to be obtained|upon (?:hire|start)|or (?:the )?ability",
    re.I,
)
_CLR_ACTIVE = re.compile(r"\b(currently|active|current|existing|in[- ]scope|possess\w*|hold\w*|must have an?)\b", re.I)
_CLR_PREF = re.compile(r"prefer|desired|a plus|nice to have|bonus|ideal|highly desirable", re.I)
_POLY = re.compile(r"polygraph|\bci poly\b|\bfs poly\b|full[- ]scope poly", re.I)
_CLR_LEVEL = re.compile(r"ts/sci|ts-sci|top secret|\bts\b|\bsecret\b|\bq\b clearance|\bl\b clearance|public trust", re.I)


_RTX_CLR_FIELD = re.compile(
    r"(?:security clearance status\s*:?\s*)?(?:active and existing security clearance required (?:on|after) day 1"
    r"|ability to obtain interim u\.s\. government issued security clearance is required prior to start date)"
    r"|security clearance status\s*:?\s*not required", re.I)


def extract_clearance(text: str) -> dict:
    secs = split_sections(text)
    status, evidence, level = "none_mentioned", [], None
    rank = {"none_mentioned": 0, "eligibility": 1, "active_preferred": 2, "active_required": 3}
    for sec_name in ("required", "body", "preferred"):
        for s in sentences(secs.get(sec_name, "")):
            if not _CLR_SECURITY.search(s) or re.search(r"clearance required (?:for|to) start", s, re.I) \
                    or re.match(r"^\s*clearance type\s*:", s, re.I) or _RTX_CLR_FIELD.search(s):
                continue  # structured fields are handled below
            if _CLR_ELIG.search(s) or (re.search(r"citizenship", s, re.I) and not _CLR_ACTIVE.search(s)):
                kind = "eligibility"
            elif _CLR_ACTIVE.search(s):
                kind = "active_preferred" if (sec_name == "preferred" or _CLR_PREF.search(s)) else "active_required"
            elif _CLR_PREF.search(s) or sec_name == "preferred":
                kind = "active_preferred"
            else:
                # e.g. bare "Secret security clearance" bullet under required qualifications
                kind = "active_required" if sec_name == "required" else "eligibility"
            if rank[kind] > rank[status]:
                status = kind
            lv = _CLR_LEVEL.search(s)
            if lv and (level is None or "top" in lv.group(0).lower() or "ts" in lv.group(0).lower()):
                level = lv.group(0)
            evidence.append(f"[{sec_name}/{kind}] {s[:200]}")
    # Structured field used by Northrop Grumman and others: "CLEARANCE REQUIRED FOR START: Yes/No".
    m = re.search(r"clearance required (?:for|to) start\W{0,3}\s*(yes|no)\b", text, re.I)
    if m:
        if m.group(1).lower() == "yes":
            status = "active_required"
        elif status == "active_required":
            status = "active_preferred"
        evidence.insert(0, f"[structured] {m.group(0)}")
    # Structured field used by RTX: "Security Clearance Status: Active and existing security clearance required on day 1"
    # means it must be held at the start; "... required after day 1", "Ability to obtain INTERIM ..." and "Not Required"
    # mean it is obtained after hiring.
    m = _RTX_CLR_FIELD.search(text)
    if m:
        if re.search(r"required on day 1", m.group(0), re.I):
            status = "active_required"
        else:
            if status == "active_required":
                status = "active_preferred"
            elif status == "none_mentioned" and not re.search(r"not required", m.group(0), re.I):
                status = "eligibility"
        evidence.insert(0, f"[structured] {m.group(0).strip()[:160]}")
    return {
        "status": status,
        "level": level,
        "polygraph": bool(_POLY.search(text)),
        "evidence": evidence[:5],
    }


_US_PERSON = re.compile(r"u\.?s\.? (?:person|citizen)|united states citizen|itar|export control|citizenship", re.I)


def extract_citizenship(text: str) -> bool:
    return bool(_US_PERSON.search(text))


# ----------------------------------------------------------------------------- degree
def extract_degree(text: str) -> dict:
    req = split_sections(text).get("required", "") or text
    phd_req = bool(re.search(r"ph\.?d\.?[^.\n]{0,40}(required|must)|(required|must)[^.\n]{0,40}ph\.?d", req, re.I))
    ms_req = bool(re.search(r"(master'?s|m\.s\.|ms degree)[^.\n]{0,30}(required|must)", req, re.I)) and not re.search(
        r"bachelor", req, re.I
    )
    ee_only = bool(re.search(r"degree in (electrical|mechanical|aerospace)[^.\n]{0,60}(?<!computer science)$", req, re.I | re.M))
    return {"phd_required": phd_req, "ms_required": ms_req, "non_cs_engineering_degree": ee_only}


# ----------------------------------------------------------------------------- salary
_SAL_RX = re.compile(r"\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])\s*(?:-|–|—|to|and)\s*\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])")


def _money(tok: str) -> float:
    tok = tok.replace(",", "").replace(" ", "")
    return float(tok[:-1]) * 1000 if tok[-1] in "kK" else float(tok)


def extract_salary(text: str, salary_text: str | None) -> dict:
    for src in (salary_text or "", text):
        m = _SAL_RX.search(src)
        if m:
            lo, hi = _money(m.group(1)), _money(m.group(2))
            if 20_000 <= lo <= 2_000_000 and lo <= hi:
                return {"min": lo, "max": hi, "text": m.group(0)}
    return {"min": None, "max": None, "text": salary_text}


# ----------------------------------------------------------------------------- title: level + family
_LVL_WORDS = [
    (r"\b(intern|internship|co-?op)\b", "intern"),
    (r"\b(chief|vp|vice president|head of|director|manager|mgr)\b", "manager"),
    (r"\b(principal|staff|distinguished|fellow)\b", "staff+"),
    (r"\b(lead|tech lead)\b", "lead"),
    (r"\b(senior|sr\.?)\b", "senior"),
    (r"\b(new grad|new graduate|graduate|early career|entry[- ]level|university grad|college grad|junior|jr\.?|"
     r"associate|apprentice|residency|rotational)\b", "entry"),
    (r"\bmid[- ]?level\b|\bmid[- ]?career\b", "mid"),
    (r"\ball levels\b|\bany level\b", "any"),
]
_LVL_TOKENS = {"i": "entry", "1": "entry", "ii": "mid", "2": "mid", "iii": "senior", "3": "senior",
               "iv": "senior+", "4": "senior+", "v": "senior+", "5": "senior+"}


def title_level(title: str) -> str:
    t = title.lower()
    for rx, lvl in _LVL_WORDS:
        if re.search(rx, t, re.I):
            return lvl
    # "Software Engineer II", "Engineer 2/3", "Level 3", "SWE III - Payments"
    for m in re.finditer(r"(?:level\s*|\b)(i{1,3}|iv|v|[1-5])(?:\s*/\s*(i{1,3}|iv|v|[1-5]))?\b(?![&\w.-])", t):
        prev = t[max(0, m.start() - 1): m.start()]
        if prev in ("&", "-", "/", ".") and not t[max(0, m.start() - 6): m.start()].endswith("level "):
            continue
        tok = m.group(1)
        if tok in _LVL_TOKENS:
            return _LVL_TOKENS[tok]
    return "unspecified"


CORE_RX = re.compile(
    r"software|developer|full[- ]?stack|front[- ]?end|back[- ]?end|\bweb\b|mobile|\bios\b|android|"
    r"platform engineer|infrastructure|site reliability|\bsre\b|devops|dev ops|devsecops|cloud|data engineer|"
    r"machine learning|\bml\b|\bmlops\b|\bai\b|artificial intelligence|deep learning|computer vision|machine vision|perception|"
    r"autonomy|robotics|simulation|forward[- ]deployed|\bfde\b|solutions? engineer|integration engineer|tools? engineer|"
    r"test automation|automation engineer|\bsdet\b|qa engineer|quality assurance engineer|security engineer|"
    r"appsec|application security|product engineer|systems software|embedded|firmware|flight software|"
    r"ground software|mission software|gameplay|game engineer|graphics|rendering|engine programmer|programmer|"
    r"research engineer|applied scientist|data scientist|analytics engineer|database|distributed systems|"
    r"release engineer|build engineer|developer experience|developer productivity|developer advocate|devrel|"
    r"technical support engineer|support engineer|customer engineer|deployment engineer|field software|"
    r"software test|verification engineer|c2\b|command and control|lattice|\bapi\b|backend|frontend|"
    r"data platform|\betl\b|big data|llm|genai|generative ai|agent|applications engineer|application engineer|"
    r"member of technical staff|\bmts\b|technical staff|\bswe\b|computer scientist|cyber|reverse engineer|"
    r"vulnerability|exploit|network engineer|systems engineer, software|software systems",
    re.I,
)
ADJACENT_RX = re.compile(
    r"systems engineer|test engineer|field engineer|mission engineer|technical program manager|\btpm\b|"
    r"product manager|solutions architect|sales engineer|customer success engineer|\bit\b engineer|"
    r"information security|data analyst|business systems|salesforce|\berp\b|operations engineer|"
    r"technical operations|implementation engineer|technical account|systems integration|integration and test|"
    r"\bi&t\b|technical writer|analyst, (?:data|engineering)|modeling|algorithm",
    re.I,
)
NONMATCH_RX = re.compile(
    r"mechanical|electrical engineer|hardware engineer|manufacturing engineer|manufacturing technician|technician|"
    r"machinist|assembler|assembly|welder|fabricat|supply chain|procurement|buyer|sourcing|logistics|warehouse|"
    r"material handler|shipping|receiving|inventory|finance|financial|accountant|accounting|\btax\b|treasury|payroll|"
    r"legal|counsel|attorney|paralegal|contracts? (?:manager|administrator|specialist)|recruit|talent|"
    r"people partner|\bhr\b|human resources|benefits|compensation analyst|marketing|communications|"
    r"\bsales\b|account executive|account manager|business development|capture manager|proposal|facilities|"
    r"security officer|security guard|program manager|project manager|program control|quality engineer|"
    r"quality inspector|inspector|production|operator|planner|scheduler|executive assistant|administrative|"
    r"office manager|receptionist|chef|cook|janitor|custodian|driver|pilot|propulsion|structures|aerodynamic|"
    r"thermal|\brf\b|antenna|optical|optics|materials|chemist|composite|tooling|industrial engineer|"
    r"process engineer|safety|environmental|ehs\b|nurse|medical|clinical|maintenance|electrician|"
    r"pcb|layout designer|drafter|cad designer|mechatronics|power electronics|battery|cell engineer|"
    r"motor|hydraulic|avionics technician|integrator|stocker|cashier|store|crew|barista|"
    r"workplace|event|coordinator|trade compliance|export compliance|security specialist|fso|"
    r"insider threat|policy|government relations|strategy|investor|corporate development|"
    r"design engineer|test technician|harness|cable|machine shop|cnc|metrology|calibration|"
    r"photographer|video|content|writer|editor|designer(?!.*(?:software|engineer))",
    re.I,
)


HARDWARE_RX = re.compile(
    r"electrical|electro-mechanical|electromechanical|mechanical|laser|propulsion|fuel|hvac|\bemc\b|\bemi\b|\brf\b|"
    r"structural|structures|actuat|thermal|optical|electro[- ]optical|camera test|hardware test|production hardware|"
    r"manufacturing test|npi engineer|liaison engineer|quality systems|quality specialist|manufacturing specialist|"
    r"integration and test technician|technician|flight test (?:&|and) integration specialist",
    re.I,
)
OPS_NONMATCH_RX = re.compile(
    r"mailroom|material|accounts payable|real estate|supervisor|planning|s&op|business operations|business & revenue|"
    r"operations associate|program operations|division operations|global operations|community engagement|"
    r"service desk|m&a|field service|field technical specialist|technical specialist|\bfsr\b|integration specialist|"
    r"threat intelligence|test site operations|enablement specialist|quality, |data analyst, quality|systems administrator",
    re.I,
)


HARD_NONMATCH_RX = re.compile(
    r"technician|machinist|plumber|porter\b|welder|welding|mechanic\b|millwright|fitter\b|toolmaker|tube bender|"
    r"food service|teacher|janitor|custodian|foreman|superintendent|merchandising|candidate specialist|recruit|"
    r"elevator|crane|heavy equipment|tool (?:&|and) die|catering|barista|housekeep|hotel operations|transportation\)|"
    r"build specialist|build associate|construction",
    re.I,
)
EXTRA_NONMATCH_RX = re.compile(
    r"\bgnc\b|guidance, navigation|dynamics engineer|loads|fluids? (?:engineer|systems)|mechanisms|turbomachinery|"
    r"power generation|power plant|water treatment|radiation effects|signal integrity|rfic|\beda\b|asic|\bdft\b|"
    r"device engineer|failure analysis|hardware development|hardware reliability|supplier development|\bnde\b|\bmep\b|"
    r"fire protection|industrial hygien|natural gas|chemical|\bsmt\b|launch engineer|recovery engineer|trajectory|"
    r"design criteria|electromagnetic|certification engineer|compliance|regulatory|account specialist|onboarding specialist|"
    r"spaceport|customer support|customer success specialist|immigration|logistician|civil engineer|controls? engineer|"
    r"controls specialist|automation (?:&|and) controls|data center (?:administrator|specialist)|network administrator|"
    r"it support|executive it|comsec|security analyst|physical security|test specialist|operations specialist|"
    r"operations analyst|business analyst|learning guide|lab architect|gateway fleet|ground network specialist|"
    r"aviation specialist|aviation development|product development engineer|process development|equipment engineer|"
    r"project engineer|starship engineer|new graduate engineer, (?!software)|mission assurance|supplier|\bcost\b|schedul|"
    r"estimat|subcontract|property|configuration (?:analyst|management)|program control|\bpricing\b|\bbudget|"
    r"(?<!data )(?<!software )(?<!security )\banalyst\b(?!.*\b(?:data|software)\b)",
    re.I,
)


def job_family(title: str, department: str | None) -> str:
    t = title or ""
    dept = (department or "").lower()
    if HARD_NONMATCH_RX.search(t) and not re.search(r"software|developer", t, re.I):
        return "nonmatch"
    # "Systems Engineer, C2 Integration" or "Flight Test Engineer" are engineering-adjacent even when the
    # title contains a software-ish token (C2, autonomy, AI); "Software Test Engineer" stays core.
    if re.search(r"\b(systems?|test|integration|mission|field|flight test|reliability)\s+engineer", t, re.I) and not re.search(
        r"software|developer|firmware|embedded|data engineer|ml engineer|machine learning|\bai\b engineer", t, re.I
    ):
        return "nonmatch" if HARDWARE_RX.search(t) else "adjacent"
    if CORE_RX.search(t):
        return "core"
    if HARDWARE_RX.search(t) or OPS_NONMATCH_RX.search(t):
        return "nonmatch"
    if dept in ("software", "engineering - software", "software engineering", "engineering"):
        return "core" if dept != "engineering" else "unknown"
    if EXTRA_NONMATCH_RX.search(t):
        return "nonmatch"
    if ADJACENT_RX.search(t):
        return "adjacent"
    if NONMATCH_RX.search(t):
        return "nonmatch"
    return "unknown"


# ----------------------------------------------------------------------------- location
# Your own regions (Southern California, the Bay Area, ...) come from profile.yaml; see jobhunt/config.py.
NON_US = re.compile(
    r"\b(australia|united kingdom|england|scotland|wales|ireland|london|japan|tokyo|korea|seoul|taiwan|taipei|"
    r"germany|munich|berlin|india|bangalore|bengaluru|hyderabad|canada|toronto|vancouver|montreal|ontario, canada|"
    r"quebec|singapore|israel|tel aviv|france|paris|netherlands|amsterdam|poland|spain|italy|sweden|norway|"
    r"denmark|finland|romania|ukraine|mexico|brazil|argentina|philippines|uae|united arab emirates|abu dhabi|dubai|saudi|riyadh|qatar|doha|bahrain|kuwait|oman|jordan|new zealand|"
    r"sydney|melbourne|canberra|adelaide|brisbane|perth|switzerland|zurich|austria|belgium|czech|estonia|"
    r"lithuania|latvia|portugal|lisbon|greece|turkey|china|beijing|shanghai|hong kong|vietnam|thailand|"
    r"indonesia|malaysia|south africa|nigeria|kenya|egypt|colombia|chile|peru|costa rica|hungary|bulgaria|serbia|croatia|"
    r"slovakia|slovenia|luxembourg|iceland|morocco|pakistan|bangladesh|sri lanka|nepal|okinawa|guam|germany|japan)\b",
    re.I,
)


US_STATES = (
    "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|"
    "indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|"
    "montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|"
    "oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|"
    "west virginia|wisconsin|wyoming|district of columbia"
)
US_RX = re.compile(
    rf"united states|\busa\b|\bu\.s\.a?\b|\bus-|\b(?:{US_STATES})\b|"
    r",\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|"
    r"OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b",
    re.I,
)


NON_US_COUNTRY = re.compile(
    r"\b(australia|united kingdom|england|scotland|wales|ireland|japan|south korea|korea|taiwan|germany|india|canada|"
    r"singapore|israel|france|netherlands|poland|spain|italy|sweden|norway|denmark|finland|romania|ukraine|mexico|brazil|"
    r"argentina|philippines|united arab emirates|uae|saudi arabia|qatar|bahrain|kuwait|oman|jordan|new zealand|"
    r"switzerland|austria|belgium|czech|czechia|estonia|lithuania|latvia|portugal|greece|turkey|china|hong kong|vietnam|"
    r"thailand|indonesia|malaysia|south africa|nigeria|kenya|egypt|colombia|chile|peru|costa rica|hungary|bulgaria|serbia|"
    r"croatia|slovakia|slovenia|luxembourg|iceland|morocco|pakistan|bangladesh|sri lanka|nepal)\b",
    re.I,
)


def explicitly_non_us(locations: list[str]) -> bool:
    """True only when every location names a foreign country and none names the US (structural, high precision)."""
    if not locations:
        return False
    for loc in locations:
        if US_RX.search(loc) or not NON_US_COUNTRY.search(loc):
            return False
    return True


def location_class(locations: list[str], remote: bool | None, hints: list | None = None) -> dict:
    """Offline hint for each location string; the job's class is its best (most preferred) one.

    `hints` is [(region_key, regex)] from config.region_hints(), most preferred first; by default the workspace
    profile's regions. This is only a hint: the AI location screener decides, and its answers are cached.
    """
    if hints is None:
        from .config import region_hints
        hints = region_hints()
    classes = []
    for loc in locations or []:
        l = loc.lower()
        is_us = bool(US_RX.search(loc)) and not re.search(r"\b(?:australia|canada|united kingdom|england)\b", l)
        hit = next((key for key, rx in hints if rx.search(l) and (is_us or not NON_US.search(l))), None)
        if hit:
            classes.append(hit)
        elif re.search(r"\bremote\b|anywhere|distributed", l):
            classes.append("non_us_remote" if (NON_US.search(l) and not is_us) else "remote_us")
        elif NON_US.search(l) and not is_us:
            classes.append("non_us")
        else:
            classes.append("other_us")
    if remote and "remote_us" not in classes:
        classes.append("remote_us")
    if not classes:
        classes = ["unknown"]
    order = [k for k, _ in hints] + ["remote_us", "other_us", "unknown", "non_us_remote", "non_us"]
    rank = {k: i for i, k in enumerate(order)}
    best = min(classes, key=lambda c: rank.get(c, len(order)))
    return {"best": best, "all": sorted(set(classes), key=lambda c: rank.get(c, len(order)))}


# ----------------------------------------------------------------------------- boilerplate
def boilerplate_lines(jobs: list[dict], threshold: float = 0.25) -> set[str]:
    """Lines that appear in a large share of a company's postings (about-us, benefits, EEO)."""
    if len(jobs) < 8:
        return set()
    counts: Counter = Counter()
    for j in jobs:
        counts.update({ln.strip() for ln in (j.get("description") or "").split("\n") if len(ln.strip()) > 40})
    cut = max(4, int(len(jobs) * threshold))
    return {ln for ln, c in counts.items() if c >= cut}


def strip_boilerplate(text: str, boiler: set[str]) -> str:
    if not boiler:
        return text
    return "\n".join(ln for ln in text.split("\n") if ln.strip() not in boiler).strip()


# ----------------------------------------------------------------------------- main entry
_SENIOR_WORDS = re.compile(
    r"extensive (?:professional )?experience|seasoned|deep expertise|expert[- ]level|proven track record of leading|"
    r"technical leadership|lead (?:a|the) team|mentor(?:ing)? (?:junior|other) engineers|senior[- ]level|"
    r"significant (?:professional )?experience|years of (?:professional|industry) experience",
    re.I,
)


def analyze(job: dict) -> dict:
    text = job.get("description") or ""
    sig = {
        "family": job_family(job.get("title", ""), job.get("department")),
        "level": title_level(job.get("title", "")),
        "yoe": extract_yoe(text),
        "clearance": extract_clearance(text),
        "us_person_required": extract_citizenship(text),
        "degree": extract_degree(text),
        "salary": extract_salary(text, job.get("salary_text")),
        "location": location_class(job.get("locations") or [], job.get("remote")),
        "age_days": days_since(job.get("posted_at")),
        "updated_age_days": days_since(job.get("updated_at")),
        "has_description": len(text) > 200,
        "seniority_phrases": sorted({m.group(0).lower() for m in _SENIOR_WORDS.finditer(text)})[:4],
    }
    return sig
