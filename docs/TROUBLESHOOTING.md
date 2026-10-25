# Troubleshooting

Start with `python3 -m jobhunt doctor`. It checks Chrome, poppler, the Python packages, the registry, your workspace
files and the test suite.

## Resume builds

| Problem | Fix |
|---|---|
| "No Chrome, Chromium or Edge found" | Install Google Chrome, or set `CHROME_PATH` to the browser executable. |
| `pdftotext` not found | macOS: `brew install poppler`. Ubuntu/Debian: `sudo apt install poppler-utils`. Windows: install poppler and add its `bin` to PATH. |
| "Chrome did not produce a PDF in time" | Run the build again; headless Chrome occasionally hangs. |
| `status: overflow` | The content doesn't fit on one page even at the most compact layout. Cut a bullet (the weakest internship first, then the weakest project). |
| `status: underfull` | More than half an inch is empty even at the roomiest layout. Add a bullet or a project. |
| `short_last_lines` | A bullet wraps onto a nearly empty line. The message says how many characters to cut; or add a few words of detail. |
| `lint: text does not extract verbatim near '...'` | Usually an odd character or a word broken across lines. Retype hyphens and quotes in that bullet. |
| A line cut short in the PDF | An unquoted ` #` in `resume.yaml` starts a YAML comment. Quote every string. |
| `No module named 'yaml'` | You're running a different Python than the one you installed packages into. Use `python3 -m pip install -r requirements.txt` with the same `python3`. |

## Fetching jobs

| Problem | Fix |
|---|---|
| `find` exits 2: not in the registry | Read `probe_hits`: the board name and job count must match the real company (names collide). Confirm on the company's careers page, or run `python3 -m jobhunt detect <careers-url>`. Then `python3 -m jobhunt register --name "..." --ats greenhouse --token ...` (Workday also needs `--host --tenant --site`). |
| Registry entry says `unsupported:<platform>` | That hiring system has no adapter (some sit behind bot protection). Check `research/ats_api_reference.md` for a known endpoint and add a fetcher in `jobhunt/ats_extra.py` with `ats.register(...)`. If no API works, list postings with a browser and say the list may be incomplete. |
| Far fewer postings than the careers page shows | A broken adapter or a changed endpoint. Compare `total_fetched` with the site and with `open_jobs_at_check` in the registry. Never accept a partial fetch silently. |
| No posting dates | Some systems give none. The tool records the date it first saw each posting, which is reliable from the second run on. |
| Sweep: some boards failed | They're listed in the run's `fetch_errors.json` and counted at the top of the report. Re-run `find` on those companies. |

## Subagents (screening and reviewing)

| Problem | Fix |
|---|---|
| A subagent stalls or times out | Its output was too big. Re-run just that file. Keep screening files at ~120 titles and review batches at ~15 postings. |
| A fit file has fewer rows than its batch | Re-run that batch. Check counts with `python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" <file>`. |
| Reviewers refuse a posting (defense, weapons) | Re-run the packet; if it repeats, review that batch in the main session. |
| `screen-apply` says titles are still unscreened | A screener skipped ids. They're kept by default (recall first) and reviewed anyway; re-run `screen-prep` and screen the rest if you want them cached. |

## Application history

| Problem | Fix |
|---|---|
| A role you applied to is still on the list | The title in your history doesn't match. Log it with the job id: `python3 -m jobhunt applied add --company ... --title ... --job-id ...`, then `python3 -m jobhunt list`. |
| Email import skipped lines | Each event needs a `YYYY-MM-DD` date, a company and one of applied / rejected / interview / assessment. |
