# Resume playbook

How to write a one-page resume that screening software can read, a recruiter can follow in thirty seconds, and an
engineer respects. Every rule here came out of a week of line-by-line work on a real resume (the
[case study](CASE_STUDY.md)), and most came from a draft that got rejected. The evidence is in
[EVIDENCE.md](EVIDENCE.md).

Examples use a fictional person. The sentence shapes, the edits and the reasons are real.

---

## What a finished page looks like

These numbers were measured on the finished case-study resume, from someone with over a year of full-time work. They
describe what done looks like at that level or above. They aren't a target to pad toward: when the inventory can't reach
them honestly, interview for more.

| | A finished page |
|---|---|
| **Fill** | Text runs to the bottom margin. No blank band, ever. |
| **Body text** | 10.5–10.9pt. A page that only fills at a bigger size isn't finished. |
| **Lines of text** | About 54. The build fails a page with a blank band at its roomiest layout, usually around 50 lines |
| **Entries** | 6–8: every substantial job and project is on the page |
| **Bullets** | 13–15: about 5 on the newest job, 2 on the next big entry, 1–2 on the rest, one bare line for a minor entry |
| **Bullet length** | About 195 characters on average. Nearly all run into a second line; 225 at most. A line holds about 108 characters |
| **Technical depth** | About three distinct technical terms per bullet |

The build enforces fill and text size, and reports the rest under `fill`. `status: underfull` means the page isn't done,
and it says how many lines are missing. [`examples/jordan-lee`](../examples/jordan-lee) is a page at this density.

**Early in a career, the page still fills, but bullets are only as long as the facts.** Interview first: people forget
most of what they did. A new graduate's page then fills with internships, teaching, real projects, honors and coursework,
and more entries with shorter bullets is the honest shape. Stretching a small project to 195 characters is padding.

**When it's done:** the page is full, the build says `ok`, and the interview has nothing left. Say plainly where it falls
short of the table and why, then stop. If it still can't fill, tell the person how many lines are missing and let them
decide. A short, honest page beats a padded one.

---

## Who reads it

Three readers. A bullet has to work for all of them at once.

| Reader | What it does | What it needs |
|---|---|---|
| **Software** (the ATS, and AI matchers such as Greenhouse Talent Matching) | Extracts your text, fills your profile, sorts applicants against the job's criteria. Matches skills by meaning. Doesn't reject you by itself. | Clean text, standard headings, the real names of what you used, inside sentences. |
| **The recruiter** | Skims for 7 to 30 seconds. Often not an engineer. Often holding a keyword list. Reads company names, titles, and the first words of bullets. | A recognizable employer and title, the best result where the eye lands, and an opening clause that says plainly what you built. |
| **The hiring manager** | Decides. Reads every bullet, then interviews you on them. | Real engineering: the named system, its scale, your part, the hard part. |

**The default reader of a bullet is the engineer who decides. You serve the recruiter through word order, not by
simplifying.** The plain "what" goes in the opening clause. The technical substance stays after it.

Getting this backward is the most damaging mistake an AI makes here. In the case study, the week went like this: plain
one-liners simplified for a skimmer were rejected as embarrassing. A dense, technical draft modeled on a strong peer's
resume was the first one that worked. Fitting that to two lines and adding the "why" came next. The finished page is the
dense draft plus the why, not a simplified version of it.

**A simplified bullet is a failed bullet, even when it's clear.** It reads as work on a single web page.

---

## The bullet: what, how, why

**What you built or changed + how (the stack, inside the sentence) + why it mattered (who it's for, what changed, how
big).** Someone should be able to read a bullet and say what you did and why. Keywords belong inside a sentence that has
a reason in it.

### Shapes that work

Use these as patterns and vary them. A page of one shape reads as generated.

**(a) Thing (scale) in stack with senior partners as what it became; tested, shipped, reception.**
> Rebuilt Brightline's patient booking portal (>600K visits/month) in **React/TypeScript** with heads of Product and
> Design as a personalized feed of care tasks; A/B tested, then shipped to all patients with >80% positive ratings

