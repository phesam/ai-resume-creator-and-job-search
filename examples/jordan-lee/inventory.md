# Work and accomplishments inventory: Jordan Lee (fictional example)

A filled-in example of `workspace/inventory.md`. Jordan, the companies and the numbers are invented; the shape of
each entry is what a useful inventory looks like. The resume built from it is `templates/resume.yaml`.

## Basics

- Work authorization: U.S. citizen. No clearance.
- Wants: Southern California or remote; open to the Bay Area for a strong role.
- Links: jordan.lee@example.com, linkedin.com/in/jlee-example, github.com/jlee-example, trailmix.example.com

## Education

- Pacific State University, B.S. Computer Science, June 2024. GPA 3.6/4.0 (fine to show).
- Coursework worth a line only for a systems variant: operating systems (built a small file system), networking.

---

## Brightline Health — Software Engineer (Aug 2024 – Present)

**In one sentence:** Brightline runs telehealth clinics; Jordan works on the team that owns appointment booking for
patients and scheduling for clinic staff.

**Scale:** ~250K bookings/month (product analytics dashboard). The scheduling service takes ~2M requests/day
(Grafana, 30-day average, Sep 2025).

**Booking flow rebuild (2025)**
- Why: the old flow was five pages; patients dropped off before confirming. Support heard "I couldn't find a time"
  daily.
- What Jordan did: rebuilt the flow in React/TypeScript as one page with live availability; worked directly with the
  Product lead and the Design lead; ran the A/B test with the analytics team.
- Result: abandoned bookings fell from 31% to 19% in a four-week A/B test (50/50 split, product analytics); shipped to
  everyone afterwards.
- Status: shipped to 100%.

**Clinic scheduling service (2025)**
- Why: clinic staff couldn't change their own schedules or visit types; every change was a support ticket, then an
  engineer edited config and shipped it in the next day's release.
- What Jordan did: designed and built a Node.js/GraphQL service and the admin screens on top of it; the clinic data
  model already existed (owned by another team). Jordan did NOT build the clinic database.
- Result: a schedule change takes ~2 minutes in the admin screen instead of a ticket and a next-day release
  (measured by Jordan timing five changes with two clinic managers).
- Scale: ~2M requests/day (patients' availability lookups go through it).

**AI design-to-schema workflow (2026)**
- Why: every new booking form needed a JSON schema, field docs and TypeScript types written by hand from the design;
  teams did it differently.
- What Jordan did: built an agent workflow: give it the design mockup, it proposes the form schema, writes the field
  docs, then generates the API types; a person reviews each step.
- Adoption: three product teams use it; it's the standard way to add a booking form (not required, but every PR in
  the last two months used it).

**Production and on-call**
- Took both booking services to production on the company's Kubernetes platform: gateway routes, Grafana dashboards,
  logs, alerts; wrote the runbooks; in the on-call rotation (1 week in 6).

**Time-zone bug (2025)**
- What: patients saw appointment slots that no longer existed after daylight-saving changes; caused double bookings.
- What Jordan did: found the bug (slots computed in server time, not clinic time), fixed it, added regression tests
  that run across DST boundaries.
- Result: double-booking support tickets went from ~40 a week to 2 (support dashboard, four weeks before vs after).

**People:** Product lead, Design lead, the analytics team, two clinic operations managers.

**Do not claim:** built the clinic database; led the team (Jordan is one of four engineers).

---

## Pacific State University, Autonomy Lab — Research Assistant (Sep 2023 – May 2024)

- The lab runs a small delivery robot around campus for mapping research.
- Why: researchers re-drove routes whenever they needed new data, because runs weren't recorded in a replayable form.
- What Jordan did: built a ROS 2 logging pipeline in Python that records the robot's camera, lidar and GPS streams;
  300+ hours of runs were recorded and labeled with it (lab dataset index).
- Also wrote a C++ ROS 2 node that flags dropped sensor frames while the robot runs; while testing it, found that a
  clock-sync bug had misaligned timestamps in 12% of earlier recorded runs (lab audit), and fixed it.
- The lab's mapping paper used the cleaned dataset. Jordan is acknowledged, not an author.
- Do not claim: co-author; designed the robot.

---

## Cartwheel Payments — Software Engineer Intern (Jun 2023 – Aug 2023)

- Built an internal Python tool that matches failed merchant payouts to bank error codes.
- Why: support agents answered "where's my payout?" tickets by reading raw bank files; it took hours per ticket.
- Result: the support team used it daily; answers took minutes instead of hours (support lead's estimate; no
  dashboard).

---

## Lumen Learning Labs — Software Engineer Intern (Jun 2022 – Aug 2022)

- Lumen makes a study app for college students; the web app is built from a shared React component library.
- Why: a district customer required a WCAG AA accessibility audit, and the app failed its first check.
- What Jordan did: added automated accessibility checks (axe) to the component library's CI, then fixed what they
  found; the checks caught 140+ contrast and labeling bugs before release (CI history), and the app passed the audit.

---

## TrailMix — Founder & Software Engineer (side project, 2025)

- A trail-conditions app: hikers post closures and mud reports.
- 1,200 monthly active users after four months (analytics), grown through two local hiking clubs. No revenue.
- Built alone: React Native client that caches reports for offline reading (no signal on trails), Node.js API on
  PostgreSQL with PostGIS distance search, nightly backups.

## Open source: a static-site generator (Rust)

- Merged a caching fix that skips unchanged pages on rebuild. Maintainers merged it in March 2026.
- Benchmark in the PR: a 5,000-page site rebuilt in 24 s instead of 41 s.
- The project has about 2K GitHub stars.

---

## Skills

- Used for real: TypeScript, JavaScript, React, React Native, Node.js, GraphQL, PostgreSQL, Python, C++ (lab),
  ROS 2 (lab), Kubernetes, Docker, Grafana, CI/CD, Git, Rust (one merged contribution).
- Coursework only: C, Java.
- Do not list: AWS (the company runs its own platform), Go.

## Interview log

### 2026-02-10
- Q: What does the 31% → 19% measure?
  A: Share of patients who started a booking and didn't confirm, A/B test over four weeks, product analytics.
- Q: Did you build the clinic database?
  A: No, the clinic platform team owns it. I built the service and the admin screens on top.
