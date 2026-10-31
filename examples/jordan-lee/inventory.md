# Work and accomplishments inventory: Jordan Lee (fictional example)

A filled-in example of `workspace/inventory.md`. Jordan, the companies and the numbers are invented; the shape of
each entry is what a useful inventory looks like. The resume built from it is `templates/resume.yaml`, and it's at the
density a finished page should have. Notice how much here didn't make the page: an inventory should be bigger than a
resume, so choosing is possible.

## Basics

- Work authorization: U.S. citizen. No clearance.
- Wants: Southern California or remote; open to the Bay Area for a strong role.
- Links: jordan.lee@example.com, linkedin.com/in/jlee-example, github.com/jlee-example, trailmix.example.com,
  queryline.example.com

## Education

- Pacific State University, B.S. Computer Science, June 2024. GPA 3.6/4.0 (fine to show).
- Dean's list twice. Off the page: Jordan works full time now.
- Coursework worth a line only for a systems variant: operating systems (built a small file system), networking.

---

## Brightline Health — Software Engineer II (Aug 2024 – Present)

**In one sentence:** Brightline runs telehealth clinics; Jordan works on the platform team that owns the patient booking
portal and the clinic scheduling services behind it.

**Scale:** >600K portal visits/month (product analytics). The scheduling service takes ~2M requests/day (Grafana, 30-day
average, Jan 2026).

**Patient portal rebuild (2025)**
- Why: the portal was a static list of links. Patients missed follow-ups and intake forms because nothing told them what
  was due. The VP of Product wanted the portal to be where care happens, not a menu.
- What Jordan did: rebuilt the home page in React/TypeScript as a feed of each patient's own care tasks (book a
  follow-up, finish intake, refill a prescription). Worked directly with the heads of Product and Design on what the feed
  should be. Led the frontend; the data came from Jordan's GraphQL service. Ran the A/B test with analytics.
- Result: A/B tested, then shipped to all patients. Post-visit survey: >80% positive ratings on the new portal, against
  61% for the old one.
- Status: shipped to everyone.

**Self-serve scheduling service (2025)**
- Why: clinic managers couldn't change their own hours or visit types. Every change was a ticket, then an engineer edited
  config and shipped it in the next day's release.
- What Jordan did: designed and built a Node.js/GraphQL service in front of the existing clinic database, plus the admin
  screens. The clinic database already existed (owned by another team). Jordan did NOT build it.
- Result: a schedule change takes ~2 minutes instead of a next-day engineering release (Jordan timed five changes with two
  clinic managers). Availability lookups all go through this service: ~2M requests/day.
- Who couldn't do what before: nobody outside engineering could change a clinic's schedule, at any clinic.

**AI design-to-schema workflow (2026)**
- Why: every new intake form needed a JSON schema, field documentation and API types written by hand from the Figma
  design, and each team did it differently.
- What Jordan did: built the end-to-end agent workflow: takes the Figma design, proposes the form schema, writes the field
  docs, then generates the matching API types; a person reviews each step.
- Adoption: used across Brightline's product teams; it's now the standard way to add a form. Jordan gave a talk on it at
  the engineering all-hands (a clause at most, not its own bullet).

**Production and on-call**
- Took new microservices to production on Brightline's AWS Kubernetes platform: API gateway routes, Grafana dashboards,
  metrics, logs, alerts. Wrote the runbooks. In the on-call rotation now (1 week in 6). Present tense on the page.
- A past interviewer asked ten minutes of follow-ups on this bullet and liked it. Keep it.

**Slot holds in the booking service (2026): the hardest work of the year**
- What was hard: two patients could book the same provider's slot at once, because availability was read and written in
  separate steps across services owned by three teams. It caused double-bookings only under load, so it took two weeks of
  log tracing to reproduce.
- What Jordan did: designed and built slot holds in the shared booking service with Redis locks. Wrote the design doc,
  aligned the three teams on a reservation API, and rolled it out behind a flag.