**(b) Capability added through a stack (scale), enabling whom, result, replacing what.** Lead with what didn't exist
before, at the level of the organization, not the one page where it first appeared.
> Added self-serve scheduling to Brightline's clinic platform through a Node.js/GraphQL service (~2M req/day), enabling
> clinic managers to change hours and visit types in **~2 minutes, replacing a next-day engineering release**

**(c) Concrete thing built in a named place, the failure it fixed and how; business stake labeled honestly.** The hardest
work goes here.
> Designed and built slot holds in the shared booking service with Redis locks, aligning three teams on a reservation
> API and fixing a race condition that double-booked providers; supports a projected $1.2M in visits

**(d) System for a named sponsor: three verbs with a number on each.** "Live" tells the reader it was real.
> Built a real-time wildfire-detection system for Northgate Aerospace: ingests live satellite thermal feeds over
> California (900+ frames/min), scores each frame in ~40 ms, and flags new fires on a map for understaffed dispatchers

**(e) The production-ownership bullet: a colon list.** One bullet may be a list of what you set up, because it proves a
cluster postings ask for and you really do it. Don't invent a purpose for it; a tacked-on clause reads worse. To shorten
it, trim the weakest item.
> Deployed new microservices on Brightline's AWS **Kubernetes** platform: set up API gateway routes and monitoring
> (Grafana dashboards, metrics, logs, alerts); created runbooks and provide on-call support

**(f) Open source proves itself** by naming the failure classes and how the fix was verified. It needs no metric.
> Merged **Rust** concurrency fixes to SiteForge's incremental build cache (a data race, a use-after-free in unsafe
> code), with Python regression suites verified under Miri and ThreadSanitizer

### What fails

> ✗ Worked on backend APIs and helped migrate services to the cloud.

A task description. No system, no scale, no reason.

> ✗ Developed scalable microservices leveraging Node.js, GraphQL, Kafka, Redis and Kubernetes to drive developer velocity.

Keyword slop: tools with a vague purpose stapled on.

> ✗ Built the app people use to book a doctor, so they can get care faster instead of calling the clinic.

Clear, and worthless to an engineer. This is the simplified failure: a reader learns nothing about the work.

### Seven tests for every bullet

1. **Repeat.** Could a recruiter say back what you built and what it was for? Cover the second half of the bullet: the
   first half alone must make sense.
2. **Engineer.** Would a senior engineer at a target company see real work, or a description of a task? Point to the
   named system and the engineering inside it (architecture, integration, decision, failure handled). If you can't, ask
   for more and rewrite.
3. **Impressed.** Would a stranger be impressed, or just informed? If only informed, it needs a stronger claim, a harder
   problem or more reach.
4. **Owner.** The person reads it back, recognizes their own work, and can explain every term and defend it for ten
   minutes, including how each number was measured.
5. **Scope, both ways.** It claims only their part ("added X through a service", not "built the platform"), and it doesn't
   undersell (would a reader guess this was one page when it was platform-wide?).
6. **Skim.** The best result is visible, with its contrast right beside it. "~2 minutes, replacing a next-day release"
   works. Six words between them kills it.
7. **Private names.** No internal service, team or product names. Public engineering terms stay, even when a recruiter
   won't know them and no posting names them. Stripping public terms strips the depth.

`python3 -m jobhunt resume` checks some of this automatically and reports `style` warnings. A person still decides.

---

## The rules, and why each exists

### Scope and framing

1. **Interview first; draft second.** The resume comes from an inventory of facts, gathered from what you already have
   and then by asking. Four rounds of bullets were rejected in the case study before the AI stopped guessing.
2. **An answer is raw material, not an instruction.** Collect the facts, then choose what earns a place.
3. **Guard against underclaiming as hard as overclaiming.** Frame work at its true scope: platform-level when it was,
   not the one page where it first appeared.
4. **Lead the strongest bullet with what didn't exist before.** Say who couldn't do what, at what level of the
   organization.
5. **Know why it mattered before wording it.** If you can't say in one sentence why the work mattered to the
   organization, ask. Don't reword around the gap.
6. **Say concretely what the beneficiary can now do,** naming the actions, not a vague word like "changes", and whose old
   process it replaced.
