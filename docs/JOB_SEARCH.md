# How the job search works, and why

The goal is every posting you could realistically get a callback for, at the companies you care about or across a
whole region, read in full, ranked by your odds and what you want, with nothing silently dropped. Sources and
strength ratings for every claim are in [EVIDENCE.md](EVIDENCE.md).

## The pipeline

| Stage | What happens | Why |
|---|---|---|
| **1. Fetch** | Every open posting straight from the company's own hiring system (applicant tracking system, ATS) through its public API: Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, Recruitee, Eightfold, Phenom, BrassRing, TalentBrew, Oracle Recruiting, Jibe, Pinpoint, Rippling, Gem, Dover, Teamtailor, Breezy, BambooHR, Jobvite, iCIMS, and Amazon, Apple, Google, Meta, TikTok and Atlassian. About 600 companies are pre-registered in `data/companies.yaml`. | The ATS is the source of truth. Job boards miss postings, duplicate them, and show the date *they* found a posting instead of when it was published. |
| **2. Universal checks** | Code removes only clear mismatches, each with quoted evidence: postings only abroad, internships, contract roles, staff/principal/lead/manager/director titles, "Senior" without a stated requirement within your limit, a stated minimum above your limit, an active clearance you don't hold, PhD required. Every exclusion is listed with its reason in the run's `triage.md`. | These read the same at every company. A regression suite (`tests/`) built from real Greenhouse, Workday, Lever and iCIMS wording catches a rule change that fixes one company and breaks another. |
| **3. AI screen** | Subagents read each company's titles (with department) and every location string, and decide "worth reading / adjacent / not relevant" and which of your regions a location is in. Keyword guesses are shown only as hints. When unsure, they keep. Decisions are cached. | No keyword list anticipates "Discovery Engineer", "Member of Technical Staff" or "Ontario, California" vs "Toronto, Ontario". |
| **4. Read** | Reviewer subagents read every remaining posting in full against your inventory (`jobhunt/rubrics/REVIEW_RUBRIC.md`) and score work match, skills, domain, level, competition, role type and career value, with any dealbreaker quoted. Identical postings are read once; earlier reviews carry over when the text hasn't changed. | Fit can't be judged from keywords. Reviewers caught a required drone-pilot license and a "recently completed degree" window that no rule did. |
| **5. Rank** | A score per posting (below), tiers A to D, and ★ on the best roles at each company. | Callback odds behave like a product: one blocker sinks them no matter how good the rest is. |
| **6. Dedupe** | Your history is rebuilt from email (confirmations, rejections, interview invites) into `applications.csv`; every posting is checked against it. | Email is the record. Filenames and memory missed most of the case study's history at one company. |
| **7. List** | `APPLY_LIST.md` and a checkbox page: referral roles first, then your region, then everywhere else, ordered by fit and what you want, each with posted date, link and which resume to send. | One place to apply from, in the order that matters. |

A **company run** (`find`) does this for one employer. A **sweep** (`sweep --regions home,remote_us`) does it across
every registry company at once and keeps only postings in the regions you name; multi-site postings listed as
"3 Locations" are kept until their detail page says where they are.

## Eligibility rules learned the hard way

- **Set your own years limit and mean it.** `eligibility.max_required_years`. The case-study candidate, with about
  1.3 years, decided postings asking 3+ were not realistic and wanted them gone, not listed as stretches.
