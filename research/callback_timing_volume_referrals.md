# Cold applications to US SWE roles (2024-2026): what moves recruiter-callback odds

_Research date: 2026-10-02. Status: COMPLETE (within budget: 25 page fetches; the web-search budget ran out mid-session, which left gaps on defense/aerospace data, Lever/Workday review mechanics, and cold-outreach reply rates)._

Each item is marked **[verified]** if it was read on the cited page this session, or **[search-summary]** if it comes only from a search-engine summary.

Evidence-strength labels:
- **strong**: large primary dataset (millions of records) from an ATS or platform, or a controlled study.
- **moderate**: vendor or platform data with a stated method, or a credible survey with a stated sample.
- **weak**: small, old, or undisclosed method, or secondary reporting of someone else's data.
- **anecdotal**: statements by recruiters or individuals.

---

## Executive summary

- **Referral vs. cold is the biggest measured gap by far.**
  - Ashby (38M applications, 93K jobs, 2021-2024): 40% of referred candidates reach an interview, against 3% of inbound (cold) applicants. The Q4 2024 offer rate per application was 7.3% for referrals and 0.2% for inbound, roughly 36x. **(strong)**
  - Gem (165M applications, 1.2M hires): referrals convert at 11x the inbound rate. **(strong)**
- **Expect 2-7% callbacks per cold application.**
  - Huntr (1.24M tracked applications, Oct 2024 to Jul 2026): company career pages 6.87%, Indeed 2.92%, Wellfound 3.75%, LinkedIn 1.95%, Dice 0.13%. **(moderate)**
  - Gem: 8% of applicants pass the initial screen and 0.5% get an offer, about 1 hire per 200 applications. **(strong)**
- **Volume roughly tripled since 2021.**
  - Ashby (May 2026): 300+ applications per hire, and candidates about 50% less likely to get an interview than five years ago. **(strong)**
  - Greenhouse: application volume up 102% since 2022, with 3x more applications per recruiter. **(moderate)**
  - LinkedIn: about 11,000 applications per minute in June 2025, up 45% or more year over year. **(moderate, secondary)**
- **Timing matters mostly in week 1.**
  - Ashby: the first week of applications is 2.5-3x larger than any later week, and non-interviewed candidates are archived after a median of about 6 days. **(strong)**
  - Greenhouse: "most recruiters review applications in the order they were sent." **(moderate)**
  - The well-known effect sizes are weak evidence: TalentWorks 2018 (n≈1,600) reported "up to 8x" within 96 hours, and GoApply reported day 1-2 = 2.5x, day 6-14 = 0.4x, day 15+ = 0.1x.
- **AI match-ranking is eroding the pure first-come advantage.**
  - Greenhouse Talent Matching (Real Talent, 2025-2026) lets reviewers "review the strongest matches first." Ashby offers AI-assisted review against recruiter criteria.
  - Neither auto-rejects. A strong match therefore matters more, and a late but strong applicant can still surface.
- **Stale and ghost postings are common.**
  - Greenhouse found 18-22% of its Q2 2024 postings were not intended to be filled. **(moderate-strong)**
  - In February 2026, 1 in 7 Indeed listings had been live 30+ days, and 4% had been live 4+ months. **(moderate)**
  - Technical roles take a median of about 75 days to first fill, so a 30-60-day-old posting may be real but late in its pipeline. **(strong)**
- **No public dataset exists for reply rates to job seekers' cold messages** to recruiters, hiring managers or alumni. Treat any specific "X% reply rate" claim as anecdotal.

---

## 1. Application timing, recruiter review order, staleness, ghost jobs

### 1a. Does applying soon after posting matter?