7. **Every clause shows what the candidate did.** Delete each clause in turn: if their credit is unchanged, it's a
   floating fact. Tie it to them or cut it.
8. **Show the thing made, its breadth and its impact.** Breadth means who beyond their own team uses it.
9. **Make reality explicit.** Say it ran on live data, real traffic, real users or in production. Otherwise a project
   reads as a class exercise.
10. **Your real scope, in your own words.** One layer in front of an existing system is "added X through a service."
    Precise scope survives the interview.
11. **Don't diminish your best work.** "Prototype" and "built the backend" undersell. A sponsored project names the sponsor
    on the employer line and in the title ("Sponsored Capstone"), and says what the system does and for whom.
12. **The bullets of one job read as one connected story:** what it is, how it was built, what it changed. No bullet depends
    on one below it.

### Sentence craft

13. **Concrete nouns beat process words.** Name the component, the failure, the behavior. "Design doc" and "aligned teams"
    may accompany the concrete thing, never replace it.
14. **Open with a strong noun phrase:** a scope word plus an input-to-output shape ("turns A into B"). The first bullet of
    the first job has the highest bar: it must read the cleanest on the page.
15. **Choose the verb by the size of the change.** Fix, add, build, rebuild and redesign mean different things.
16. **Claim ownership when true:** "designed and built", "led", "owned". Plain doesn't mean modest. Ongoing duties take the
    present tense ("provide on-call support"), finished work the past.
17. **Don't upgrade a plain true word.** If it was a dialog, write dialog. Nothing a person wouldn't say out loud.
18. **Read every bullet aloud.** Reject awkward or resume-voice phrasing even if no rule names it.
19. **Grammar agreement in lists.** Every item after a verb must work with that verb; each clause after a semicolon has its
    own verb; paired items take the same form. Things are built *with* a framework and written *in* a language.
20. **Don't write what the verb implies.** A finished thing is assumed live unless rollout carries a result ("A/B tested,
    then shipped to all"). Keep short reach words ("company-wide") when true: they carry scale cheaply.
21. **Keywords are not adjectives.** Don't insert a technology to score a match.
22. **Fix a correction by changing the claim,** not by adding a defensive qualifier that reads strangely.
23. **"Its" needs its name on the line above.** "Built its backend" in a separate entry leans on nothing. "Trained its model"
    directly under the bullet naming the system is fine.
24. **No filler:** "increasing developer velocity", "feels instant", "various", and the stiff verbs recruiters read as AI
    ("leveraged", "spearheaded", "utilized", "orchestrated"). Also avoid repeating one shape: several bullets ending
    ", so ..." or "instead of ..." reads as generated.

### What goes on the page

25. **Every substantial job and project goes on the page first.** A page isn't done until they're all there and the page is
    full. Then choose what to cut, if anything.
26. **Never trade a strong entry for a detail.** No substantial entry gets cut to pay for a count or a line of trivia.
27. **Put in-demand work under the strongest employer,** near the top, not only in projects, when true.
28. **The hardest work gets its own interview pass and a bullet that shows it.** If they say it was hard and the bullet reads
    weak, dig deeper before cutting. A real bug or race condition is engineering a manager respects.
29. **When a clause is weak, ask what it took.** Replace it with what you learn instead of rewording it.
30. **Ask what past interviewers praised, and protect it** from later cuts.
31. **Name senior partners and cross-team alignment.** "With heads of Product and Design" and "aligning three teams" show you
    work with others. That's not trivia. Trivia is team size, approval steps, raw counts that sound small ("107 test cases"),
    and how many users were in an A/B test.
32. **A talk, award or adoption note is a clause on the work it belongs to,** never its own bullet.
33. **Don't dress repeat work as a design win.** Easy repeat work gets a plain clause or merges into another bullet.
34. **Leave out what signals the wrong thing:** baseline practice listed as an achievement, implementation details that read
    as naive to an engineer, and skills for work you don't want to do.
35. **No identifiers or inventories in bullets:** no pull-request or ticket numbers, no feature lists.
36. **For a big project, build a menu first.** List everything the person did, with their share of it, and let them choose. A
    broad product gets a breadth bullet, not one small feature. Never leave out shipping and release work.
