# Resume playbook

How to write a one-page resume that the screening software can read, a non-technical recruiter can understand in
thirty seconds, and an engineer still respects. Every rule here came out of a week of line-by-line work on a real
resume (the [case study](CASE_STUDY.md)), and most of them came from a correction: a draft that got rejected, and
the reason why. The evidence behind the rules is in [EVIDENCE.md](EVIDENCE.md).

Examples in this file use fictional people and companies. The edits and the reasons are real.

---

## Who reads your resume

Three readers, usually in this order. A bullet has to work for all three at once.

| Reader | What it does | What it needs from you |
|---|---|---|
| **Software** (the ATS, and now AI matchers such as Greenhouse Talent Matching and Ashby's review) | Extracts your text, fills your profile, lets recruiters search it, sorts applicants against the job's criteria. Matches skills by meaning, not by counting words. Does not reject you by itself. | Text that extracts cleanly, standard section names, and the real names of the things you used (React, Kubernetes), inside sentences. |
| **The recruiter** | Skims for 7 to 30 seconds. Often not an engineer. Often holding a keyword list from the hiring manager. Looks at company names, titles and the first bullet or two of each job. | A recognizable employer and title, the best result where the eye lands, and plain words that say what you built and why it mattered. |
| **The hiring manager** | Reads the bullets that survived the skim, then interviews you on them. | Real engineering: the system, its scale, your part, the hard part. Nothing you can't talk about for ten minutes. |

The case study's turning point was accepting that the first reader is not a senior engineer who can fill in what a
bullet leaves out.
Drafts written for an engineer read like jargon to the recruiter; drafts written for the recruiter read like
nothing to the engineer. The fix is one sentence that does both.

---

## The bullet formula: what, how, why

**What you built or changed** (a noun a stranger recognizes) **+ how** (the technologies, inside the sentence)
**+ why it mattered** (who it was for, what changed, how big).

> Built the Node.js/GraphQL service that lets clinic staff change their schedules (~2M requests/day), so a schedule
> change takes **~2 minutes instead of a support ticket and a next-day release**

- What: a service that lets clinic staff change their schedules. A recruiter can repeat that.
- How: Node.js/GraphQL. The keywords are there, in context, not dumped.
- Why: ~2 minutes instead of a ticket and a release. Scale: ~2M requests/day.

A list of tools with no purpose fails, even when every tool is one the posting asks for:

> ✗ Deployed and operated the service on the managed Kubernetes platform, configuring namespaces, environments,
> service-mesh routing, Grafana dashboards, alerts, and on-call support.

That is a setup checklist. The reader learns you touched Kubernetes and learns nothing about what it was for.
In the case study, proposals like this were rejected as keyword slop: the goal was for anyone reading a bullet to
understand what was done and why.

### Five tests for every bullet

1. **The repeat test.** Could a recruiter who isn't an engineer say back what you built and what it was for?
2. **The interview test.** Could you talk about it for ten minutes, including how each number was measured?
3. **The scope test.** Does it claim only your part? ("Added X through a service" when you built one layer, not
   "built the platform".)
4. **The skim test.** Is the best result visible, with its contrast right next to it?
5. **The stranger test.** Is every name one an outsider knows? Internal service names, team names and acronyms fail.

`python3 -m jobhunt resume` runs automatic versions of some of these (weak openers, no purpose or number, more than
one bold, keyword stuffing, first person, your banned phrases and internal names) and reports them as `style`
warnings. A person still decides.

---

## The rules, and why each one exists

### Content

**1. Interview first, draft second.** The resume is built from an inventory of facts collected by asking you
questions, not from your old resumes and not from guesses. In the case study, four rounds of bullets were rejected
before the AI stopped guessing and started asking; the person said they had all the information for a perfect
resume, they just didn't know what was needed. Ask everything missing in one numbered list: why it was built, who
used it, your part, the result from what to what, the plain meaning of every internal term.

**2. An answer is raw material, not an instruction.** Something you said in the interview does not automatically
belong on the page. Collect the facts, then choose what earns a place.

**3. Say why.** Every bullet carries its reason: the problem before, who it helped, what it made possible.

**4. Name the system and its scale.** "~250K bookings/month", "~2M requests/day", "8,000+ documents". Scale tells a
recruiter the work was real without needing to understand it.

**5. Put the best result where the skimmer looks, and keep its contrast next to it.**
> ✗ ...enabling Operations to publish changes in minutes and configure tests independently, replacing a 1–2 day
> engineering release cycle
>
> ✓ ...enabling Operations to make layout and content changes in **~3 minutes, replacing a 1–2 day engineering release**

When "~3 minutes" is six words away from "1–2 days", the contrast is lost. Keep the exact number too: "in minutes"
was rejected for "~3 minutes".

**6. Your real scope, in your own words.** The case-study candidate built the GraphQL layer that connected a
company's portal to an existing CMS. A draft said "Built the portal's CMS platform," which reads as if they had built
the entire CMS. The final wording: "Added CMS capability to the carrier portal through a Node.js/GraphQL service." Precise scope is also the honest scope, and it survives the
interview.

**7. Don't diminish your best work.** Words like "prototype" and "built the backend" undersell. The case study's
strongest project was a sponsored capstone; drafts called it a prototype and put the university on the employer
line. The final version names the sponsor as the employer, says what the system does and who it is for, and keeps
the numbers the person could explain.

**8. Never drop a number without asking what it measures.** "Performance improved 20%" was cut from a draft for
having "no baseline." It had one: Lighthouse scores against the old site. The person was right to be angry: a number
from your own work is not invented just because the AI doesn't know what it means. Ask. Then keep it, reword it, or
drop it with the person's agreement.

**9. Don't re-ask settled facts.** Once a number or status is confirmed (">70% positive ratings", "projected
$1.5M", "merged in March"), record it in `decisions.md` under "Fixed facts" and stop questioning it.

**10. Exact status.** Achieved vs projected ("supports a projected $1.5M"), shipped vs A/B tested, merged vs in
review, "not instant end to end" when a background job takes an hour. If a status might change (a PR in review),
use wording that is true either way ("Contributed fixes"), then update it when it changes.

**11. Leave out what doesn't impress the reader.** Team size ("two-person team"), internal process ("needed
senior-director approval"), raw counts that sound small ("107 test cases"), the number of users in an A/B test,
"5 more teams are adopting it", "all but two" of anything. None of these make a reader think better of you, and some
make them wonder.

**12. No filler.** Rejected in the case study: "increasing developer velocity", "feels instant", "required",
"modules", "Existing". Also avoid the stiff verbs recruiters now read as AI: spearheaded, leveraged, utilized,
orchestrated. Plain verbs (built, rebuilt, fixed, added, cut) read as a person.

**13. Name things; don't point back with "its."** A bullet that starts "Built its backend" leans on the bullet above
it. Name the system again or merge the bullets.

**14. Don't overfit to one posting.** The candidate mentioned on-call runbooks because one posting asked for them;
the AI rewrote a whole bullet around runbooks. Add a posting's word only where it fits the work cleanly.

**15. Keywords belong where they are true.** Count which technologies the roles you want actually ask for (in the
case study, React, TypeScript and Python led across 57 well-matched postings; "full stack" appeared at 8 of 11
companies; monitoring/on-call at 7 of 11). Then make sure the ones you really used appear in bullets. Never add one
you didn't use. A skill you can't defend in an interview is a liability.

**16. Bold one thing per bullet, at most.** The item a skimmer should catch: the main technology or the headline
result. Unbold anything that doesn't stand on its own ("8,000+ documents", "$1.5M", a secondary language).

### Structure

**17. About two lines per bullet: one for what, one for why.** Splitting two-line bullets into one-liners was tried
and rejected: each half lost either the what or the why. No study compares one- and two-line bullets; Huntr's
guidance is 3 to 5 bullets per role at 150 to 200 characters (the final case-study resume averaged 196). Vary them a
little so the page isn't one block.

**18. Order bullets by strength and by what recruiters scan for.** The strongest, most recognizable work first:
the biggest result with the most-asked-for stack (React/TypeScript) led, the AI workflow came second, and the
backend service with less-asked-for keywords (GraphQL) came third. The AI workflow had been buried at the bottom;
it moved up.

**19. One page, one column, filled.** The builder fits your content to exactly one page by adjusting font size and
spacing within readable limits, and fails loudly if it can't. Wider gaps between bullets were added after the first
build read like one big paragraph.

**20. No summary.** The evidence for summaries is thin, and it costs three lines of real work.

**21. Skills: two lines, only what you can be questioned on.** No "AI coding tools" line (rejected as keyword
filler: everyone uses them; it belongs in an interview answer). Remove anything you haven't really used (the
candidate removed AWS). Drop trivia a hiring manager won't care about (a specific backend-as-a-service brand).