| Finding | Evidence | Source |
|---|---|---|
| **TalentWorks (2018, ~1,600 applications).** Applying in the first 96 hours ("Golden Hours") gave "up to an 8x higher chance" of an interview, and "every day you wait after the 'Golden Hours' reduces your chances by 28%". Applications sent 6-10am had a 13% interview chance, falling about 10% every 30 minutes after that. Applying on Monday gave +46%. | **weak**: small, observational, one vendor's users, not SWE-specific, pre-2020 market. Widely cited anyway. [verified via summary page] | paulvanderlaken.com summary; original at talent.works (2018) |
| **GoApply (2024, "10,000+ job seekers", via jobstrack.io).** Day 1-2 = 2.5x the average interview rate, day 3-5 = 1.0x, day 6-14 = 0.4x, day 15+ = 0.1x. Applying within 24-48h gave "2 to 3 times more interviews". "72% of job offers… went to people who applied within the first 5 days". | **weak**: secondary page, method not published, confounded because old postings include ghost or filled jobs. [verified on secondary page] | jobstrack.io |
| **Ashby (13M+ applications, 2021-2023, US tech companies with 1-1,500 employees).** "The first week of inbound applications is consistently 2.5-3x higher than all following weeks." Technical roles drew about 174 applications in their first 4 weeks in 2023, against about 60 in 2021. | **strong** (volume curve). [verified] | Ashby applications-per-job report |
| **Ashby (54M applications, 93K jobs, Jan 2021 to Mar 2026).** "Non-interviewed candidates are archived in a median ~six days"; interviewed candidates average 21 days. Review is continuous, roughly within a week of each application, not batched at the end. | **strong.** [verified] | Ashby Recruiting Operations Benchmarks |
| **Huntr.** The median time from application to first interview was 5.6 days (2025) and 6 days (Q1 2026). | **moderate.** [verified] | Huntr 2025 annual; Huntr Q1 2026 |

**Interpretation.** No high-quality causal study isolates timing. The mechanism is well supported, though:
1. Most applicants arrive in week 1.
2. Recruiters screen continuously, often in order received.
3. Shortlists for phone screens form within about the first 1-2 weeks.

Later applicants are usually still reviewed, but against a bar already set by an existing shortlist, and sometimes after active review has stopped. The raw multipliers (8x, 25x) are almost certainly overstated, because they are confounded by ghost or filled postings and by more motivated early appliers. A defensible prior is roughly 2-3x better odds in days 0-3 than in days 15+, larger for high-volume roles.

### 1b. How recruiters work through applicants

