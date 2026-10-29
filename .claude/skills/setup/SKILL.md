---
name: setup
description: First-run setup for the resume and job-search workflow. Use when the user says "set me up", "get started", "how do I use this", or when workspace/ doesn't exist yet. Checks the machine, creates the workspace, fills profile.yaml by asking a short list of questions, then gathers what the user already has (with consent) and hands off to the inventory interview.
---

# setup: from a fresh clone to a working workspace

Work from the repository root. Read `CLAUDE.md` (or `AGENTS.md`) once if you haven't.

## 1. Check the machine

```bash
python3 -m pip install -r requirements.txt
python3 -m jobhunt init
python3 -m jobhunt doctor
```

`init` copies `templates/` into `workspace/` and never overwrites. Fix every `FAIL` from `doctor` before going on
(docs/TROUBLESHOOTING.md has the fixes: Chrome or `CHROME_PATH`, poppler for `pdftotext`, Python packages).

## 2. Explain the workflow in five lines

Say, briefly:
1. We interview you about your work and save every fact in `workspace/inventory.md`.
2. We write your resume from those facts, one bullet at a time, with your approval on every change.
3. We fetch every open posting at companies you name (or across a region) from their own hiring systems, read the
   plausible ones in full, and rank them by your odds and what you want.
4. You get `workspace/APPLY_LIST.md`: what to send, in order, with the resume to use.
5. You apply yourself. Nothing is ever submitted or sent for you.

## 3. Fill profile.yaml

Ask these in ONE numbered list (the user can answer in any order, by voice, in fragments). Don't ask what the
templates already answer sensibly.

1. Your name as it should appear on the resume.
2. Work authorization (and U.S. citizen or not: export-controlled roles need it). Any security clearance?
3. When you started full time (month/year), and when you graduated.
4. Where do you want to work, best first? (A metro, "anywhere remote", a second-choice city.) Would you move for a
   great role elsewhere?
5. What kinds of roles: the job titles you'd take, and kinds of work you'd rather avoid (pure test, analyst, ops...).
6. The most years of experience a posting can ask for and still be worth sending.
7. Companies you'd drop everything for (they go on the watchlist).
8. Anyone who will actually refer you, and where. (A LinkedIn connection who works there is not a referral.)
9. Your current base pay, if you want roles that pay less flagged (never used to rank).
10. Do you target defense, space or other export-controlled work? (Decides "U.S. Citizen" in the header and the
    systems variant.)

Then edit `workspace/profile.yaml`:
- `name`, `summary` (3–5 plain sentences; refine after the inventory exists), `target_roles`, `citizenship`,
  `clearance`, `fulltime_start`, `graduation`, `eligibility.max_required_years`.
- `regions`: one entry per place they named, best first, with `covers`, `hint_places` (the cities and towns in that
  area that postings will name), a `broad_match` regex for the state if useful, and `weight` (1.1 for the top
  choice, 1.0 for nearby, ~0.85 for a second metro). Set `remote_weight` (1.1 if remote lets them live where they
  want), `elsewhere_weight` (0.65 if they'd only move for something great, higher if open), and
  `apply_list.local_table` to their top region keys.
- `role_preferences` from what they'd rather avoid; `referrals`; `pay.current_base`.
- `workspace/watchlist.yaml`: the companies from question 7 (names as in `data/companies.yaml`; for one that isn't
  there, `python3 -m jobhunt resolve "<name>"`).
- `workspace/privacy_terms.txt`: their name, email, phone, handles, employers, project names, school. Only matters if
  they ever publish a fork of this repo; `python3 -m jobhunt privacy-check` uses it.

Show the profile changes in a few lines. Run `python3 -m jobhunt doctor` again (the profile must parse).

## 4. Hand off

Start the `gather-sources` skill: with the user's consent it finds their old resumes, reviews, local repositories and
GitHub activity, so the interview only asks about what those don't answer. Then the `inventory-interview` skill.
If the user only wants jobs today and already has a resume they like, they can
skip to `find-jobs`, but the reviewers score fit against `inventory.md`, so at least a rough inventory (paste the
resume text into it) has to exist first.
