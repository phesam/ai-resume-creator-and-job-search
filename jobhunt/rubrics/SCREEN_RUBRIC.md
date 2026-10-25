# Screening rubric (titles and locations)

You are screening job titles and location strings for one candidate. First read the run's `screen/BRIEF.md`: it
says who the candidate is, which kinds of roles to keep, and the location region keys to use.

The code has already removed internships, staff/principal/director/manager titles, postings that list only foreign
countries, and postings that explicitly require more years than the candidate's limit, an active clearance they lack,
or a PhD. **Your job is recall first:** a reviewer reads every kept posting in full later, so when in doubt, KEEP.
A wrong drop is invisible forever; a wrong keep costs one reviewer a minute.

## Titles: one decision per id

- `keep software`: any role whose core work matches the brief's "roles to keep". For a software engineer that
  includes software, full-stack, frontend, backend, platform, infrastructure, SRE/DevOps, data or ML engineering, AI
  engineering, embedded and firmware *software*, flight/ground/mission software, autonomy/robotics software,
  simulation, tools, test automation/SDET, security engineering with coding, developer experience, forward-deployed
  and solutions engineers who write code, and new-grad/early-career/rotational programs in that field.
- `keep adjacent`: roles where the candidate's core skill is a substantial part but not the center. For a software
  engineer: systems engineering on software-defined products, integration and test with scripting, technical
  operations for software systems, analytics engineers who write SQL/Python, controls engineers who mainly program,
  entry-level technical program roles.
- `drop <3-8 word reason>`: everything else (other engineering disciplines without that skill, technicians and
  trades, operations, supply chain, finance, legal, HR/recruiting, sales/marketing, support, facilities, program or
  project management, analysts who don't code).
- The regex hint at the end of each line is only a hint; ignore it when the title says otherwise. Use the
  department/team column: it often decides ("Engineer II" in a Software department → keep).
- Never drop a title only because it is unfamiliar or company jargon ("Mission Engineer", "Discovery Engineer",
  "Member of Technical Staff"). Keep it; the reviewer will read the posting.
- Do not drop for seniority words ("Senior", "II", "Lead" was already handled by code). Do not drop for location.

## Locations: one region key per string

Use only the keys listed in `screen/BRIEF.md` (the candidate's own regions plus `remote_us`, `other_us`, `non_us`,
`unknown`). Read the whole string: "Ontario, California" is in California, "Toronto, Ontario" is in Canada;
"Remote - US" is `remote_us`, "Remote - Canada" is `non_us`; "Hybrid" alone is `unknown`. A bare country with no
city ("United States", "USA") means US-wide: `remote_us` (the reviewer corrects it if the posting names an office).
A city that belongs to none of the candidate's regions is `other_us`. When a region's `covers` line names a town,
that region wins.

## Output format (compact text: keep your output short)

Write a plain-text file (the path you were given, ending in `.txt`) with ONE line per title id:
```
G0001 keep software
G0002 keep adjacent
G0003 drop mechanical design, no coding
```
and, if you were also given `locations.md`, one line per location string:
```
L Costa Mesa, California, United States => home
L Remote - US => remote_us
```
Every id in your titles file (and every location string, if assigned) must appear exactly once. Write the file
with one `cat > file <<'EOF' ... EOF` command or the Write tool, then check the count with
`grep -c '^G' <file>`: it must equal the number of G-ids in the titles file.
