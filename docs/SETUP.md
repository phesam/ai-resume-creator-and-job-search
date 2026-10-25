# Setup, step by step

From a computer with nothing installed to your first "set me up". About 20–30 minutes, most of it installs.
If a step fails, [TROUBLESHOOTING.md](TROUBLESHOOTING.md) has the fixes.

## 0. What you need

| Thing | Why | Required? |
|---|---|---|
| An AI coding agent: **Claude Code** (Claude Pro or Max plan) or **Codex** (included with ChatGPT plans) | It runs the whole workflow: interviews you, writes the resume, reads job postings | Yes, for the full workflow. ChatGPT in the browser alone covers only the resume half ([prompts/](../prompts)). |
| **Python 3.10 or newer** | The `jobhunt` tool | Yes |
| **Google Chrome** (or Chromium or Microsoft Edge) | Turns your resume into a PDF | Yes |
| **poppler** (`pdftotext`) | Checks what screening software reads from the PDF | Yes |
| **git** | Downloads this repository and updates it | Yes (or download the ZIP) |
| An internet connection | Fetches postings from employers' hiring systems | Yes |
| Read-only access to your email (Gmail) | Rebuilds your application history so you never apply twice | Optional |

Built for software engineers job hunting in the United States. Tested on macOS and Linux; on Windows, use WSL
(step 1c).

## 1. Install the basics

### 1a. macOS

1. Install Homebrew if you don't have it: follow the one-line command at [brew.sh](https://brew.sh).
2. In Terminal:
   ```bash
   brew install python git poppler
   ```
3. Install [Google Chrome](https://www.google.com/chrome/) if you don't have it.

### 1b. Linux (Ubuntu or Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git poppler-utils
```
Then install Google Chrome from [google.com/chrome](https://www.google.com/chrome/) (or `sudo apt install chromium`).

### 1c. Windows

The simplest path is WSL, which gives you Ubuntu inside Windows:
1. Open PowerShell as Administrator and run `wsl --install`, then restart.
2. Open "Ubuntu" from the Start menu and follow **1b** inside it.
3. If the PDF build can't find Chrome inside WSL, install it there (`sudo apt install chromium`) or set `CHROME_PATH`.

Native Windows (no WSL) should work but is untested: install Python from
[python.org](https://www.python.org/downloads/) (tick "Add to PATH"), Chrome, git from
[git-scm.com](https://git-scm.com), and a poppler build with its `bin` folder added to PATH.

### Check

```bash
python3 --version     # 3.10 or newer
pdftotext -v          # prints a version
git --version
```

## 2. Install your AI agent

Pick one. Each install guide is the official one; follow it if the command below has changed.

**Claude Code** (needs a Claude Pro or Max plan, or an Anthropic API account):
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Or use the Claude desktop app's Code tab. Guide: [docs.claude.com: Claude Code](https://docs.claude.com/en/docs/claude-code/overview).

**Codex** (included with ChatGPT plans):
```bash
npm install -g @openai/codex      # or: brew install codex
```
(`npm` comes with Node.js from [nodejs.org](https://nodejs.org).)
Sign in with your ChatGPT account the first time you run `codex`. Guide:
[developers.openai.com/codex](https://developers.openai.com/codex).

## 3. Get the code

Copy the repository's URL from the green **Code** button on GitHub, then:
```bash
git clone <the URL you copied>
cd ai-resume-creator-and-job-search
```
(No git? "Download ZIP" from the same button, unzip it, and `cd` into the folder.)

## 4. Install the Python packages

Inside the folder:
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows without WSL: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
```
The `source .venv/bin/activate` line has to be run again in every new terminal before using `python3 -m jobhunt`.
Your AI agent runs commands in its own terminal; if it reports `No module named 'yaml'`, tell it to activate `.venv`
first.

## 5. Create your workspace and check everything

```bash
python3 -m jobhunt init
python3 -m jobhunt doctor
```
- `init` creates `workspace/`, the folder for your own files (inventory, profile, resume, application history,
  search results). Git ignores it, so it never gets uploaded.
- `doctor` should print only `OK` and `TODO` lines. Fix any `FAIL` first (TROUBLESHOOTING.md).
- The three `TODO` lines mean your profile, inventory and resume are still templates. Step 7 fills them in.

## 6. Gather what you'll be asked for

Having these at hand makes the first session much faster:
- Your current resume or LinkedIn "Experience" text (as raw material; the wording will change).
- For each job and project: what it was, why it existed, what *you* did, how big it was, and any numbers you know,
  with what each number measures.
- Where you want to work, best first; the most years a posting can ask for and still be worth it; the kinds of roles
  you'd rather avoid.
- Companies you'd drop everything for, and anyone who will actually refer you (a LinkedIn connection is not a
  referral).
- Your links (LinkedIn, GitHub, portfolio) and your work authorization.

## 7. Start

Open your agent in the repository folder:
- **Claude Code:** `cd` into the folder and run `claude` (or open the folder in the desktop app).
- **Codex:** `cd` into the folder and run `codex`.

Then say:

> set me up

The setup playbook checks your machine, asks about ten questions in one list (you can answer by voice, in any
order), fills in `workspace/profile.yaml`, and starts the interview about your work. From there:

| Say | What happens |
|---|---|
| "interview me" | Every fact about your work, recorded in `workspace/inventory.md` |
| "write my resume" | Bullets one at a time, your approval on each, then a checked one-page PDF |
| "review my resume" | An independent read as software, a recruiter and a hiring manager |
| "I want a job at Acme" | Every Acme posting fetched, read and ranked |
| "every job in Los Angeles I'm a fit for" | The same across about 600 companies |
| "what should I apply to?" | `workspace/APPLY_LIST.md` and a checkbox page |

## 8. Optional extras

- **Email history (recommended).** Connect Gmail to your agent (in Claude, through Settings → Connectors). The
  agent only reads, to find confirmations, rejections and interview invites. Without it, log applications yourself:
  `python3 -m jobhunt applied add --company "Acme" --title "Software Engineer" --url <link>`.
- **Sites that block scripts.** A few career sites refuse automated requests. With Claude in Chrome (the browser
  extension) the agent can read those pages through your browser; otherwise it tells you the list may be incomplete.
- **Fewer permission prompts** in Claude Code: see the top of TROUBLESHOOTING.md.
- **Daily new-postings check:** add your top companies to `workspace/watchlist.yaml` and say "anything new at my
  companies?" each morning, or set it up as a scheduled task.

## 9. How much it uses your plan

The resume work is ordinary conversation. Job searches use more, because AI subagents read the postings:
- One company: one screener per ~120 titles and one reviewer per ~30–45 postings. A small company takes a few
  minutes; a company with thousands of postings takes a dozen or more subagents.
- A sweep across every registered company is the heaviest run. Try it first with `--limit 20` or a `--category`.
- Repeat runs are cheap: titles and locations already screened are cached, and unchanged postings keep their reviews.

## 10. Keeping it up to date

```bash
git pull
python3 -m pip install -r requirements.txt
python3 -m jobhunt doctor
```
Your `workspace/` folder is never touched by an update.
