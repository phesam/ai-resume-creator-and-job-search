---
name: resume-workshop
description: Write or revise the resume in workspace/resume.yaml from the inventory, one bullet at a time, with the user's approval on every change, then build the one-page PDF and run every check. Use when the user wants a new resume, wants to rewrite or tighten bullets, add new work, create a role-family variant, or asks "is my resume good".
---

# resume-workshop: a resume a recruiter understands and an engineer respects

Read first, every time: `docs/RESUME_PLAYBOOK.md` (the rules and why), `workspace/inventory.md` (the only source of
facts), `workspace/decisions.md` (what's settled and what wording was rejected), and the current `workspace/resume.yaml`.

## Ground rules

- **Every claim comes from the inventory.** If a fact is missing, stop and ask (the `inventory-interview` rules:
  one numbered list, no cap). Never write around a gap.
- **Propose in chat; wait for a yes; then edit.** When the user asks a question ("could we split this?", "what
  about...?"), answer in chat: yes or no, the proposed wording, the trade-off. No edits, no test PDFs, no trial
  files until they say go. During fine-tuning, don't work ahead of the decision in front of you.
- **One bullet at a time.** Offer 3–5 wordings (10 if asked). Let them pick and edit. Their own wording, tightened, is
  usually the winner.
- **One resume per role family.** Never regenerate bullets for a single posting.
- **Record every decision and rejected wording** in `decisions.md` as you go, with the date and reason.

## 1. Know the target

- Which role families? Usually one `general` variant first. Add `systems` or `ai` (or others) only if the user
  targets roles that need different evidence on the page.
- **Count keywords** in 10–30 current postings they would really apply to (use a company run's `review/` packets or
  `python3 -m jobhunt fresh show`). Tally the technologies and phrases that recur. This tells you which TRUE skills
  must be visible in bullets. Never add one they didn't use.

## 2. Choose the material

- Per job, the 4–5 strongest results for the newest role, 1–3 for internships, 1–2 per project.
- Strongest first within each job: the biggest, clearest result with the most-asked-for stack. Don't bury a current,
  in-demand item (an AI workflow, a production service) at the bottom.
- Cut order when space runs out: the weakest internship (keep it as one line if possible), then the weakest
  project, then the weakest bullet of the main job.
- Don't let two projects show the same thing.
- A startup goes under Projects for big-company targets ("Co-founder & Software Engineer").

## 3. Draft each bullet (what + how + why)

For each bullet, before proposing it, check it yourself against the five tests in the playbook:
1. Can a non-engineer repeat what was built and what it was for?
2. Could the user talk about it for ten minutes, including how each number was measured?
3. Does it claim only their part ("added X through a service", not "built the platform")?
4. Is the best result visible, with its contrast next to it ("~3 minutes, replacing a 1–2 day release")?
5. Is every name one an outsider knows (no internal service names, team names, acronyms)?

Also: about two lines (one for what, one for why), plain past-tense verbs, the stack inside the sentence, scale where
it helps, exact status (projected, A/B tested, merged), at most one bold item, no team size or process trivia, no
filler ("increasing developer velocity", "leveraged", "various"), no first person.

When a bullet must lose words to fit, keep it one bullet and drop its least important part. Don't split one story into
two thin bullets.

## 4. Header, skills, education

- Header: name; phone | email | LinkedIn | GitHub (plain text, clickable); "U.S. Citizen" only if it matters for
  their targets. No city. No photo.
- No summary.
- Skills: two lines (`Languages:`, `Tools:`), only what they could be questioned on, most relevant first. A variant
  may use three lines with its own grouping.
- Education: school, date, degree and GPA on one line. Honors only if early in their career and the page has room.
- Projects: a `link` shows as plain text and is clickable; no dates.

## 5. Edit, build, check

After the user approves a change, edit `workspace/resume.yaml` (quote every string; an unquoted ` #` cuts the line).
Then:

```bash
python3 -m jobhunt resume --variant general      # or --all
```

Ship only when the report shows `status: ok`, `lint: []` and `short_last_lines: []`.
- `overflow`: too long for one page; cut. `underfull`: more than half an inch empty; add.
- `short_last_lines`: trim the characters it names, or add a few words of detail.
- `style`: advisory. Fix real problems; explain to the user why a flagged bullet is fine if it is.
Add rejected phrases to `writing.banned_phrases` and internal names to `writing.jargon` so the build flags them next
time.

Read the extracted text once as a recruiter would: `pdftotext -layout workspace/resume/general/<Name>_Resume.pdf -`.

## 6. Outside reviews

Offer the `resume-review` skill (a fresh, independent read). When the user pastes a review from another model or a
person: evaluate it point by point with evidence, agree where it's right, push back where it's wrong (for example a
reviewer who wants a number dropped that the user can explain), and propose only the changes worth making. Make sure
the reviewer saw the latest version.

## 7. Keep it alive

- Give the user an editable copy if they want to edit wording themselves (a shared doc or plain text), and match
  `resume.yaml` to their edits.
- When they report new work or results: inventory first, then a proposal.
- When asked whether the PDFs are current, check (`ls -l workspace/resume/*/` against `resume.yaml`'s modification
  time) instead of guessing.
