---
name: resume-workshop
description: Write or revise the resume in workspace/resume.yaml from the inventory, then build the one-page PDF and run every check. Produces a full, dense page written for the engineer who decides, with the recruiter served through word order. Use when the user wants a new resume, wants to rewrite or tighten bullets, add new work, create a role-family variant, or asks "is my resume good".
---

# resume-workshop: a full page an engineer respects and a recruiter can follow

Read first, every time: `docs/RESUME_PLAYBOOK.md` (the rules and why), `workspace/inventory.md` (the only source of
facts), `workspace/decisions.md` (what's settled and what wording was rejected), the current `workspace/resume.yaml`, and
the finished page in `templates/resume.yaml` with its pattern comments.

**The target is that page's density: full to the bottom margin, 6–8 entries, 13–15 bullets, about 195 characters each,
about three technical terms per bullet.** That's for someone with a year or more of real work. A clean, tidy, sparse page is
a failure, even if every sentence is clear and the build says `ok`, until the interview has nothing left. With less experience,
the page still fills, with more entries and bullets only as long as the facts (step 8 says when to stop). The steps below are
gates: don't skip one because it looks unnecessary.

## Ground rules

- **Every claim comes from the inventory, and only confirmed facts go on the page.** A fact marked *unconfirmed* gets
  confirmed first (contact details and education can wait until they read the draft). If a fact is missing, stop and ask (the
  `inventory-interview` rules: one numbered list, no cap). Never write around a gap.
- **Written for the engineer who decides.** The plain "what" opens the bullet, and the technical substance stays after it.
  Never remove engineering content to make a bullet easier to read. Keep public technical terms; cut only private names.
- **When the user asks a question,** answer in chat: yes or no, the proposed wording, the trade-off. No edits, no test PDFs,
  no trial files until they say go. During fine-tuning, don't work ahead of the decision in front of you.
- **One resume per role family.** Never regenerate bullets for a single posting.
- **Record every decision and rejected wording** in `decisions.md` as you go, with the date and reason.

## 1. Inventory gate

Before writing a bullet, check the inventory. For every substantial job and project, it must answer:
why it existed and who couldn't do what before; their exact part; scale; results from what to what; status; and the hard
part, including what it took. Also: what past interviewers praised.

Any gap: run the `inventory-interview` skill now. A thin inventory makes a thin page, and no wording fixes that.

Big projects (their own product, a large open-source effort): make a menu first. With consent, read the code as well as the
commit log, list everything they built with their share of it, and let them choose. Include shipping and release work.

## 2. Get a model resume

Ask for one or two real resumes from people in the same field, at about the same level, who get callbacks. If they have
none, find public ones online and say that's what you did.

Record the model's density in `decisions.md` under "Model and research": bullets per job, lines per bullet, technical terms per
bullet, what they name, how they show ownership. Pick a model at the person's level: a new graduate's page doesn't look like a
senior engineer's. Your draft has to match it or beat it. Without a model, use `templates/resume.yaml`.

## 3. Research this role and level

Search the web for current guidance from recruiters and hiring managers for this role and level. The playbook is a starting
point, not a substitute. Put sources you couldn't read at the top of your reply. Every recommendation carries its evidence and
how strong that evidence is. Don't cite a page you haven't opened.

## 4. Count keywords

```bash
python3 -m jobhunt keywords --companies "Acme,Globex,Initech" --match "software|engineer"
```

Use 3–10 companies they'd really apply to, or `--run <dir>` for a finished run. Rows marked `IN INVENTORY, NOT ON RESUME` are skills
the page doesn't show yet (before the first draft, that's every skill in the inventory). Check each against the inventory before
using it. Never add a skill they didn't use. Put title keywords in a bullet where they're plainly true, not only in Skills.

## 5. Plan the page before wording it

Show the plan in chat, as a table, and get a yes: every entry, in order, with how many bullets it gets and the main point of
each bullet.

- **All substantial entries go on the page.** The page isn't done until they're all there and it's full. Never drop a substantial
  entry to pay for a detail.
- Bullets: about 5 on the newest job, 2 on the next big entry, 1–2 on the rest, one bare line for a minor entry (a side item can be
  a single row: `inline_org: true`, `bullets: []`). Move bullets between entries to fit the person. **The page decides the count:** if it's short, add more; 4–5 per job is not a cap.
- Pick each major entry's highlight. Strongest first within a job: the biggest result with the most-asked-for stack; current,
  in-demand work high up, never buried, without splitting a story to get it there. In-demand work goes under the strongest employer
  when true, not only in projects.
- The hardest work gets its own bullet, with the failure named.
- The bullets of one job read as one story, and no bullet depends on one below it. Two projects don't prove the same thing.
- A startup goes under Projects for big-company targets ("Co-founder & Software Engineer"). A sponsored project puts the sponsor
  on the employer line.

Cut order when space runs out: a minor entry down to one line, then the weakest bullet on a project, then the weakest bullet on the
main job. Never cut a substantial entry entirely without asking.

## 6. Draft

Write the whole page as a first draft in chat, then work through it one bullet at a time.

**Every bullet follows a named pattern** (playbook, "Shapes that work"; worked examples in `templates/resume.yaml`). Use several
patterns across the page. Aim for 160–225 characters; a line holds about 108, so nearly every bullet runs into a second line.
Minor entries are shorter. Show each wording's character count.

For each bullet:
1. **State its single main point** and get a yes before rewording it.
2. Offer 3–5 wordings (10 if asked). Say what each one does better. If you call one best, name the criteria.
3. After two rejected rewrites, stop generating. Ask them to say it in their own words, then tighten that.
4. Do a cold-recruiter read before showing a wording. Check the seven tests: repeat, engineer, impressed, owner, scope both ways,
   skim, private names.