**22. Header: name, phone, email, LinkedIn, GitHub, and citizenship only if it matters.** No city: a non-local city
gets you filtered out by location searches, and you may want to relocate. Email, LinkedIn and GitHub are clickable in
the PDF and visible as plain text (recruiters click; parsers read the text). "U.S. Citizen" goes in the header when
you target defense, space or other export-controlled (ITAR) work; elsewhere it tells a skimmer no sponsorship is
needed.

**23. Your employer's brand is a signal.** Keep the company name and your title clean and visible on their own line.
For a sponsored project, put the sponsor on the employer line and say "Sponsored Capstone" in the title.

**24. A startup goes under Projects for big-company applications.** A field experiment (Botelho & Chang) sent 2,400
applications for entry-level software jobs: former founders got about 43% fewer callbacks. Title it
"Co-founder & Software Engineer", make the bullets about what you built and for whom, and use one founder label only.
A startup-facing variant can move it up.

**25. No dates on projects.** They added nothing and raised questions.

**26. Keep a weak internship as one line rather than cutting it**, if the page has room: it shows another real job.
It is the first thing to cut when space runs out.

**27. GPA on one line; drop the honors list** once you have a full-time job.

**28. Don't make two projects say the same thing.** If one project already shows MCP and agents, use the other
project's bullets for something else it uniquely shows (a desktop app, a release pipeline, paying users).

