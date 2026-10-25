---
name: apply-list
description: Build and explain the one list the user applies from (workspace/APPLY_LIST.md and the apply_list.html checkbox page), plan referrals, check application forms, and help with application questions. Use when the user asks "what should I apply to", "give me the list", "which role should I use my referral on", "can I apply to this", pastes a job link to add, or asks for help with an application form question.
---

# apply-list: what to send, in what order

Read `docs/APPLYING.md` once. The list is a file, not a chat message: long lists in chat get lost. In chat, give a few
lines and link the file.

## Build it
```bash
python3 -m jobhunt list
```
It re-scores every company's newest run (posting age and your history move; reviews don't), drops anything already
applied to, applies `eligibility.max_required_years`, the per-company cap and `company_rules`, and writes:
- `workspace/APPLY_LIST.md`: Referral (best three roles per referral company), Ask first (strong matches blocked by
  one stated requirement), your region, everywhere else, and "Not on this list" with counts and reasons;
- `workspace/apply_list.html`: the same list with checkboxes. Ticks are saved in the browser; "Copy log commands for
  checked roles" gives the `applied add` lines to run or paste back to you. (In Claude Code with the Artifact tool, you
  can also publish it as a private page; its checks then live in that page's database.)

Every row shows the posted date, a link to the posting and which resume to send. Tell the user the counts and link
the file. If the list looks wrong (a role they applied to, a role at the wrong level), fix the input (log the
application, fix the review), never the file by hand.

## A link the user found
1. `python3 -m jobhunt resolve "<Company>"`. If the company is registered, run the `find-jobs` refresh so the posting
   gets read and ranked with everything else.
2. If it isn't, or they just want this one: read the posting (`fresh show`, or open it), decide eligibility honestly
   (years, level from the company's ladder, location, clearance, form questions), and add it to
   `workspace/picks.yaml`: required `company`, `job_id`, `title`, `url`; plus a hand score (`work`, `yoe`, `region`,
   `where`, `variant`, `career`) and a `note` with what the job is, what matches, the main gap and the pay. Then
   rebuild the list; it reports any pick missing a required field.

## Eligibility, decided not asked
- Don't ask whether they "want" a role they'd qualify for; decide whether they can plausibly get it and say so.
- If they say they don't fit, re-read the requirements line by line with them before agreeing or disagreeing.
- A missing years line is not eligibility; check the company's ladder.
- Postings above their years limit stay off the list.

## Referrals
For each referral company: recommend ONE role (job id and link) and one backup, after checking both forms' required
questions (`python3 -m jobhunt fresh show "<Company>" <id>`). Remember who the referrer is: a friend who can submit a
referral can't necessarily ask recruiting anything. Offer the short message in `docs/APPLYING.md` for them to adapt
and send themselves.

## Application questions
- Yes/no screening questions: help them read what's being counted; answer truthfully. If a truthful "no" rules them
  out, say so and move on.
- Essays ("most impressive accomplishment", "three bullets of exceptional ability", "why us"): suggest which inventory
  items to use and the one point each should make, in a few lines. Let them write it. If they ask you to write it,
  keep it short, specific and in their voice, using only inventory facts.

## When they've applied
Log each one (`python3 -m jobhunt applied add ...`) and rebuild the list. Confirm in one line.
