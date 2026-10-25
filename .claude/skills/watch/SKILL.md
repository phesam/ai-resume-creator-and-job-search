---
name: watch
description: Catch new postings at the user's top companies within days of posting, decide eligibility, and add the good ones to their apply list. Use when the user asks "anything new at my companies?", for a daily check, or to set up a scheduled daily run.
---

# watch: apply in the first week

Most applicants arrive in a posting's first week and recruiters review as applications come in, so for the companies
the user cares most about (`workspace/watchlist.yaml`), speed is the edge.

## 1. List what's new
```bash
python3 -m jobhunt fresh list --days 8
```
Prints, as JSON, every posting first published in the last 8 days (by the employer's own date) that hasn't been
marked reviewed, plus `errors` for any company that couldn't be fetched, and `no_publish_dates` for systems that give
no dates (use `python3 -m jobhunt watch` for those: it lists postings new since the last check). If `errors` isn't
empty, retry once; never report "nothing new" for a company you couldn't fetch.

## 2. Read the plausible ones
Read every new posting whose title could be the user's kind of work (`target_roles` in the profile), including
"Senior" titles, then apply the eligibility rules. Skip only titles that are plainly another profession. When unsure,
read it:
```bash
python3 -m jobhunt fresh show "<Company>" <id>
```
shows the whole posting, its locations, date, pay and (Greenhouse, Ashby) required form questions.

## 3. Decide eligibility
From `workspace/inventory.md` and `workspace/profile.yaml`:
- Not eligible: a stated minimum above `eligibility.max_required_years`; an active clearance required on day one
  that they lack; a required degree they don't have; internships and contract roles; roles outside the country.
- **Senior or no years stated:** work out the level from the company's ladder (the same company's other postings
  with that level word, and pay bands). Count it only when the posting itself states a minimum within their limit.
  If you can't establish the level, list it as "couldn't confirm level" instead of adding it.
- Never drop a role for location alone if the user said they'd take any job at that company; never ask whether they
  want it.

## 4. Add the eligible ones
Add each to `workspace/picks.yaml` (inside `picks:`; skip a job id already there) with a hand score: `work` (0–5, how
much of the daily work they've done), `yoe`, `region` (a key from the profile), `where`, `variant`, `career` (0–5),
`posted`, `added`, `url`, `title`, and a two- or three-sentence `note` (what the job is, what matches, the main gap,
the pay). Then:
```bash
python3 -m jobhunt fresh mark <id> <id> ...   # every id you looked at, read or skipped; pass ids as separate arguments
python3 -m jobhunt list
```

## 5. Report
Short, top company first: a table of the eligible new roles (title linked, company, published date, location, years
asked, work match, resume), one line each on why they fit and the gap, then per company one line: how many new, how
many read, and the ones ruled out with the reason ("asks 5+ years").

## Running it daily
In Claude Code, a scheduled task can run this skill each morning (it runs only while the app is open). The task
prompt should say: work in this repository; run the steps above; never apply, send messages or edit the resume;
report briefly. Codex users can run the same steps by hand, or from cron with their agent's non-interactive mode.