37. **Don't make two projects prove the same thing.**
38. **A startup goes under Projects for big-company applications,** titled "Co-founder & Software Engineer". A field
    experiment (Botelho & Chang) found former founders get about 43% fewer software-engineering callbacks. A startup-facing
    variant can move it up.
39. **Sweep older resume versions once before finalizing,** for anything stronger than the current page.

### Numbers

40. **Never drop a number without asking what it measures.** "Performance improved 20%" was cut for having no baseline; it had
    one. A number from your own work isn't invented because the AI doesn't know what it means.
41. **Exact status.** Projected vs achieved, shipped vs A/B tested, merged vs in review. Check merge status before claiming it.
    If it might change, use wording true either way.
42. **One scale number per story.** A second of the same kind adds nothing.
43. **Don't name the measuring tool when the plain metric reads fine.** "Performance improved 20%" passes. Keep the tool for
    the interview.
44. **Keep the exact number you can explain.** "~2 minutes" beats "in minutes". Don't shave a number you can defend because a
    reviewer finds it odd; do round what you only estimated.
45. **Don't re-ask settled facts.** Record them in `decisions.md` under "Fixed facts".

### Keywords and vocabulary

46. **Count what target postings ask for** (`python3 -m jobhunt keywords --companies "A,B,C"`). It shows which skills you have
    that the page doesn't show yet. Never add one you didn't use.
47. **Put a title keyword in a bullet where it's plainly true,** not only in Skills. Audit Skills in both directions: bullets'
    tools missing from Skills, and Skills items that appear nowhere else, with a reason for each.
48. **Cap repetition.** Past three uses of one tool, swap extras for the broader word postings use (service, API, backend).
    Inside one job, don't repeat a result or prove the same skill twice.
49. **Don't overfit to one posting.** Add a posting's word only where it fits cleanly.

### Length and layout

50. **About two lines per bullet: one for what, one for why.** Splitting into one-liners was tried and rejected: each half lost
    either the what or the why.
51. **Vary where bullets end.** A page where every bullet fills both lines reads as one block. Never pad to fill a line; the
    build flags only a stranded word.
52. **Space is proportional to weight.** A minor entry gets one line. Keep it rather than cut it if the page has room: it
    shows another real job. It's the first thing to shrink when space runs out.
53. **Bold the one thing a skimmer should catch** (two only for two separate results): the main technology or the headline
    result. Unbold anything that doesn't stand alone.
54. **Order bullets by strength and what's in demand.** The biggest result with the most-asked-for stack first; current
    in-demand work (an AI workflow, say) high up, never buried. Don't split one story to get it there.
55. **Wider gaps between bullets, smaller text.** A page with no air reads as one paragraph.
56. **When a bullet won't fit, keep it one bullet and drop its least important part.** Don't split a story to avoid choosing.
    A request to lighten a bullet means cut: remove words and report what left.

### Entries and headings

57. **Header:** name, phone, email, LinkedIn, GitHub, all plain text, with email and links clickable. No city (a non-local city
    gets you filtered out). "U.S. Citizen" when you target export-controlled work; elsewhere it's optional, and tells a skimmer
    no sponsorship is needed.
58. **No summary.** The evidence is thin, and it costs three lines of real work.
59. **Skills: two lines, one line each,** only what you can be questioned on (a specialist variant may need a third). No "AI
    coding tools" filler. Remove what you haven't really used and trivia a hiring manager won't care about.
60. **Keep the employer's brand clean and visible.** An unknown employer gets a few words of context ("Bay Area edtech
    startup").
61. **Title each project by what it is.** No grab-bag heading over several small items.
62. **No dates on projects.** They add nothing and raise questions.
63. **GPA on one line when it helps;** a low one can stay off. Honors and coursework come off once you work full time.
    Students and new graduates keep real ones, one line each under Education.

---

## One resume, not one per job

Per-job AI tailoring was the case study's previous approach: about 100 applications, zero human callbacks. Once AI made
tailoring free, employers stopped rewarding it (Galdin & Silbert).

- **A few role-family variants,** each fully polished. Variants reorder projects and skills, drop an entry, or add a
  supporting project. They never get new wording per posting.