If a bullet can't reach 160 characters without inventing or padding, it stays short. Ask for more first; never stretch it.

Details that get missed:
- Lead with the capability that didn't exist before, at the level of the organization, not the one page where it appeared.
- Own it: "designed and built", "led". Past tense for finished work, present for ongoing ("provide on-call support").
- Concrete nouns beat process words. Each clause shows what the candidate did: delete a clause, and if their credit doesn't change,
  it goes.
- Name senior partners and cross-team alignment. Leave out team size and approval steps.
- A talk, award or adoption note is a clause on the work it belongs to.
- Make reality explicit on projects: live data, real users, production.
- Exact status. Never drop a number without asking what it measures.
- Bold the one thing a skimmer should catch (two only for two separate results).
- Vary bullet shapes and where they end. Never pad to fill a line.
- When a clause is weak, ask what it took. Replace it with what you learn.
- Push back on their wording too, with evidence. When you call a phrase weak, say why, in terms of what a reader does with it.

Fine-tuning:
- **Apply exactly what was approved,** nothing bundled with it. If an approval is ambiguous, confirm. Say what's removed and what
  replaces it. A near-final bullet gets the smallest possible edit.
- **Never remove anything quietly.** After merging two drafts, list every fact that fell out.
- "Lighten this bullet" means cut: remove words and report what left. When a bullet must lose words, keep it one bullet and drop its
  least important part.
- Check fit privately with `--check`, which writes no file. Tell them how many lines are left on the page.

## 7. Header, skills, education

- Header: name; phone | email | LinkedIn | GitHub (plain text, clickable). "U.S. Citizen" when they target export-controlled work;
  elsewhere optional. No city. No photo. No summary.
- Skills: two lines, one line each (`Languages:`, `Tools:`), only what they could be questioned on, most relevant first. Check both
  directions: tools in bullets missing from Skills, and Skills items that appear nowhere else, with a reason for each. Only a
  specialist variant may use a third line. Leaving a minor tool off is fine.
- Education: school, date, degree and GPA on one line (a low GPA can stay off). Honors and coursework come off once they work full
  time. Students and new graduates keep real ones as `lines:` under the school, one line each.
- Projects: a `link` shows as plain text and is clickable; no dates. An unknown employer gets a few words of context on its line.

## 8. Build and fill the page

After the user approves, edit `workspace/resume.yaml` (quote every string; an unquoted ` #` cuts the line). Then:

```bash
python3 -m jobhunt resume --check --variant general   # fit report only, writes no file
python3 -m jobhunt resume --variant general           # or --all
```

Ship only when the report shows `status: ok`, `lint: []` and `short_last_lines: []`. Read `fill` every time.

- **`underfull`:** the page has a blank band, and the note says how many lines are missing. Don't stop here, and don't hand this
  to the user as finished. Add, in this order:
  1. real work from the inventory that isn't on the page yet;
  2. a second bullet on an entry with only one;
  3. a line of real detail on a thin bullet (`avg_bullet_chars` far under 190 says this is the problem);
  4. back to the interview for that entry: the hard part, who used it, what it replaced;
  5. if the real material has run out and they're early in their career: honors and coursework lines under Education, then
     activities, then class projects that have real detail.
  Never grow the text, never pad with words, never invent. A bullet with nothing to say isn't material, even if it makes the build
  pass: it fails the engineer test. If the page still can't fill, tell them how many lines are missing and let them decide: a short,
  honest page beats a padded one. The file is `.underfull.pdf`.
- **`overflow`:** too long for one page; cut, in the cut order above.
- **`short_last_lines`:** a stranded word, or a bullet running to three lines. Trim it. Don't add words to reach further.
- **`style`:** advisory. Fix real problems. If a flagged bullet is fine, explain why to the user.

Add rejected phrases to `writing.banned_phrases` and private names to `writing.jargon` so the build flags them next time.

## 9. Before calling it done

**It's done when the page is full, the build says `ok`, and the interview has nothing left.** If they've told you that's everything,
believe them after one more pass. Say plainly where the page falls short of the target and why, then stop pushing.

- **Compare to the model,** side by side: `fill` numbers against the density you recorded, then the strongest bullet against the
  model's strongest, on clear start, clear end, concrete steps and shown reach. If the model looks fuller or more technical, it isn't
  done.
- **Look at the PDF.** Open it. A blank band, a thin page or a block of same-length bullets is a failure, whatever the status says.
- **Check every claim** against the inventory, one by one.
- **Ask what's left.** Review findings and weak bullets produce new questions. Put them to the person in one list before stopping.
- **Sweep older resume versions once** for anything stronger than the current page.
- **Read it once as a recruiter:** `pdftotext -layout workspace/resume/general/<Name>_Resume.pdf -`.
- Raise anything still open before shipping.

## 10. Outside reviews

Offer the `resume-review` skill (a fresh, independent read). When the user pastes a review from another model or a person: evaluate
it point by point with evidence, agree where it's right, push back where it's wrong (a reviewer who wants a number dropped that the
user can explain, or a simpler bullet that loses the engineering). On a full page, every addition names what it replaces. The reviewer
needs the latest version and `decisions.md`.

Then give the real test: two or three people in their field, ten seconds each: what do I do, and what was most impressive?

## 11. Keep it alive

- Keep one obvious current file and say its path. Give the user an editable copy if they want to edit wording themselves (a shared doc or
  plain text), and match `resume.yaml` to their edits.
- When they report new work or results: inventory first, then a proposal.
- When asked whether the PDFs are current, check (`ls -l workspace/resume/*/` against `resume.yaml`'s modification time) instead of
  guessing.
