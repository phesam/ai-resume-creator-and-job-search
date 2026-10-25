# Using this with ChatGPT or Codex instead of Claude Code

Everything here works with any capable coding agent. What you get depends on whether the AI can run commands on
your computer.

| You have | What works | How |
|---|---|---|
| **Claude Code** | Everything | Open the repo folder and say "set me up". The skills in `.claude/skills/` run automatically. |
| **Codex CLI or the Codex app** (included with ChatGPT plans) | Everything | Open the repo folder. Codex reads `AGENTS.md`, which points it at the same step-by-step playbooks (`.claude/skills/*/SKILL.md`). Say "set me up". |
| **ChatGPT in the browser** (no access to your files) | The resume half: inventory interview, bullet workshop, recruiter review, judging one posting | Copy the prompts in [`prompts/`](../prompts) into a chat. Paste your inventory and resume text in. Build the PDF yourself, or run `python3 -m jobhunt resume` locally. |

## Codex notes

- **Subagents.** The Claude Code skills fan screening and reviewing out to parallel subagents. If your Codex setup
  doesn't run subagents, do the same work in the main session, one file at a time: one `screen/titles_XX.md`, then
  write its `screen_XX.txt`; one review batch, then write its `fit/*.json`. Write each result to disk before opening
  the next file. It's slower, not worse.
- **Network.** `find`, `sweep`, `watch` and `fresh` call public job APIs. Allow network access for those commands.
- **Email.** The application-history import needs read access to your email (a Gmail connector or an exported list).
  Without it, log applications with `python3 -m jobhunt applied add`, and duplicate checks use what you logged.

## ChatGPT-in-the-browser notes

- Start with [`prompts/01_inventory_interview.md`](../prompts/01_inventory_interview.md). Keep the inventory it
  produces in a document you own; paste it into every later chat.
- Then [`prompts/02_bullet_workshop.md`](../prompts/02_bullet_workshop.md), one job at a time.
- Then [`prompts/03_recruiter_review.md`](../prompts/03_recruiter_review.md) in a fresh chat, so the reviewer isn't
  anchored on the conversation that wrote the bullets.
- For a single posting you're considering, [`prompts/04_judge_a_posting.md`](../prompts/04_judge_a_posting.md).
- Watch the output for non-breaking hyphens and odd spaces (chat models emit them). The PDF builder here strips the
  problem by checking every build; if you write your resume in a word processor, paste the text into a plain-text
  editor once and retype any hyphen that looks wrong.