- **Choose the variant by reading the role, not by the company or a word match.** A term in passing, or one naming another
  team, doesn't make it a specialist role. A web role at a defense company gets the general resume. `posting_must_mention` in
  `profile.yaml` suggests a variant; the role's daily work decides.
- **Never swap a strong project for a weak one that hits keywords.** A class project can be one supporting line on the variant
  that needs it.
- **The one safe per-job edit is reordering the skills lines** (`--emphasize "C++,Python"`). It never adds a skill.
- **No per-company copies.** They go stale. One PDF per variant.

---

## Format and ATS safety

The builder (`jobhunt/resume.py`) enforces these on every build:

- **One full page.** Text fits at 10.5–10.9pt and runs to the bottom margin; the last line or so is spread through the gaps,
  never left as a band. `overflow` and `underfull` builds go to `.overflow.pdf` and `.underfull.pdf`, never the final path.
- Text-based PDF printed by Chrome, kerning and ligatures off, so every word extracts with its spaces.
- Plain ASCII hyphens and spaces. AI tools emit non-breaking hyphens and narrow no-break spaces that break search.
- Every bullet, title and skills line extracts word for word; contact details parse; the name is the first line.
- No stranded words, no three-line bullets, no wrapped skills lines, no wrapped contact line.

Ship only when the build says `status: ok` with empty `lint` and `short_last_lines`.

---

## Working on it with an AI

The `resume-workshop` skill follows this. It's the part most people skip, and it's why the result reads as yours.

1. **Gather and interview** until every substantial entry has its why, your part, scale, results and the hard part.
2. **Get a model.** One or two real resumes from people in your field and at your level who get callbacks. Compare on bullets
   per job, lines per bullet, technical terms, what they name, and how they show ownership. The first draft that worked in the
   case study was built this way.
3. **Research current guidance online** for your role and level. This playbook is a starting point, not a substitute. Say what
   couldn't be read. Every recommendation carries its evidence and how strong that evidence is.
4. **Confirm the point before rewording.** State a bullet's single main point and get a yes. After two rejected rewrites, stop
   generating and ask the person to say it in their own words. Most final bullets are their wording, tightened.
5. **Propose in chat; wait for a yes; then edit.** At fine-tuning, no test PDFs and no working ahead. A file with changes in it
   looks like a change, whatever the AI calls it. Use the character budget and `--check` to confirm fit privately.
6. **One bullet at a time.** Offer several wordings (ten, if asked). A wording called "best" names its criteria.
7. **Apply exactly what was approved,** nothing bundled with it. Say what's removed and what replaces it. Never remove anything
   quietly; after merging drafts, list every fact that fell out. A near-final bullet gets the smallest edit.
8. **Do a cold-recruiter read on every proposed draft,** before showing it.
9. **Push back on the person's wording too,** with evidence, not only on outside reviews. When calling a phrase weak, say why,
   in terms of what a reader does with it.
10. **Check every claim against the inventory before building.** Every overclaim that slipped in was caught this way.
11. **Get outside reviews, then judge them.** Give a reviewer the latest version and the decisions log, or it re-proposes what
    was settled. Every addition on a full page names what it replaces.
12. **Keep one obvious current file** and an editable copy the person can change (a doc, not YAML). Keep open items in a list,
    and raise them before shipping.
13. **Record every decision and rejected wording** in `decisions.md`.

## Validating it

A simulated skim isn't validation. Have two or three real people in your field do a ten-second test: what do I do, and what was
most impressive? Then count responses. Callback counts need hundreds of applications to separate two versions (see
[EVIDENCE.md](EVIDENCE.md)), so judge by those reads, not by a week of silence.

## Before you send it

- [ ] Every claim is in `inventory.md`, and you can defend each bullet for ten minutes.
- [ ] Each bullet passes the seven tests.
- [ ] The build says `status: ok`, `lint: []`, `short_last_lines: []`, and you've read the `style` warnings.
- [ ] Side by side with your model resume, it's as full and as technical.
- [ ] The PDF's text pasted into a plain editor reads in the right order with no odd characters.
- [ ] The file is named `First_Last_Resume.pdf`.
- [ ] You're sending the right variant for what this posting asks for.