- Result: double-bookings stopped. Finance projects $1.2M a year in visits kept (a projection, not measured revenue).

**Smaller things, not on the page:** dark mode for the portal; a Storybook for the shared components; moved the team's
tests from Jest to Vitest.

**People:** heads of Product and Design, the analytics team, two clinic operations managers.

**Do not claim:** built the clinic database; led the team (Jordan is one of four engineers).

---

## Northgate Aerospace — Software/ML Engineer, Sponsored Capstone (Jan 2024 – Jun 2024)

- A company-sponsored senior capstone at Pacific State. Northgate gave the team live satellite data and a real user: county
  fire dispatchers, who are understaffed and watch feeds by hand.
- What it is: a real-time wildfire-detection system. It ingests live satellite thermal feeds over California (900+
  frames/min), scores each frame in ~40 ms, and flags new fires on a map.
- What Jordan did: the ingestion pipeline and the map backend, then trained the PyTorch U-Net (94.2% recall on the test
  set Northgate held out) and added Grad-CAM heatmaps that show why each region was flagged. Dispatchers wouldn't trust a
  bare alert.
- Recognition: 1st place of 60 teams at the senior showcase; presented to Northgate's engineering directors.
- Do not claim: deployed in production at Northgate (it ran on live data, but as a demonstration).

---

## Cartwheel Payments — Software Engineer Intern (Jun 2023 – Aug 2023)

- Why: support agents answered "where's my payout?" by reading raw bank files; each ticket took hours.
- What Jordan did: rebuilt the payout-investigation tool alone, with FastAPI and a Python ETL job that syncs 8M+ bank records
  nightly.
- Result: ticket resolution time fell 60% (support dashboard, four weeks before and after). Company-wide support onboarding
  now links to it.

---

## Lumen Learning — Software Engineer Intern (Jun 2022 – Aug 2022)

- Lumen is a Bay Area edtech startup. Jordan built the frontend for a responsive study-planner web client: CRUD workflows
  and REST API integration. No results to speak of. A minor entry: one plain line.

---

## TrailMix — Co-founder & Software Engineer (side project, 2025)

- A mobile safety app for backcountry hikers: offline maps, closure alerts, trip check-ins.
- 12K monthly users five months after launch (analytics). No revenue.
- Jordan led engineering and one intern. Built it full stack: an offline-first sync engine with conflict resolution (hikers
  edit trips with no signal), a multi-tenant Postgres backend with PostGIS search, and signed iOS and Android builds through
  a GitHub Actions CI/CD pipeline.

## SiteForge — open-source static-site generator (Rust, Python)

- Merged Rust concurrency fixes to the incremental build cache: a data race and a use-after-free in unsafe code. Both merged,
  checked on GitHub Jan 2026.
- Wrote Python regression suites and verified the fixes under Miri and ThreadSanitizer.

## Queryline — searchable knowledge base (side project)

- Answers from internal wikis for AI agents. Hybrid search combining pgvector embeddings and BM25 keyword ranking, with an
  MCP server for search and versioned writes. Python/FastAPI, React/TypeScript, PostgreSQL/pgvector. A few friends' teams
  tried it; no adoption worth a number.

---

## Skills

- Used for real: TypeScript, JavaScript, Python, Rust, SQL, React, React Native, Node.js, GraphQL, FastAPI, Kubernetes,
  Docker, PostgreSQL, Redis, Grafana, CI/CD, Git, PyTorch.
- Coursework only: C, Java.
- Do not list: Go, Terraform (could not defend either in an interview).

## Interview log

### 2026-02-10
- Q: What does the >80% measure?
  A: The post-visit survey question on the new portal, against 61% for the old one.
- Q: Did you build the clinic database?
  A: No, another team owns it. I built the service and the admin screens in front of it.
- Q: What was the hardest thing you did this year?
  A: The double-booking bug. It only happened under load, and the fix needed three teams to agree on one API.
- Q: What did past interviewers ask the most about?
  A: The on-call setup and the slot holds.
