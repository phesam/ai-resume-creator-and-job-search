# Case study: one engineer's resume and job search, before and after

This workflow was built for one early-career software engineer in October 2026, then generalized. This page shows
what their resume looked like at each stage, what changed and why, and what happened to their applications.

**Privacy note.** Employers, products, projects and numbers below are changed so the person can't be identified.
The structure of every bullet, every edit, every reason and the application statistics are real.

---

## The person

- About 1.3 years full time as a software engineer at a large, well-known company, on a platform team: a
  high-traffic web portal (React/TypeScript), Node.js/GraphQL services, Kubernetes, monitoring and on-call.
- Two internships, a company-sponsored university capstone (a real-time ML system), merged open-source fixes in
  C++, and a short-lived startup with paying users.
- U.S. citizen. Wanted to move to a specific region or take a clear step up.

## Three versions of the resume

### Version 1: simple and general (early summer)

One page, short bullets, written by hand. Example bullets (details changed):

> Built and launched a Node.js/TypeScript GraphQL service powering personalized actions on the carrier portal
> homepage, owning schema design and production integration.
>
> Eliminated code changes and releases for routine homepage content updates by integrating the portal with the
> company's headless CMS.
>
> Leading engineering for a redesign of the portal's highest-traffic page across product, design, backend, and
> platform teams.

This version got the person a final-round interview at a company they badly wanted. One callback.

### Version 2: tailored by AI for every posting (late summer)

A chat-assistant workflow rewrote the resume for each posting to match its keywords: about a hundred applications,
each with its own resume file named after the company and role. Example bullets from those versions (details
changed):

> Built and operated a 520K-request/day portal-to-CMS orchestration service on the company's Kubernetes platform,
> cutting content and layout update lead time from next-day overnight releases to ~3 minutes.
>
> Owned production infrastructure across environments, API gateway and service-mesh routing, Grafana and log
> observability, alerting, and on-call support.
>
> Architected an MCP-compatible agent runtime with 48 built-in and gated tools, user-defined extensions, and
> approval-gated actions; enforced deny-by-default permissions, organization-scoped RLS, and signed updates.

Dense, keyword-heavy, written for a machine. Every bullet sounds impressive and almost none says what the thing
was for. The header also gained a city (the wrong one for where they wanted to work), and the AI had left
non-breaking hyphens inside the phone number and the LinkedIn URL.

**Zero human callbacks** from about a hundred tailored applications.

### Version 3: this workflow (October)

Rebuilt over about a week, one bullet at a time, from an interview about the work. Final bullets (details changed):

> Rebuilt the logistics company's carrier-portal homepage (>600K views/week) in **React/TypeScript** with heads of
> Product and Design as a personalized feed of carrier tasks; A/B tested, then shipped to all carriers with >70%
> positive ratings
>
> Built an end-to-end **AI agent** workflow that turns Figma designs into CMS fields, documentation, and
> corresponding API schemas; adopted across the company's portal teams to standardize contributions
>
> Added CMS capability to the carrier portal through a Node.js/GraphQL service (~900K req/day), enabling
> Marketing/Product to make layout and content changes in **~3 minutes, replacing a 1–2 day engineering release**
>
> Deployed new microservices on the company's cloud **Kubernetes** platform: set up API gateway routes and monitoring
> (Grafana dashboards, metrics, logs, alerts); created runbooks and provide on-call support
>
> Designed and built carrier onboarding transition dialogs in the shared app shell, aligning three teams on
> backend-set dismissal flags and fixing a race condition that caused wrong redirects; supports a projected $1.5M in revenue

And the capstone, which had been called a "prototype" with the university on the employer line:

> Built a real-time grid-fault detection system for <Sponsor>: ingests live substation sensor data (1,000+
> updates/min), scores each reading in ~8 ms, and flags failing equipment on a map for understaffed operators
>
> Trained its PyTorch autoencoder (**97.4%** accuracy) and added explanations of why each reading was flagged;
> won **2nd place** at the university capstone showcase and presented to the sponsor's directors

## What changed, and the reason for each

