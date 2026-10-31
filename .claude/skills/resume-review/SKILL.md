---
name: resume-review
description: An independent, evidence-based review of the user's resume PDF as three readers see it (screening software, a non-technical recruiter, a senior engineer or hiring manager), plus a fullness check and a claims audit against the inventory. Makes no changes. Use when the user asks "is my resume good", "review my resume", "will this get callbacks", or wants a second opinion before applying.
---

# resume-review: read it the way it will be read

This skill reviews; it never edits. Its output is findings and proposed wordings, for the user (or the
`resume-workshop` skill) to accept or reject.

For an unanchored read, run it in a fresh subagent that gets only the PDF path, `docs/RESUME_PLAYBOOK.md`,
`docs/EVIDENCE.md`, `workspace/decisions.md` (so it doesn't re-propose what was settled) and, for the claims audit,
`workspace/inventory.md`. It doesn't get the conversation that wrote the bullets. Confirm it has the latest version.

Search the web for current recruiter and hiring-manager guidance for this role and level, and put anything you couldn't read at
the top of the report.

## 1. Is the page finished?

Open the PDF and run `python3 -m jobhunt resume --check`. A finished page runs to the bottom margin at 10.5–10.9pt, with 6–8 entries,
13–15 bullets, about 195 characters each and about three technical terms per bullet (`docs/RESUME_PLAYBOOK.md`,
`templates/resume.yaml`). Put it next to their model resume if they have one. A thin or plain page is the top finding: send them
back to the interview for more material. Rewording can't fix it.

## 2. The software's read (2 minutes)

```bash
pdftotext -layout <pdf> -
pdftotext <pdf> /dev/stdout | LC_ALL=C grep -n '[^ -~]'
```
- Reading order right? Name first? Contact details intact (no broken URLs, no odd hyphens)?
- Every non-ASCII character intentional (en dashes in dates and bullets are fine; U+2011, U+202F, U+00A0 are not)?
- Standard headings (Experience, Projects, Education, Skills)? One column?
- Do the technologies the target postings ask for (that the person really used) appear in bullets, not only in the
  skills lines?

## 3. The recruiter's skim (30 seconds, then write down what you remember)

Look at the page for 30 seconds as a recruiter who is not an engineer, holding a keyword list. Then, without looking:
- Which companies and titles do you remember? Is the employer brand obvious?
- For each job, can you say in plain words what they built and why it mattered?
- What's the single most impressive thing on the page? Is it near the top?
- Does each bullet's opening clause make sense alone?
- Any private names (internal services, teams, product code names)? Public technical terms are fine, even ones you don't know: they're
  for the engineer. Never suggest removing one to help the skim.

## 4. The engineer's read

Be a senior engineer at a target company deciding whether to interview this person. This is the read that decides. Bullet by bullet:
- **Real work or a task description?** Point to the named system and the engineering inside it. A clear bullet with nothing in it fails.
- **Impressed or just informed?**
- **What + how + why** present? Name any bullet that is a list of tools or tasks with no purpose. One production-ownership colon list is
  fine: it proves a cluster postings ask for.
- **Scope, both ways.** Any verb that claims more than the inventory supports? Any bullet that undersells platform-wide work as one page,
  when the inventory shows more?
- **Ownership:** are "designed and built" and "led" used where true?
- **Numbers:** does each say what it measures? Any that a reader would ask "of what?" about?
- **The hardest work:** is it on the page, with its failure named? Check the inventory's hard parts against the bullets.
- **Contrast placement:** is the best result next to its baseline?
- **Filler and AI voice:** stiff verbs, identical bullet shapes, vague metrics, process words where a concrete noun belongs.
- **Layout:** bullets over two lines, too much bold, every bullet ending at the same width.

## 5. Claims audit

For every bullet, find the supporting fact in `workspace/inventory.md`. List any claim that is missing, stronger than
the inventory says, or has a stale status (for example "merged" for something still in review).

## 6. Report

Lead with a verdict in two sentences. Then the findings in priority order, each with:
- what's wrong and which reader it hurts,
- the evidence (cite `docs/EVIDENCE.md` or the playbook rule and its strength),
- a proposed rewording that uses only inventory facts, with its character count. **On a full page every addition names what it
  replaces.** Length-neutral suggestions only.

Say what is already strong and should not be touched. Don't recommend changes recorded as tried and rejected in
`workspace/decisions.md`, or re-question its fixed facts, unless you have new evidence; if you do, say so explicitly.

End with the real test, because a simulated skim isn't validation: two or three people in their field, ten seconds each: what do I do,
and what was most impressive? Count the answers.
