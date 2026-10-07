---
name: kup
description: Fill the monthly KUP report (Koszty Uzyskania Przychodu, the Polish 50% tax deduction for creative work) - collects the user's merged GitHub pull requests for a month, writes a Polish creative-work description for each, and records them in the KUP Google Sheet. Also reads and edits the KUP sheet, or any Google Sheet shared with the same service account, cell by cell. Use when the user asks to update, fill, catch up, preview or fix the KUP report or sheet, wants a monthly summary of their work for KUP, or wants to read or change a Google Sheet.
license: MIT
compatibility: Needs uv, the gh CLI logged in to GitHub, network access to GitHub and Google Sheets, and a Google service account key. macOS or Linux.
allowed-tools: Bash Read
---


# KUP monthly report

`scripts/kup.py` does everything deterministic: it reads the sheet, picks the month and its row, searches GitHub, drops backports and dependency bumps, stores the plan, writes the row and keeps a CSV history. Your part is the Polish descriptions and talking to the user. For direct sheet reads and edits outside the monthly workflow, see [Sheet access](#sheet-access).

Paths here are relative to this skill's directory. Run the script as `uv run --quiet --script <skill dir>/scripts/kup.py <command>`. Every command prints JSON to stdout, and on failure prints `{"error": ...}` to stderr and exits 1.

The commands need network access (GitHub, Google, PyPI on the first run) and write to `~/.cache/uv`, `~/.cache/kup`, `~/.local/state/kup` and `~/.local/share/kup`. In a sandboxed agent, run them with escalated permissions or outside the sandbox (in Codex, request escalation for these commands).

With the key in 1Password, the first command that touches the sheet asks the user to approve 1Password once. It then keeps a Google access token, never the key, in `~/.cache/kup/google-token.json` for up to an hour, so the rest of the run asks nothing. Tell the user to expect that one prompt, and.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Inputs
2. Workflow
3. How the script triages
4. Sheet access

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
