# Evidence

What the research says about getting a callback, how strong each piece is, and where it comes from. Researched
October 2026. The longer notes behind this page are in [`research/`](../research).

**Strength labels.** **Strong**: a randomized or field experiment, a large primary dataset (millions of records) from
an ATS or platform, a statistical fact, or primary vendor documentation of how a tool behaves. **Moderate**: large
vendor data with a stated method, consistent guidance from several major employers' recruiting teams, or a credible
survey. **Weak**: vendor marketing, small or undisclosed samples, single-company analyses. **Anecdotal**: individual
recruiters and hiring managers.

**The honest headline:** almost nothing about resume *format* has been tested causally for software engineers. The
strongest evidence is about the channel (referral vs cold), timing, writing quality, founder signals, and what AI did
to the value of tailoring. Everything else is a convergence of moderate and weak evidence, labeled that way.

---

## 1. The channel matters more than anything on the page

| Finding | Strength | Source |
|---|---|---|
| 40% of referred candidates reach an interview vs 3% of inbound (cold) applicants; offer rate per application 7.3% vs 0.2% (Q4 2024) | Strong (38M applications) | [Ashby: referrals](https://www.ashbyhq.com/talent-trends-report/reports/referrals) |
| Referrals convert at 11x the inbound rate; ~1 hire per 200 applications | Strong (165M applications) | [Gem 2026 benchmarks](https://www.gem.com/blog/key-takeaways-from-the-2026-recruiting-benchmarks-report) |
| 300+ applications per hire, tripled since 2021; candidates ~50% less likely to get an interview than five years ago | Strong (100M+ applications) | [Ashby, May 2026](https://www.prnewswire.com/news-releases/new-data-from-ashby-reveals-surge-in-applications-rising-selectivity-and-shifting-recruiter-workloads-302765846.html) |
| Interview rate by channel: company career pages 6.87%, direct ATS links 3.16%, Indeed 2.92%, LinkedIn 1.95%, Dice 0.13% | Moderate (1.24M tracked applications; self-reported) | [Huntr: best job boards](https://huntr.co/research/best-job-boards) |
| No public dataset exists for reply rates to cold messages to recruiters or alumni; treat any "X% reply rate" as anecdote | — | [Lumyhired 2026](https://www.lumyhired.com/blog/job-search-strategies-2026) |

**So:** get referrals for your best-fit roles; apply on the company's own site, not through Easy Apply; expect 2–7%
per cold application.

## 2. Timing: week one matters

| Finding | Strength | Source |
|---|---|---|
| The first week of applications is 2.5–3x larger than any later week | Strong | [Ashby: applications per job](https://www.ashbyhq.com/talent-trends-report/reports/2023-trends-report-applications-per-job) |
| Non-interviewed candidates are archived after a median of ~6 days; review is continuous, not batched | Strong (54M applications) | [Ashby: recruiting ops benchmarks](https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends) |
| "Most recruiters review applications in the order they were sent" | Moderate (vendor description) | [Greenhouse, Jan 2025](https://my.greenhouse.com/blogs/what-really-happens-after-you-apply-for-a-job) |
| Greenhouse's matcher lets recruiters "review the strongest matches first"; it never advances or rejects by itself | Moderate (documentation) | [Greenhouse release notes, Feb 2026](https://support.greenhouse.io/hc/en-us/articles/47028491519387-Release-notes-February-2026) |
| "Up to 8x" for the first 96 hours; day 1–2 = 2.5x, day 15+ = 0.1x | Weak (small, vendor, confounded by ghost jobs) | TalentWorks 2018; [GoApply via jobstrack.io](https://jobstrack.io/blog/first-mover-advantage-applying-early-tech-jobs) |
| 18–22% of Greenhouse postings in Q2 2024 were not meant to be filled ("ghost jobs") | Moderate | [Entrepreneur, via WSJ](https://www.entrepreneur.com/business-news/ghost-job-listings-on-the-rise-how-to-spot-avoid-experts/485494) |
| Technical roles take a median ~75 days to first fill | Strong | Ashby benchmarks |

**So:** check your top companies daily and apply in the first week; a 30–60-day-old posting may be real but late in
its pipeline. The tool weights age at about a third of fit because the size of the early advantage is poorly
measured.

## 3. What the screening software actually does

| Finding | Strength | Source |
|---|---|---|
| The "75% of resumes rejected by ATS bots" figure traces to a 2012 sales claim by a resume-optimization company that never published a method | Strong (origin traced) | [Computerworld 2012](https://www.computerworld.com/article/1458323/5-insider-secrets-for-beating-applicant-tracking-systems.html) |
| ATSs parse and index; knockout questions (authorization, location, clearance, years) are the real automatic filter | Moderate | [Orosz, The Tech Resume Inside Out](https://thetechresume.com/samples/ats-myths-busted); [Enhancv, 25 recruiters](https://enhancv.com/blog/does-ats-reject-resumes/) |
| Greenhouse Talent Matching sorts applicants by calibrated criteria; skills match by meaning; **more matched terms don't necessarily mean a higher score**; no auto-reject | Strong (documentation) | [Greenhouse Talent Matching FAQ](https://support.greenhouse.io/hc/en-us/articles/41131886674075-Talent-Matching-FAQ) |
| Ashby's AI review marks each criterion met or not with a citation from the resume; no numeric ranking; a human decides | Strong (documentation) | [Ashby AI-assisted review](https://www.ashbyhq.com/product-updates/ai-assisted-application-review) |
| Workday HiredScore grades applicants A–D, which can set review order | Strong (documentation) | [Workday responsible AI](https://www.workday.com/en-us/legal/responsible-ai-and-bias-mitigation.html) |
| 88% of employers agree their systems screen out qualified candidates who don't exactly match criteria | Moderate (employer self-report) | [HBS/Accenture, Hidden Workers](https://www.hbs.edu/managing-the-future-of-work/research/Pages/hidden-workers-untapped-talent.aspx) |
| No ATS vendor documents a keyword-match pass threshold | Moderate | Vendor documentation above |

**So:** write for the matcher by naming the real technologies you used, in sentences, under standard headings, in a
PDF whose text extracts cleanly. Don't chase a "match score". Answer form questions truthfully; that's where the
automatic filtering is.

## 4. How people read resumes

| Finding | Strength | Source |
|---|---|---|
| First skim averages 7.4 s; strong resumes had simple layouts, clear headings, bold titles; weak ones had clutter, long sentences, columns, little white space and keyword stuffing | Moderate (small vendor study) | [Ladders eye-tracking, 2018](https://www.hrdive.com/news/eye-tracking-study-shows-recruiters-look-at-resumes-for-7-seconds/541582/) |
| 76 recruiters, ~2,200 judgments: median 31 s per resume; decisions tracked company brands more than content | Moderate | [interviewing.io, 2024](https://interviewing.io/blog/are-recruiters-better-than-a-coin-flip-at-judging-resumes) |
| Experience at a top company raised selection odds by ~35% | Moderate | interviewing.io, 2024 |
| Readers take in about the first two words of a list item when scanning | Moderate (usability research) | [Nielsen Norman Group](https://www.nngroup.com/articles/first-2-words-a-signal-for-scanning/) |
| Typos were the strongest predictor of offers in one startup's hiring data | Weak–moderate | [Aline Lerner, 2013](https://blog.alinelerner.com/lessons-from-a-years-worth-of-hiring-data/) |
| A hiring manager who reads "lead developer of a React Native app" still doesn't know whether it shipped or worked; specific evidence wins | Anecdotal | Jacob Kaplan-Moss, on evaluating candidates |

**So:** the employer name, your title and the first bullet or two of each job decide the skim. Lead with the
strongest, most recognizable result.

## 5. Writing the bullets

| Finding | Strength | Source |
|---|---|---|
| Algorithmic writing help on ~480K jobseekers' resumes produced ~8% more hires, with no drop in employer satisfaction | Strong (RCT) | [Wiles, Munyikwa & Horton, NBER / Management Science](https://www.nber.org/papers/w30886) |
| "Accomplished [X] as measured by [Y], by doing [Z]"; say what the outcome was | Moderate (official guidance) | [Google: how we hire](https://www.google.com/about/careers/applications/how-we-hire/); [Laszlo Bock](https://www.linkedin.com/pulse/20140929001534-24454816-my-personal-formula-for-a-better-resume) |
| Focus on actions and results; apply the "so what?" test | Moderate | [Amazon recruiters](https://www.aboutamazon.com/news/workplace/amazon-job-application-resume-writing-tips) |
| A number with a baseline ("from X to Y") is believed; a lone percentage is doubted | Anecdotal (consistent across practitioners) | Bock; [James Cooper](https://thecareerlaunchpad.beehiiv.com/p/the-deal-with-resume-metrics) |
| Internal project names and acronyms are a common mistake | Anecdotal | [Gergely Orosz, common mistakes](https://thetechresume.com/samples/common-mistakes) |
| Recruiters prefer short bullets (72%); natural keyword use over stuffing (76%) | Weak (n=25, vendor) | [Enhancv](https://enhancv.com/blog/does-ats-reject-resumes/) |
| Plain verbs (built, shipped) read better than inflated ones (spearheaded, leveraged); identical bullet shapes and unverifiable metrics read as AI | Anecdotal | [Steve Yegge](https://steve-yegge.blogspot.com/2007/09/ten-tips-for-slightly-less-awful-resume.html); [Gem, Apr 2026](https://www.gem.com/blog/detect-ai-generated-resumes) |
| No study compares one-line and two-line bullets; Huntr's guidance is 3–5 bullets per role at 150–200 characters | — | Huntr resume guidance |

## 6. Tailoring and AI

| Finding | Strength | Source |
|---|---|---|
| On a large freelance platform, employers paid a premium for customized applications before LLMs, and stopped after | Moderate–strong | [Galdin & Silbert, 2025](https://arxiv.org/abs/2511.08785v1) |
| Tailored resumes 4.23% vs untailored 2.07% interview rate | Weak (self-reported; the vendor sells tailoring; tailorers may pick better-fit jobs) | [Huntr Q1 2026](https://huntr.co/research/job-search-trends-q1-2026) |
| 74% of hiring managers have seen AI content in applications; 76% say it makes authenticity harder to judge | Weak–moderate (survey) | [Resume Genius 2025](https://resumegenius.com/blog/job-hunting/ai-impact-on-hiring) |
| 67% of HR leaders say AI-generated applications slow hiring | Weak–moderate | [Robert Half, Mar 2026](https://press.roberthalf.com/2026-03-10-Robert-Half-survey-67-of-HR-leaders-report-AI-generated-applications-are-slowing-hiring) |
| 22% of hiring managers have found hidden prompt-injection text in resumes | Moderate (survey) | [Greenhouse, Nov 2025](https://www.greenhouse.com/newsroom/an-ai-trust-crisis-70-of-hiring-managers-trust-ai-to-make-faster-and-better-hiring-decisions-only-8-of-job-seekers-call-it-fair) |
| LLM screeners prefer resumes written by the same model 67–82% of the time | Moderate (model behavior; real-hiring effect unknown) | [Xu, Li & Jiang, 2025](https://arxiv.org/abs/2509.00462) |
| Google: show each minimum qualification clearly; Amazon: keep several resumes for different skill sets | Moderate | Google, Amazon guidance above |

**So:** a few hand-polished role-family resumes, the posting's term for things you really did, and never per-job
regeneration, hidden text or prompt injections. In the case study, ~100 AI-tailored applications produced zero human
callbacks.

## 7. Specific signals

| Finding | Strength | Source |
|---|---|---|
| 2,400 applications to entry-level software jobs: non-founders 24% callbacks vs former founders 13.6%; successful founders fared worst | Strong (field experiment) | [Botelho & Chang, Organization Science 2023](https://pubsonline.informs.org/doi/10.1287/orsc.2022.1592) |
| Applicants farther from the job got fewer callbacks | Strong design, low-wage jobs | [Phillips, JHR 2020](https://jhr.uwpress.org/content/55/3/864) |
| Location appears in 97.6% of recruiter searches and is mandatory 90.8% of the time | Moderate (one platform) | [Pin, 2026](https://www.pin.com/blog/recruiter-search-behavior-study/) |
| ITAR "U.S. person" covers citizens, permanent residents, refugees and asylees; export-controlled roles require it | Strong (regulation) | [22 CFR 120.62](https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.62) |
| 42% of employers screen new grads by GPA (down from 73% in 2019) | Moderate | [NACE Job Outlook 2026](https://www.naceweb.org/job-market/trends-and-predictions/employer-use-of-skills-based-hiring-practices-grows) |
| Standout open source belongs on the resume, with why it matters; recruiters often don't click links, and Greenhouse can anonymize them | Anecdotal / documentation | Orosz; Greenhouse docs |
| One application per company: 6.07% response; 2–3: 4.64%; 4–7: 3.34%; 8+: 1.91% | Moderate (correlational) | Huntr Q1 2026 |
| Google allows up to three applications per rolling 30 days | Strong (Google's own rule, for Google) | [Google Careers help](https://support.google.com/googlecareers/answer/6095391?hl=en) |

## 8. Format and parsing

| Finding | Strength | Source |
|---|---|---|
| At least 15% of CVs use columns; a major parser handles true column gaps correctly ~82% of the time | Moderate | [Textkernel](https://www.textkernel.com/learn-support/blog/improving-extraction-from-column-resumes/) |
| Text-based PDFs parse fine; image-only PDFs and DOCX quirks are the real risks | Moderate | Orosz; Greenhouse and Lever docs |
| Non-breaking hyphens (U+2011) survive PDF extraction as distinct characters and break exact-phrase search; DOCX importers have dropped them, turning "2019-2021" into "20192021" | Weak (technical tests, bug reports) | Extraction test in `research/`; [bug report](https://github.com/klasolsson81/jobbliggaren/issues/1802) |
| GPT models emit narrow no-break spaces (U+202F) | Weak | [OpenAI community thread](https://community.openai.com/t/gpt-5-non-reasoning-outputs-u-202f-narrow-no-break-space-instead-of-normal-spaces-breaks-text-rendering-on-macos-apps/1362321) |

## 9. What one person's results can and can't tell you

- With a true callback rate of p per application, the chance of zero callbacks in 100 applications is 37% at p = 1%,
  13% at 2%, 5% at 3%. Zero for 100 is unlucky at an average rate but plausible at 1–2%.
- To show one resume version doubles callbacks (3% → 6%) with standard confidence takes about 750 applications per
  version. You can't A/B test your way to an answer; use research-backed defaults and reviews from people who hire.

## Gaps

- No 2024–26 primary data on applicant volume or callback rates at defense and aerospace contractors.
- No data on callback outcomes for reposted listings.
- No public data on reply rates to cold outreach.
- Lever, Workday and iCIMS review mechanics were not verified from primary sources.
