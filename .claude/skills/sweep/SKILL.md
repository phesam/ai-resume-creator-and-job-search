---
name: sweep
description: Find every role the user is a strong fit for across many companies at once, kept to the regions they want (for example "every job in Los Angeles I'd be great for, startups included"). Use when the user asks for jobs in a place rather than at a company, or asks which companies to look at. Fetches every supported company in the registry (or a category), filters to their regions, then screens, reviews and ranks exactly like find-jobs.
---

# sweep: a whole region, every company

Same rules and the same stages as the `find-jobs` skill; read it first. Differences are below.

## 1. Fetch and filter
```bash
python3 -m jobhunt sweep --regions home,home_outer,remote_us --name la
# options: --category "robotics,space"   --companies "Acme,Globex"   --limit 20 (a quick trial)   --workers 12
```
- Region keys come from `workspace/profile.yaml` (`python3 -m jobhunt sweep --regions x` lists valid keys on error).
- It fetches every supported registry company in parallel (about 600; a few minutes), keeps postings with a location
  in those regions, and also keeps postings whose location can't be judged yet: "3 Locations" (Workday lists
  multi-site postings that way until the detail page is read), no location, or a string that matches a region's
  `broad_match` but no known place. Those are settled after the screen and the detail fetch.
- Boards that failed are in `<run>/fetch_errors.json` and counted in the report. Tell the user which companies are
  missing; re-run `find` on any that matter.

## 2. Screen
Same as find-jobs step 2, with more files. The titles files include a company column; decisions are cached per
company. The location file holds every new string from the kept postings: classifying them well is what keeps the
region filter honest.

## 3. Review, history, rank
Same as find-jobs steps 3–5. Reviews made here carry over to later company runs (and the other way round) when the
posting text is unchanged. `rank` writes one report across all companies, with each company's history summarized
and ★ on the best roles at each company.

## 4. Discovery: companies not in the registry
To widen the net before sweeping, find companies with software hiring in the region (regional "Built In" lists,
hiring.cafe, SimplifyJobs' New-Grad-Positions on GitHub, local accelerators), resolve each one
(`python3 -m jobhunt resolve "<name>"` / `detect <careers-url>`), confirm the board is really that company, and
`register` it with a `category`. Never trust an aggregator's posted date; the sweep uses the employer's own.

## 5. Hand off
`python3 -m jobhunt list`, then the same short summary as find-jobs: the accounting (companies fetched, failed,
postings in the regions, dropped per reason, read in full), and the strong matches or a link to `APPLY_LIST.md`.
Offer to add the companies with strong matches to `workspace/watchlist.yaml`.
