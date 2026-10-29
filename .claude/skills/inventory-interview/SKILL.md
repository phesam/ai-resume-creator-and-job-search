---
name: inventory-interview
description: Interview the user about their work and record every fact in workspace/inventory.md, the only source of truth for the resume and job reviews. Use at setup, when they mention new work, results or numbers, before writing or revising any bullet whose facts are thin, or when they say "update my inventory".
---

# inventory-interview: get the facts before writing anything

The case study's first four rounds of resume bullets were rejected because they were drafted from old resumes and
guesses. The person had every fact needed; they just didn't know which ones the writer needed. So: ask.

## Rules

- **Ask everything missing in one numbered list, grouped by job or project.** No cap on the number of questions.
  The user answers in any order, often by voice, often in fragments. That's fine.
- **Record answers verbatim-ish, dated,** in the entry's section and in the "Interview log" at the bottom of
  `workspace/inventory.md`. Keep their words; they become the best bullets.
- **An answer is not an instruction to put it on the resume.** Collect the facts; choosing comes later.
- **Never invent.** Don't fill a gap with a plausible guess. If they don't know a number, write that they don't.
- **Never drop a number without asking what it measures.** If a figure has no baseline in the notes, ask for it.
- **Don't re-ask what's settled.** Read `inventory.md` and `decisions.md` first.
- This file is personal; it lives in the ignored `workspace/` folder.

## 1. Start from what exists

Read `workspace/inventory.md`. If the `gather-sources` skill hasn't run, offer it first: with consent it reads old
resumes, self-reviews, local repositories and GitHub, so you only ask about what they don't answer. If the user would
rather paste things (an old resume, LinkedIn text, a brag document), record the facts in them (not the wording),
marked "from old resume, unconfirmed".

Start the question list with what the sources left open: every fact marked *unconfirmed* (a quick yes, no or
correction each), and every conflict between sources (two versions of one number, a status that may have changed).

## 2. Ask, per entry (job, internship, startup, open source, serious project)

Use the template's fields. For each entry, ask only what's missing:

1. **What is it, in one sentence a stranger would understand?** Who uses it?
2. **Why did it exist?** What was broken, slow, missing or manual before? Who was hurt by that?
3. **What did you personally do?** What did others do? What did you own end to end? What decisions did you make?
4. **What was hard?** Unknown systems, failures, a nasty bug, a deadline, teams that disagreed. How did you figure it
   out?
5. **Scale:** users, traffic (views/week, requests/day), data size, money, number of teams.
6. **Results, from what to what:** time saved, speed, errors, adoption, revenue, ratings. For each: what exactly it
   measures, the baseline, the period, where the number comes from.
7. **Status:** shipped to everyone? A/B tested? Merged or in review? Achieved or projected?
8. **Adoption and recognition:** who uses it now, teams onboarded, awards, who you presented to.
9. **Who you worked with:** stakeholders by role (head of product, design lead, other teams).
10. **Stack you actually used** (only what you could be questioned on), and what you did NOT use.
11. **Internal names:** what does each acronym or internal service name mean in plain words?
12. **How would you say it out loud** to a friend outside tech?

Also ask about: skills they have but never listed; coursework and class projects (only for a variant that needs
them); links they want on the resume; anything they're proud of that isn't on any resume.

## 3. Check sources you can read

If they point you at a repository, a design doc or a project folder, read it to confirm facts and to find things
worth asking about (for example "what does the 8 ms in this pipeline measure?"). Ask them to confirm anything you infer; a
repo shows what the code does, not what they personally did.

## 4. Summarize and save

- Fold the answers into each entry's fields; keep the raw Q&A in the interview log with the date.
- Mark conflicts ("March 3 says 60%; March 9 says >64%: newer wins") and settled facts.
- Tell the user, in a few lines, what's now recorded and what's still open. Then offer the next step: the
  `resume-workshop` skill.
