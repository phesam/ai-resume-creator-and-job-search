---
name: resume-review
description: An independent, evidence-based review of the user's resume PDF as three readers see it (screening software, a non-technical recruiter, a hiring manager), plus a claims audit against the inventory. Makes no changes. Use when the user asks "is my resume good", "review my resume", "will this get callbacks", or wants a second opinion before applying.
---

# resume-review: read it the way it will be read

This skill reviews; it never edits. Its output is findings and proposed wordings, for the user (or the
`resume-workshop` skill) to accept or reject.

For an unanchored read, run it in a fresh subagent that gets only the PDF path, `docs/RESUME_PLAYBOOK.md`,
`docs/EVIDENCE.md` and (for the claims audit only) `workspace/inventory.md`, not the conversation that wrote the
bullets.

## 1. The software's read (2 minutes)

```bash
pdftotext -layout <pdf> -
pdftotext <pdf> /dev/stdout | LC_ALL=C grep -n '[^ -~]'
```
- Reading order right? Name first? Contact details intact (no broken URLs, no odd hyphens)?
- Every non-ASCII character intentional (en dashes in dates and bullets are fine; U+2011, U+202F, U+00A0 are not)?
- Standard headings (Experience, Projects, Education, Skills)? One column?
- Do the technologies the target postings ask for (that the person really used) appear in bullets, not only in the
  skills lines?

## 2. The recruiter's skim (30 seconds, then write down what you remember)

Look at the page for 30 seconds as a recruiter who is not an engineer, holding a keyword list. Then, without looking:
- Which companies and titles do you remember? Is the employer brand obvious?
- For each job, can you say in plain words what they built and why it mattered?
- What's the single most impressive thing on the page? Is it near the top?
- Anything you couldn't understand (internal names, acronyms, jargon)?

## 3. The hiring manager's read

Bullet by bullet:
- **What + how + why** present? Name any bullet that is a list of tools or tasks with no purpose.
- **Scope honest?** Any verb that claims more than the inventory supports?
- **Numbers:** does each say what it measures? Any that a reader would ask "of what?" about?
- **Engineering substance:** is there at least one example of a hard problem solved (a failure, a race condition, an
  integration, a migration)?
- **Contrast placement:** is the best result next to its baseline?
- **Filler and AI voice:** stiff verbs, identical bullet shapes, vague metrics.
- **Density:** walls of text, bullets over two lines, too many bolds.

## 4. Claims audit

For every bullet, find the supporting fact in `workspace/inventory.md`. List any claim that is missing, stronger than
the inventory says, or has a stale status (for example "merged" for something still in review).

## 5. Report

Lead with a verdict in two sentences. Then the findings in priority order, each with:
- what's wrong and which reader it hurts,
- the evidence (cite `docs/EVIDENCE.md` or the playbook rule and its strength),
- a proposed rewording that uses only inventory facts.

Say what is already strong and should not be touched. Don't recommend changes the playbook records as tried and
rejected (`workspace/decisions.md`) unless you have new evidence; if you do, say so explicitly.