| Change | Why |
|---|---|
| Every bullet says what it was for | The goal was that anyone could read a bullet and understand what was done and why. Version 2 bullets listed tools and tasks with no purpose. |
| The homepage bullet leads with the product, its scale and who it served | The biggest, clearest result goes first, in words a recruiter can repeat. |
| "Built the CMS platform" became "Added CMS capability ... through a service" | The person built the layer in front of an existing CMS, not the CMS. Precise scope survives the interview. |
| "~3 minutes" sits right next to "replacing a 1–2 day engineering release" | The contrast is the result; six words between them killed it. "In minutes" was rejected for the exact number. |
| The AI workflow moved from last to second | It was strong, current and asked for; it was buried. |
| Kubernetes, monitoring, runbooks and on-call stayed, in one bullet with a colon | 7 of 11 target companies asked for it, the person really does it, and one earlier interviewer had liked exactly that. |
| The capstone names the sponsor as the employer, says what the system does and for whom | It was the person's best project; "prototype" and "built the backend" undersold it. |
| Precise capstone numbers kept | The person could explain exactly what each measured, and had discussed them in an interview. |
| The race-condition fix is in the onboarding bullet | It was the hardest work of the year; a bug that would have made the site unusable is engineering a manager respects. |
| No team size, no internal names, no process trivia | A reader gains nothing from knowing the team had two people. |
| No "increasing developer velocity", "required", "all but two", "5 more teams are adopting it" | Filler, or overclaim, or makes the reader wonder. |
| Header: no city; "U.S. Citizen" added; email, LinkedIn, GitHub clickable | A non-local city gets filtered; many targets were export-controlled; recruiters click. |
| Skills cut to two lines; AWS and a backend-as-a-service brand removed | Only things the person could be questioned on, and that a hiring manager would care about. |
| No "AI coding tools" skills line | Everyone uses them; keyword filler. It belongs in an interview answer. |
| The startup stayed under Projects, as "Co-founder & Software Engineer" | Former founders get fewer callbacks at big companies (field experiment). |
| Project dates and the honors list removed | They added nothing. |
| Wider gaps between bullets; the page auto-fits to exactly one full page | The first build read like one big paragraph. |
| Three role-family variants instead of a hundred tailored files | Tailoring stopped paying once AI made it free; the per-company copies went stale. |

The full rule set these became is the [resume playbook](RESUME_PLAYBOOK.md).

## What changed in the job search

| Before | After |
|---|---|
| Applied from LinkedIn and aggregator lists | Every open posting fetched from each company's own hiring system (about 600 companies registered) |
| Applied to whatever matched keywords, including many regular postings well above their level | Every candidate posting read in full; ranked by how much of the daily work they had already done, eligibility, location, freshness and career value |
| Postings asking 3+ years treated as stretches | Left off: with ~1.3 years, not realistic |
| A "Senior" posting with no years listed treated as possible | The company's own ladder checked; those went off the list |
| Repeat applications to the same few companies (more than a dozen to one) | Spread across companies; a list ordered by fit and what they wanted |
| Applied whenever | New postings at top targets checked daily; applied in the first week |
| History tracked by memory and filenames | History rebuilt from confirmation, rejection and interview emails; duplicates caught |
| Referrals not used | Referral roles listed first, three per company at most, with the role to ask for |

## Results

| Period | Applications | Human interviews | Automated tests |
|---|---|---|---|
| About 14 months with versions 1 and 2 | ~180 at ~90 companies | 1 (the version 1 callback, to a final round) | 4 |
| Two weeks with version 3 and this search | ~50 | 4 companies interviewing: 3 from applications sent the same day (each called within 10 days), 1 from an application sent a few weeks earlier | 0 |

**How much does this prove? Less than it looks like, and more than nothing.**
- The samples are small. Counting only the three interviews from the ~50 new applications: at a true rate of 3% per
  application (roughly the cold-application average in Ashby's data), three or more interviews in fifty applications
  happens about 19% of the time by chance. At the old rate of
  about 0.6% (1 in 180), it would happen less than 1% of the time.
- The resume, the targeting (early-career and level-I roles that matched the daily work, in the region they wanted)
  and the timing (fresh postings) all changed at once. There is no way to say how much each contributed.
- What the evidence does support: referrals and fresh, well-matched applications move odds the most; the resume is
  what decides whether the skim turns into a read. See [EVIDENCE.md](EVIDENCE.md).
