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

With the key in 1Password, the first command that touches the sheet asks the user to approve 1Password once. It then keeps a Google access token, never the key, in `~/.cache/kup/google-token.json` for up to an hour, so the rest of the run asks nothing. Tell the user to expect that one prompt, and run the first sheet command on its own rather than in parallel, because 1Password denies a second prompt while one is open.

If a command reports a missing config, missing credentials or an unshared spreadsheet, read `references/setup.md` and walk the user through it.

## Inputs

Take these from the user's request:

- Month as `YYYY-MM`. Without one, the script picks the oldest month missing from the sheet, up to the current month after the 20th or the previous month before it.
- Dry run: preview only, nothing is written to the sheet.
- Force: replace a month that is already in the sheet without asking.

## Workflow

### 1. Plan

```bash
uv run --quiet --script scripts/kup.py plan [--month YYYY-MM]
```

- `up_to_date: true` means no month is missing. Say so and stop.
- `missing` lists every month without a row. Handle one month per pass, oldest first. If the user asked to catch up, repeat the whole workflow for each month.
- `existing: true` means the month already has row `row`. Unless the user asked for a dry run or to force it, ask whether to replace it and stop if they say no.
- `fetched` is the raw PR count and `skipped` counts what triage dropped, by reason.
- `to_describe` lists the included PRs, `{url, title}` with the conventional commit prefix and backport markers already stripped. If it is empty, tell the user the month has no PRs and ask whether to record it as empty, which keeps later runs from stopping at it. If they agree, go to step 3.
- `dependency_only: true` means every PR was a dependency update, so all of them stay in.

### 2. Describe

Write one Polish description per PR in `to_describe`, following `references/kup-rules.md` and the style rules below. Keep each description within `max_description_chars`, because a Google Sheets cell holds at most 50,000 characters. When `dependency_only` is true, describe the upgrade strategy, the compatibility analysis and the integration checks, not the version bump.

Save descriptions in batches of up to 50:

```bash
uv run --quiet --script scripts/kup.py describe --month YYYY-MM --input - <<'EOF'
{"https://github.com/org/repo/pull/123": "Opracowanie mechanizmu walidacji stref DNS w systemie zarządzania konfiguracją sieciową"}
EOF
```

Each call merges into the saved plan, so work can stop and resume. Run `describe --month YYYY-MM` without `--input` to list what is still missing. The script refuses unknown URLs, empty or multi-line descriptions, and strips trailing periods.

For a large month, agents that can run subagents may split `to_describe` into batches and let each subagent call `describe` for its own batch. Give each subagent the full text of `references/kup-rules.md` and the style rules inline. Afterwards, read all descriptions together and fix phrasing that repeats across batches.

Style rules for the descriptions:

- No significance inflation, promotional language or vague attributions.
- No AI vocabulary: dodatkowo, kluczowy, kompleksowy, innowacyjny, wszechstronny, zaawansowany used as filler, nor their English cousins (crucial, delve, enhance, foster, pivotal, robust, seamless, showcase, leverage).
- Plain verbs over copula avoidance, no forced groups of three, the same word for the same concept.
- Sentence case, straight quotes, no em dashes, no emoji, no bold.
- No "w celu" filler, one qualifier per claim at most, no generic conclusions.
- Vary the opening verb and sentence rhythm across the month.

### 3. Preview and write

Always preview first:

```bash
uv run --quiet --script scripts/kup.py write --month YYYY-MM --dry-run
```

Show the user the target row and column B. Then write, adding `--force` only when replacing an existing month the user agreed to replace:

```bash
uv run --quiet --script scripts/kup.py write --month YYYY-MM [--force]
```

The write refuses a row that holds other data, refuses to replace an existing month without `--force`, and refuses cells over the Google Sheets limit. Both the dry run and the real write replace that month's rows in `~/.local/share/kup/pr-history.csv` with every fetched PR, including skipped ones and why they were skipped.

### 4. Report

Tell the user the month, the row, how many PRs were included and skipped by reason, the sheet URL, the CSV path, and which months are still missing.

## How the script triages

- Backports: PRs in the same repository with the same conventional commit scope and the same title once backport markers (`[backport release-x]`, `(backport)`, `backport ... to release-x`) are removed count as one. It keeps the one without a marker, otherwise the lowest PR number, and skips the rest as `backport_duplicate`. A PR titled `backport of #N` or `bp N` is skipped the same way when PR N of the same repository is in the month.
- Dependency updates: a `chore`, `build`, `fix` or `revert` commit scoped `deps`, or a title that bumps, updates or upgrades something to or from a version. These are skipped as `dependency_filtered`, unless the whole month is dependency updates.
- Search: one GitHub search per organization, split into shorter date ranges when one hits the 1,000-result cap. When GitHub rate-limits the search, the script waits and retries on its own for up to six minutes, printing `waiting` lines to stderr, so a large month's `plan` can take a while.
- Rows: one row per month in column A. A new month goes at the row of the last earlier month plus the months between them, so gap rows stay empty for backfilling.
- Columns: A is the month label (`March 2026`), B the descriptions, C the sorted unique repository URLs, D the PR URLs in the same order as B.

## Sheet access

`kup.py sheet` reads and edits a sheet directly, for checking the report or fixing a cell by hand. It defaults to the spreadsheet and tab from the config. `--spreadsheet <ID or URL>` and `--tab <name>` point it at any other sheet shared with the same service account. Tab names are case-sensitive, so run `list` first when unsure.

```bash
uv run --quiet --script scripts/kup.py sheet list   [--spreadsheet ID_OR_URL]
uv run --quiet --script scripts/kup.py sheet read   [--spreadsheet ...] [--tab NAME] [--range A45:D52]
uv run --quiet --script scripts/kup.py sheet write  [--spreadsheet ...] [--tab NAME] --cell B3 --value "done" [--user-entered]
uv run --quiet --script scripts/kup.py sheet append [--spreadsheet ...] [--tab NAME] --row '["Alice","done"]' [--after-col A] [--user-entered]
uv run --quiet --script scripts/kup.py sheet clear  [--spreadsheet ...] [--tab NAME] [--range A2:D100]
```

- `read` prints rows as a 2D array of strings with the computed values of formulas. Show them to the user as a table.
- Values are stored as typed text by default. `--user-entered` parses them the way the Sheets UI does, which turns `=SUM(A1:A3)` into a formula and `2026-02-26` into a date.
- `append` without `--after-col` goes below the last row holding data in any column. `--after-col A` goes below the last filled cell of column A instead, which is safer when other columns hold stray data.
- `clear` without `--range` empties the whole tab. Confirm with the user before running it, and before any `write` or `clear` on the KUP tab outside the monthly workflow.
