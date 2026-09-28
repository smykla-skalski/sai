# kup

Fill the monthly KUP report (Koszty Uzyskania Przychodu, the Polish 50% tax deduction for creative work). The skill collects your merged GitHub pull requests for a month, has the agent write a Polish creative-work description for each, and writes the row to your KUP Google Sheet. It also reads and edits that sheet, or any other Google Sheet shared with the same service account.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex and other compatible agents. It runs on macOS and Linux.

## Installation

Claude Code:

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install kup@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add kup@sai
```

Other agents that read Agent Skills can use `skills/kup/` directly, for example by linking it into `~/.agents/skills/kup`.

Then do the one-time setup in [`skills/kup/references/setup.md`](skills/kup/references/setup.md): GitHub login, a Google service account key, sharing your sheet with it, and `~/.config/kup/config.toml`.

## Usage

Ask in plain words, for example "fill my KUP report", "catch up the KUP sheet" or "preview KUP for 2026-03". In Claude Code, `/kup` works too, and in Codex `$kup`. The agent previews every row before it writes.

## How it works

`skills/kup/scripts/kup.py` does the deterministic part: it finds the month and its row in the sheet, searches GitHub, drops backports and dependency bumps, stores the plan, writes the row and keeps a CSV history in `~/.local/share/kup/`. The agent writes the Polish descriptions following `skills/kup/references/kup-rules.md`. The script's own checks run with `uv run --script skills/kup/scripts/test_kup.py`.

## License

MIT