- **Greenhouse candidate blog (Jan 8, 2025).** "Most recruiters review applications in the order they were sent". Roles "get hundreds or even thousands of applications as soon as they are posted". When volume is high, recruiters may filter or auto-reject. **moderate** (vendor's description, not a measurement). [verified]
- **Greenhouse Talent Matching / Real Talent.**
  - Announced June 3, 2025, as a "tiered applicant inbox". [verified]
  - Packaged in the Fall 2025 release on Sept 16, 2025. [verified]
  - February 2026 release notes: it organizes "applications based on how they match your job criteria" so reviewers can "review the strongest matches first". Recruiters can filter by "priority candidates, fraud status, application date, location". "Talent Matching never advances or rejects candidates automatically." **moderate** (vendor documentation; adoption share unknown). [verified]
- **Ashby AI-Assisted Application Review.** Recruiters define must-have, should-have and nice-to-have criteria, and the AI marks each application against them with citations. Ashby says it does not numerically "rank" applicants, and a human advances or rejects. **moderate.** [search-summary]
- **Lever / Workday / iCIMS.** Not covered this session for lack of search budget. From background knowledge (not verified this session): Workday acquired HiredScore (2024), which grades candidates for recruiters. Treat this as unconfirmed.
- **Recruiter load explains why review stops early.** Gem: the average recruiter has 13-14 open reqs and 2,500+ applications. Recruiters handle 93% more applications than in 2021, with 14% fewer recruiters. **strong.** [verified]

**Takeaway.** Review order is moving from chronological to match-tiered. At AI-tiered companies, which in 2025-2026 increasingly include Greenhouse and Ashby customers, timing still helps but match quality decides whether you are seen at all. At high-volume companies reviewing in chronological order, timing matters more.

### 1c. Ghost jobs, evergreen or pipeline postings, reposts, staleness

- **Greenhouse (Q2 2024 data, reported by WSJ, Jan 13, 2025).** 18-22% of jobs posted on Greenhouse were ghost jobs ("roles that companies aren't actually trying to fill"). About 70% of its 7,500+ clients posted at least one. For about 15% of clients it was habitual, with half their Q2 listings unfilled. The most-affected industries were construction, arts, food and legal, not tech. **moderate-strong** (platform data, secondary reporting). [verified via Entrepreneur]
- **Clarify Capital (Feb 2026; 176,268 Indeed listings across 49 industries).** Listings live 30+ days were flagged as potential ghost jobs. 1 in 7 (about 14%) were live 30+ days, 4% for 4+ months, and 21% of senior-level postings were flagged. **moderate** as posting-age data; **weak** as a ghost-job measure, since age alone does not make a posting a ghost. [verified]
- **Clarify Capital (earlier survey, about 1,000 hiring managers).** 81% of recruiters said their employer had posted ghost jobs. About 1 in 3 had postings up 30+ days, and about 1 in 8 left a job open 4+ months. **weak-moderate** (commissioned survey). [search-summary]
- **Resume Builder (2024; 649 hiring managers via Pollfish).** About 39-40% said their company posted a fake listing in 2024. Top reasons: appearing open to external talent (67%), appearing to grow (66%), and making staff feel replaceable (62%). **weak-moderate.** [search-summary]
- **LiveCareer (Mar 2025; 918 HR professionals).** 45% "regularly" and 48% "occasionally" post ghost or pipeline jobs. **weak.** [search-summary]
- **Job-seeker perception.** In Huntr's Q1 2026 survey, 93% believe they applied to ghost jobs. A Greenhouse/HR Dive figure says 36% of seekers applied to a role that was never filled. **weak.** [verified / secondary]
- **How long real technical reqs stay open.**
  - Ashby: technical roles take a median of about 75 days to first fill (about 60 for business roles). By seniority, senior roles take 71 days, mid-level 63 and junior 52. **strong.** [verified]
  - Ashby's May 2026 release: about 10 weeks for technical roles. **strong.** [verified]
  - Gem: average time to hire is 41 days (2024). **strong.** [verified]
- **Reposts.** No dataset on callback outcomes for "Reposted" listings was found. This is a gap.

**When is a posting effectively stale?**
- **Days 0-3:** peak.
- **Days 4-7:** still in the main review cohort.
- **Days 8-14:** below average; a shortlist is likely forming.
- **Days 15-30:** low odds unless the role is niche or low-volume, or is AI-ranked and you are a top match.
- **Days 31+:** treat as stale.
- **Days 60+:** likely evergreen, ghost, or late-stage.

Even so, a 30-60-day-old technical posting is often a genuinely open req, because the median time to first fill is about 75 days. It is just past the cold-application window.

---

## 2. Applicant volume and response rates

### 2a. Volume per posting and per hire

- **Ashby (press release May 7, 2026; 100M+ applications, 200K+ jobs, 2021-2026).** 300+ applications per hire on average, tripled since 2021. Candidates are "roughly 50% less likely to receive an interview than they were five years ago". **strong.** [verified]
- **Ashby (2021 to early 2024).** Applications per technical role rose 161% (2.6x). In 2023 a technical role drew about 174 applications in its first 4 weeks. Company size (1-1,500 employees) made no significant difference. **strong-moderate** (pre-2025). [verified]
- **Gem 2026 benchmarks (165M applications, 15M candidates, 1.2M hires; Jun 2021 to May 2025).** 8% of applicants pass initial screening, and 0.5% get an offer, "roughly one hire per 200 applications". **strong.** [verified]
- **Gem 2025 benchmarks (140M applications; 2021-2024).**
  - Candidates are "3x less likely to get hired" than three years earlier.
  - Job boards produce 49.0% of applications but 24.6% of hires.
  - Time to hire rose from 33 to 41 days, and interviews per hire from 14 to 20.
  - **strong.** [verified]
- **Greenhouse (Sept 16, 2025).** Applications are up 102% since 2022, and recruiters have 3x more applications to review each. **moderate.** [verified]
- **LinkedIn (via NYT, June 2025; Fortune, Nov 18, 2025).** "An average of 11,000 applications per minute," with applications "spiked more than 45%," partly due to AI tools. **moderate** (platform figure, secondary reporting). [verified on Fortune]
- **CareerPlug 2024 (10M+ applications, SMBs, not tech).** About 180 applicants per hire, and 3% go from application to interview. **moderate** (secondary). [verified on secondary page]

### 2b. Cold-application response / callback rates

- **Ashby (38M applications).** Inbound application to interview: "just 3%". Inbound offer rate per application fell from 0.7% (Q3 2021) to 0.2% (Q4 2024), "a ~70% reduction". **strong.** [verified]
  - Note: a secondary summary (Studojo) cites about 12% for inbound application to interview. That fits the 2021 offer rate (12% x 6% ≈ 0.7%), so the 3% figure is the more recent one. This reconciliation is my inference.
- **Huntr best-job-boards (Oct 1, 2024 to Jul 1, 2026; 1,244,654 tracked applications; all occupations).** Interview rate by channel:

  | Channel | Interview rate |
  |---|---|
  | GovernmentJobs | 7.28% |
  | Company career pages | 6.87% |
  | Google Jobs | 6.60% |
  | Welcome to the Jungle | 3.78% |
  | Wellfound | 3.75% |
  | Direct ATS links | 3.16% |
  | Handshake | 3.10% |
  | Indeed | 2.92% |
  | Glassdoor | 2.89% |
  | LinkedIn | 1.95% |
  | Built In | 1.91% |
  | ZipRecruiter | 1.12% |
  | Dice | 0.13% |

  LinkedIn is 78% of all tracked applications; it rose to 4.00% in Q2 2026. **moderate** (self-selected users, self-reported outcomes, no role breakdown). [verified]
- **Huntr 2025 annual (598,627 applications from 57K+ seekers).** LinkedIn 3.1%, Indeed 4.5%, Wellfound 6.0%, Dice 0.35%. Tailored resumes converted at 5.8% and untailored at 3.73%. 18% of seekers needed 100+ applications to reach an offer. **moderate.** [verified]
- **Huntr Q1 2026 (139,927 applications; 25,635 seekers).** **moderate**, correlational. [verified]
  - Tailored resumes 4.23%, untailored 2.07%.
  - Seekers sending 11-20 applications got 9.25% per application; those sending 100+ got 2.58%.
  - One application per company gave 6.07%; 8+ applications to the same company gave 1.91%.
  - Remote-only roles 3.63%, onsite 5.76%.
- **Jobscan (Feb 2025; 2.5M applications from tool users).** A resume title matching the target title was associated with a "10.6 times higher" interview rate, and a cover letter with 3.4x. **moderate** (vendor, correlational; title match is partly a proxy for genuine fit). [verified]

### 2c. Big tech vs startups vs defense/aerospace

- **Startups.**
  - Wellfound's response rate is about 1.5-2x LinkedIn's: 3.75% vs 1.95% (2024-26), and 6.0% vs 3.1% (2025). **moderate-weak**, because channel is confounded with company and role mix.
  - Ashby, whose customer base is startup and scale-up heavy, found no significant difference in applications per job by company size (1-1,500 employees). [verified]
- **Big tech.**
  - No 2024-2026 primary applicants-per-posting figure was found.
  - Huntr's speed from application to interview: Meta and Uber 1-2 weeks; Google, Adobe, Microsoft and Salesforce 12-16 days; Accenture, IBM, Deloitte and EY 17-22 days; Pinterest and Oracle 30+ days. **moderate-weak.** [verified]
  - Given 300+ applications per hire on average, big-tech SWE postings plausibly run far higher. That is inference.
- **Defense/aerospace.**
  - No 2024-2026 primary data on applicant volume or callback rates was found within the budget. This is a gap.
  - Structurally, US-person (ITAR/EAR) and clearance requirements shrink the eligible pool. That is inference, not measured.
  - The only adjacent measured signal is government job boards: GovernmentJobs at 7.28-8.7%. This covers public-sector roles, not contractors.
- **Staffing or contract boards.** Dice's 0.13-0.35% is the worst channel measured, so deprioritize staffing-agency reposts.

---

## 3. Referrals and cold outreach

### 3a. Measured referral advantage

- **Ashby (38M applications, 93K jobs, 2021-2024).** **strong.** [verified]
  - Referrals are about 1% of applications, falling from 2% in Q1 2021 to under 1% by Q1 2024.
  - Application to interview: referral 40%, inbound 3%, sourced 25%, internal and agency 42%.
  - Interview to offer: referral 16%, inbound 6%, sourced 6%.
  - Offer rate per application, Q4 2024: referral 7.3% (down from 12.1%), inbound 0.2%. That makes referrals about 13x better at reaching an interview and about 36x better at reaching an offer.
- **Ashby Recruiting Ops (54M applications, through Mar 2026).** "52% of referred candidates pass initial screens compared to 35% overall." **strong.** [verified]
- **Gem 2026.** Referrals "convert at 11x the rate of inbound applicants". Sourced candidates are "nearly eight times more likely to be hired", and internal mobility is 32x. **strong.** [verified]
- **CareerPlug 2024 (10M+ applications, SMBs).** A referred applicant is about 11x more likely to be hired than a job-board applicant. Referrals are 2% of applicants but 11% of hires. **moderate** (secondary, non-tech). [verified on secondary page]
- **Huntr Q1 2026 survey (503 respondents who got interviews).** 38% of interviews came through relationships: employee referral 14%, recruiter outreach 13%, networking 12%. Yet "85% spend their time on online applications." **weak-moderate** (survey). [verified]
- **Jobscan recruiter survey (384 HR professionals, 2025).** 69.4% rate employee referrals "extremely" or "very" important. **moderate** (survey). [verified]

**Caveat.** Referral averages include strong referrals, where the referrer knows the candidate's work. A cold "referral-for-a-stranger" probably captures only part of this lift. No dataset separating the two was found.

### 3b. Reply rates of cold outreach to recruiters, hiring managers or alumni

- **No public primary dataset found.** One 2026 review states: "We found no public dataset with reply rates for candidate messages to hiring managers." [verified on lumyhired.com] Coverage was limited because the search budget ran out.
- **Closest proxies (not the same thing).**
  - Huntr Q1 2026: networking accounted for 12% and recruiter outreach for 13% of interviews. **weak-moderate.**
  - Gem: recruiter-sourced candidates convert at about 8x inbound. This measures recruiter-to-candidate outreach, not the reverse.
- Treat any specific "X% reply rate to cold emails or LinkedIn DMs" figures as **anecdotal**.

---

## Implications for ranking job postings

These are concrete defaults. Weights are judgment calls calibrated to the evidence above, not fitted to data.

**1. Suggested 100-point callback-likelihood score.**

| Component | Points | Why |
|---|---|---|
| Skills / title / seniority match | **55** | Best-supported lever. Title match ~10.6x (Jobscan); tailoring ~1.6-2x (Huntr); AI tiering surfaces "strongest matches first" (Greenhouse 2026). This is the gate in both chronological and AI-ranked review. |
| Freshness (posting age) | **20** | Real but weakly quantified. Mechanism is strong: week-1 volume 2.5-3x, ~6-day median archiving, in-order review. Effect sizes are weak (8x, 25x). Keep at about one-third of the match weight, so a mediocre fresh match never outranks a strong 2-3-week-old match. |
| Posting legitimacy / ghost risk | **15** | 18-22% ghost rate (Greenhouse); 14% of listings are 30+ days old (Clarify). |
| Channel / competition modifiers | **10** | Career page or direct ATS beats LinkedIn Easy Apply (6.87% / 3.16% vs 1.95%); onsite or hybrid beats remote-only (5.76% vs 3.63%); eligibility filters such as US-person or clearance shrink the pool. |

**Referral override.** If the user has a real referral path (someone who will submit them), rank the posting above all cold postings up to about 60 days old. Referrals give about 13x the interview rate and about 36x the offer rate (Ashby), which outweighs every other factor combined.

**2. Freshness points (out of 20), by days since original posting.**

| Days since posting | Points |
|---|---|
| 0-1 | 20 |
| 2-3 | 18 |
| 4-7 | 14 |
| 8-14 | 8 |
| 15-21 | 5 |
| 22-30 | 2 |
| 31-60 | 0, with a "stale" flag |
| >60 | 0, plus a −5 to −10 legitimacy penalty (likely evergreen, ghost, or late-stage) |

This curve compresses the GoApply shape (2.5x, 1.0x, 0.4x, 0.1x) roughly on a log scale, discounted for weak evidence and AI ranking.

**3. Adjustments to the freshness curve.**
- **AI-ranked ATS** (Greenhouse with Talent Matching, Ashby AI review, likely for many 2025-2026 startups and scale-ups): stretch the curve about 1.5x. For example, give 8-14 days the 4-7-day value, because strong matches can surface late.
- **Very high-volume roles** (big tech, generic "Software Engineer II", remote-only): steepen the curve. Treat 8+ days as 15-21 days.
- **Low-volume or eligibility-restricted roles** (US-person or clearance-required defense/aerospace, niche stacks): stretch the curve about 1.5-2x, because a smaller pool means a slower shortlist. This is inference.

**4. Legitimacy penalties (out of 15).** All of the following are judgment, with no outcome data behind them.
- −5: no posting date available.
- −5: posted 31-60 days ago.
- −10: posted more than 60 days ago.
- −5: generic or evergreen title ("General Application", "Talent Community", "Future Opportunities").
- −5: "Reposted" with an original date more than 30 days ago. Use the original date for freshness when known.
- −10: staffing-agency or Dice-sourced (Dice converts at 0.13-0.35%).
- −3: the same company has 8+ open reqs with identical text across many locations (an evergreen signal).

**5. Per-company cap.** Apply to at most 2-3 best-matching reqs per company per quarter. In Huntr data, one application per company converted at 6.07%, against 1.91% for 8+.

**6. Operational rule.** Scrape daily and apply to strong-match postings within 72 hours (ideally within 24). Go through the company career page or ATS rather than Easy Apply. Plan on about 2-7% callbacks per cold application, so roughly 15-50 strong-match applications per expected interview.

**7. Expected-value framing.**
- Cold application: about 3% to interview (Ashby), or about 2-7% depending on channel (Huntr).
- Referral: about 40% to interview (Ashby).
- One referral is worth about as much as 10-15 cold applications. Spend part of each day turning top-ranked postings into referral attempts (alumni, ex-colleagues) instead of only applying.

---

## Sources

**Primary (ATS or platform data)**
- Ashby, "Are referred candidates more likely to get hired?" (38M applications, 2021-2024): https://www.ashbyhq.com/talent-trends-report/reports/referrals
- Ashby, Recruiting Operations Benchmarks (54M applications, 2021 to Mar 2026): https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends
- Ashby, Applications per Job (13M+ / ~14M applications): https://www.ashbyhq.com/talent-trends-report/reports/2023-trends-report-applications-per-job
- Ashby press release, May 7, 2026 (100M+ applications): https://www.prnewswire.com/news-releases/new-data-from-ashby-reveals-surge-in-applications-rising-selectivity-and-shifting-recruiter-workloads-302765846.html
- Ashby, AI-Assisted Application Review [search-summary]: https://www.ashbyhq.com/product-updates/ai-assisted-application-review
- Gem, 2026 Recruiting Benchmarks takeaways: https://www.gem.com/blog/key-takeaways-from-the-2026-recruiting-benchmarks-report
- Gem, 2025 Recruiting Benchmarks takeaways: https://www.gem.com/blog/10-takeaways-from-the-2025-recruiting-benchmarks-report

**Greenhouse (vendor statements and documentation)**
- "What really happens after you apply" (Jan 8, 2025): https://my.greenhouse.com/blogs/what-really-happens-after-you-apply-for-a-job
- Introducing Real Talent (June 3, 2025): https://www.greenhouse.com/blog/introducing-greenhouse-real-talent
- Real Talent update (July 31, 2025): https://www.greenhouse.com/blog/making-hiring-safer-and-more-human-an-update-on-real-talent
- Release notes, February 2026: https://support.greenhouse.io/hc/en-us/articles/47028491519387-Release-notes-February-2026
- Fall 2025 press release (Sept 16, 2025): https://www.prnewswire.com/news-releases/greenhouse-launches-new-tools-to-tame-chaotic-hiring-funnels-302556958.html

**Job-seeker tracker data and vendor surveys**
- Huntr, 2025 Annual Job Search Trends: https://huntr.co/research/2025-annual-job-search-trends-report
- Huntr, Q1 2026 Job Search Trends: https://huntr.co/research/job-search-trends-q1-2026
- Huntr, Best Job Boards of 2026, Ranked by Interview Rate: https://huntr.co/research/best-job-boards
- Jobscan, State of the Job Search 2025: https://www.jobscan.co/state-of-the-job-search

**Ghost jobs**
- Greenhouse ghost-job data (via WSJ), Entrepreneur, Jan 2025: https://www.entrepreneur.com/business-news/ghost-job-listings-on-the-rise-how-to-spot-avoid-experts/485494
- Clarify Capital, Ghost Jobs 2026 (Indeed listings analysis): https://clarifycapital.com/ghost-jobs-2026
- Clarify Capital, earlier hiring-manager survey [search-summary]: https://clarifycapital.com/job-seekers-beware-of-ghost-jobs-survey
- Resume Builder survey, via Staffing Industry Analysts [search-summary]: https://www.staffingindustry.com/news/global-daily-news/39-hiring-managers-report-fake-job-listings-report-says
- LiveCareer survey, via The Interview Guys [search-summary]: https://blog.theinterviewguys.com/ghost-jobs-exposed/

**Secondary reporting and weak sources**
- Fortune, Nov 18, 2025 (LinkedIn 11,000 applications per minute): https://fortune.com/2025/11/18/hiring-job-seekers-recruiters-talent-acquisition-ai-doom-loop-application-technology/
- TalentWorks 2018, summarized: https://paulvanderlaken.com/tag/talentworks/ (original: https://talent.works/blog/2018/01/08/the-science-of-the-job-search-part-i-13-data-backed-ways-to-win/)
- jobstrack.io, citing GoApply 2024: https://jobstrack.io/blog/first-mover-advantage-applying-early-tech-jobs
- Lumyhired, 2026 (states that no public cold-outreach reply-rate dataset exists): https://www.lumyhired.com/blog/job-search-strategies-2026
- LastRound AI, citing CareerPlug 2024: https://lastroundai.com/blog/application-response-rate-benchmarks
- CareerPlug: https://www.careerplug.com/recruiting-metrics-and-kpis/
- Studojo, citing CareerPlug referral data: https://studojo.com/reports/referrals-vs-applications-how-people-get-hired-2026