- **A missing years line is not eligibility.** "Senior" with no years at one company meant 3–5+ years and at another
  5–12. The reviewer judges level from the same company's other postings and pay bands. Count a Senior title as
  eligible only when that posting itself states a minimum within your limit (some companies' "Senior" really is 2+).
- **Read years for someone with your degree.** "Bachelor's with 5 years, or Master's with 3, or PhD with 1" asks 5 of
  a bachelor's holder. "Bachelor's; OR 2+ years in lieu of a degree" asks no years of you. A "Level 2 or 3" posting
  counts the lower level. Before this was fixed, the parser read most of one large employer's postings as asking 2+
  years when they asked 1+, and wrongly dropped 47 postings.
- **Meeting the minimum list is not a fit.** An electronic-warfare posting scored near-perfect because TypeScript was
  one of five accepted languages; the team actually worked in Rust and Haskell on radio systems. That is why
  `work_match` (how much of the daily work you've done) multiplies the whole score.
- **The form is the real filter.** A referral was nearly spent on a role whose form asked "3+ years with a JVM
  language? Yes/No". Read the required questions first: `python3 -m jobhunt fresh show "<Company>" <id>` prints them
  for Greenhouse and Ashby postings. Answer truthfully.
- **New-grad programs have windows.** "Graduated within the last 12 months", "Class of 2026". Check them.
- **Read every location.** A posting listing five cities including Los Angeles is a Los Angeles posting. A posting
  open in several places counts as its best location for you.
- **Choose the resume by what the posting asks**, not the company's industry.

## The ranking model

`score = 100 × match quality × work match × experience × clearance × location × chance of being seen × competition × role preference × career value × repeat applications`

Every weight lives in `profile.yaml` so you can change it. They are calibrated judgment, not fitted rates.

- **Match quality** = 0.6 × required qualifications + 0.25 × domain hooks + 0.15 × level fit (reviewer scores).
  Skills and title match are the best-supported lever, and Greenhouse's matcher now lets recruiters review the
  strongest matches first.
- **Work match** (0–5 → 1.0 / 0.85 / 0.6 / 0.35 / 0.15 / 0.05). See above. A review with no work match is estimated
  from its requirements score, never treated as a full match.
- **Experience**: 1.0 at or below your years (or an early-career window that fits), 0.75 at 2+, 0.4 at 3+, 0.25 at 3+
  with "non-internship" wording, 0.15 at 4+, 0.05 at 5+. With no years stated, the reviewer's level fit decides
  (5 → 1.0, 4 → 0.85, 3 → 0.6, 2 → 0.35).
- **Clearance and citizenship**: active clearance required → excluded (unless you hold one); preferred × 0.85;
  "eligible to obtain" no penalty; U.S.-person-only (ITAR) × 1.05 because it shrinks the pool and you qualify;
  polygraph × 0.8.
- **Location**: your region weights. The case study: home region 1.1, remote 1.1 (a remote job lets you live where
  you want), outer home region 1.0, a second metro 0.85, elsewhere 0.65, or 0.85 when the reviewer rates the role 5/5
  for career value ("elsewhere would have to be a great company").
- **Chance of being seen** = 0.45 + 0.55 × freshness, freshness from 1.0 at 0–1 days to 0.06 past 60 days. Ashby's
  data: the first week of applications is 2.5–3× larger than any later week and non-interviewed candidates are
  archived after a median of about 6 days. How much early applicants gain is weakly measured, so age gets about a
  third of the weight of fit: a mediocre fresh match never outranks a strong match that is 2–3 weeks old. The curve
  is stretched 1.5× on Greenhouse and Ashby (AI ranking surfaces strong matches late) and for U.S.-person roles
  (smaller pool). Dates always come from the employer's own system. A referral switches this factor off.
- **Competition**: 0.84–1.16 from the reviewer's estimate.
- **Program window**: new-grad programs for recent graduates × 0.65 when you'd be 12–18 months past graduation at the
  start, × 0.5 beyond that.
- **Role preference** and **career value** (0.7 + 0.06 × value): what you want, so a niche or dead-end role drops up
  to 30%.
- **Repeat applications**: off by default. Huntr's data shows response rates per application falling from 6.07% (one
  application to a company) to 1.91% (8+), but that is diminishing returns per application, not proof that a
  good-fit role is hurt by an earlier rejection. The case-study candidate objected when it buried good roles, so it
  became opt-in. History is shown next to every role either way.
- **Referrals**: a contact who can refer you anywhere at a company removes posting age and pool pressure there; a
  referral for a named posting triples its score. About 40% of referred candidates reach an interview against about
  3% of cold applicants (Ashby, 38M applications).

**Tiers:** A ≥ 55, B ≥ 42, C ≥ 30, D below, X = a dealbreaker found on reading. A strong role blocked by one stated
requirement is listed separately as "ask first": raise it with a referrer or recruiter instead of applying cold.

## How many per company

The reports star up to `apply_cap` roles per company per quarter (default 8; the case study started at 3 and
raised it when the cap hid strong matches). The evidence is thin: Google's own rule is three applications per 30
days at Google; Huntr's per-application response rates fall with volume; recruiters see every application on one
candidate profile. A guideline, not a law. The apply list caps each company at `per_company_max` minus what you sent
there in the last 90 days, and never caps a role you asked to track or a company in `uncapped_companies`.

## Duplicates

A posting is marked DUPLICATE (and left off every list) when you applied to the same posting, or to the same title
at the same company, within about six months. Same company and a similar title is shown for information only. An
outcome older than six months is shown as "applied before" and does not block. Level I and level II with the same
words are different postings.

## Finding companies

Use aggregators only to discover companies, then run this workflow on each company's own system:
- the registry itself (`category` and region fields in `data/companies.yaml`);
- SimplifyJobs' New-Grad-Positions on GitHub (updated daily, with citizenship flags) for early-career programs;
- hiring.cafe (crawls employer career pages, good filters);
- regional lists such as Built In.

Never trust an aggregator's "posted" date.

## Speed

- `python3 -m jobhunt watch` (no AI calls) lists postings new since the last check at `watchlist.yaml` companies.
- `python3 -m jobhunt fresh list --days 8` lists postings first published in the last N days, by the employer's own
  date, minus ones you've marked reviewed. The watch skill reads them, decides eligibility, and adds the good ones to
  `picks.yaml` and your apply list. Run it daily (a scheduled task works) for your top targets.

## Honest limits

- Callback rates are low for everyone: about 2–7% per cold application in 2025–26. No resume fixes that alone.
  Referrals and applying in a posting's first week move the odds most.
- The multipliers are calibrated judgment from the evidence, not fitted rates.
- Some hiring systems have no adapter or block scripts. The tool says so; it never reports a partial fetch as
  complete. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- The code assumes a U.S. job search (citizenship, clearance, U.S. locations). The resume method is not U.S.-specific.