### Format and ATS safety

The builder (`jobhunt/resume.py`) enforces these on every build:

- Text-based PDF printed by Chrome (the same engine family as Google Docs exports), Times New Roman, kerning and
  ligatures off so every word extracts with its spaces ("forAction" and "onAWS" were caught before this).
- Plain ASCII hyphens and spaces. AI tools emit non-breaking hyphens (U+2011) and narrow no-break spaces (U+202F)
  that break exact-phrase search and some importers. Earlier resumes in the case study had U+2011 inside the phone
  number and LinkedIn URL.
- Every bullet, title and skills line must extract word for word; contact details must parse; the name must be the
  first line.
- No orphan words: a bullet whose last line is under 30% of the width gets flagged with how many characters to cut.
- Ship only when the build says `status: ok` with empty `lint` and `short_last_lines`.

---

## One resume, not one per job

Per-job AI tailoring was the case study's previous approach: about 100 applications with a freshly tailored resume
each, zero human callbacks. One simple general resume had earlier gotten a final-round interview. The research
agrees on why: once AI made tailoring free, employers stopped rewarding it (Galdin & Silbert), and hiring managers
report distrust of AI-sounding applications.

What to do instead:

- **A few role-family variants**, each fully polished by you: for example `general` (full-stack, product,
  platform), `systems` (embedded, C/C++, autonomy), `ai` (LLM and agent tooling). Variants reorder projects and
  skills, drop an entry, or add a supporting project. They never get new wording per posting.
- **Choose the variant by what the posting asks, not by the company.** A web role at a defense company gets the
  general resume. In `profile.yaml`, `posting_must_mention` makes this automatic.
- **Never swap a strong project for a weak one that hits keywords.** A shipped product with paying users beats a
  class project, even on an embedded posting. The class project can appear as one supporting line on the variant that
  needs it ("has this person written code close to hardware at all?").
- **The one safe per-job edit is reordering the skills lines** so the posting's must-haves come first
  (`--emphasize "C++,Python"`). It never adds a skill.
- **No per-company copies.** They go stale. One PDF per variant.

---

## Numbers

- Use a number when you know what it measures, from what to what, and can explain how it was measured.
- Round to what you actually measured ("~2M requests/day", ">70% positive ratings"). A precise figure is fine when it
  is the reported result of a defined test and you can explain it.
- When there is no business metric, use honest proxies: scale (requests, users, documents), adoption (teams using
  it), speed (minutes instead of days), reliability (incidents, tickets), scope (owned end to end, replaced the old
  system).
- If a recruiter could reasonably ask "of what?", answer it in the bullet or pick another number.

---

## Working on it with an AI

The resume workshop skill follows this process. It is the part most people skip, and it is why the result reads as
yours.

1. **Interview** for the facts. Save every answer, dated, in `inventory.md`.
2. **Count keywords** in current postings you would apply to, so you know which true skills to make visible.
3. **Propose in chat; wait for a yes; then edit.** At the fine-tuning stage, no test PDFs, no "trial" files and no
   working ahead. A rendered file with changes in it looks like a change, whatever the AI says about it being a test.
4. **One bullet at a time.** Offer several wordings (ten, if asked) and let the person pick and adjust. Most final
   bullets in the case study are the person's own wording, tightened.
5. **When a part has to go to fit, keep one bullet and drop the least important part.** Don't split a story into two
   bullets to avoid choosing.
6. **Check every claim against the inventory before building.** Every overclaim that slipped in was caught this way.
7. **Get outside reviews, then judge them.** Paste a review from another model or person, and have the AI push back
   with evidence where the review is wrong. Give the reviewer the latest version, not an old one.
8. **Keep an editable copy the person can change** (a doc, not YAML), and sync the source to it.
9. **Record every decision and rejected wording** in `decisions.md`, so nobody argues the same point twice.
10. **Build, run every check, and read the PDF once as a recruiter would.**

---

## Before you send it

- [ ] Every claim is in `inventory.md`, and you can talk about each bullet for ten minutes.
- [ ] Each bullet passes the repeat, scope, skim and stranger tests.
- [ ] The build says `status: ok`, `lint: []`, `short_last_lines: []`; you've read the `style` warnings.
- [ ] The PDF's text pasted into a plain editor reads in the right order with no odd characters.
- [ ] The file is named `First_Last_Resume.pdf`.
- [ ] You are sending the right variant for what this posting asks for.
