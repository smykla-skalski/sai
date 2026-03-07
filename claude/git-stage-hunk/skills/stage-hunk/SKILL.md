---
name: stage-hunk
description: >-
  Stage only your changes when a file has edits from multiple sessions
  or agents. Commit part of a file without git add -p. Works without
  a TTY. Use when the working tree has mixed changes and you need to
  commit selectively - list hunks, pick by ID or file or pattern,
  then commit. Non-interactive partial staging, selective git add,
  split hunks, stage by line range.
argument-hint: "[--list [--file PATH] [--split] [--table]] [--hunk H1,H3.1,H5:5-10] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--verify] [--dry-run] [--table]"
allowed-tools: AskUserQuestion, Bash
user-invocable: true
disable-model-invocation: true
---

# stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Replaces `git add -p` in scripted and multi-agent environments.

This skill has `disable-model-invocation: true` - it is only invoked by the user. The heavy lifting happens in the shell script. Your first action MUST be Bash - call the script directly, then present the output. Do not re-implement git diff/apply logic yourself.

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --table
```

## Quick workflow

1. List hunks:

   ```
   "${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --table
   ```

2. Stage the ones you want:

   ```
   "${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3 --table
   ```

3. Commit, then re-list to see what remains.

**WARNING: Hunk IDs shift after staging or committing.** Always re-list before using IDs from a previous run.

Filter the listing to one file:

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --file src/auth.ts --table
```

## Preprocessed context

- OS: !`uname -s`

## Arguments

Parse from `$ARGUMENTS`:

| Flag                     | Default | Purpose                                          |
|:-------------------------|:--------|:-------------------------------------------------|
| `--list`                 | -       | List all unstaged hunks with IDs and previews    |
| `--list --file PATH`     | -       | List hunks filtered to file(s), comma-separated  |
| `--list --split`         | -       | List all hunks with sub-hunk breakdown           |
| `--split H3`             | -       | Show sub-hunks for one specific hunk             |
| `--hunk H1,H2,...`       | -       | Stage specific hunks by global ID                |
| `--hunk H3.1,H3.2`      | -       | Stage sub-hunks by dot-notation ID               |
| `--hunk H3:5-10`         | -       | Stage hunk-relative lines 5-10 of H3            |
| `--pattern REGEX`        | -       | Stage hunks matching regex content               |
| `--file PATH`            | -       | Stage all hunks for file(s), comma-separated     |
| `--range FILE:S-E`       | -       | Stage hunks overlapping line range               |
| `--table`                | off     | Output as markdown table (default is NDJSON)     |
| `--dry-run`              | off     | Preview without applying                         |
| `--verify`               | -       | Show staged vs unstaged summary                  |

`--file` has dual behavior: with `--list` it filters the listing, without `--list` it stages all hunks for that file. If no mode flag is provided, default to `--list`.

## Workflow

### Phase 1: Setup

1. Parse `$ARGUMENTS` for mode flags and options.

### Phase 2: Dependency check

1. Run the script with `--check-deps`:

   ```
   "${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --check-deps
   ```

2. Parse the NDJSON output. Each line is a dependency status.
3. If the script exits with code 3 (patchutils missing), use AskUserQuestion:
   - Question: "patchutils is not installed. Install it now?"
   - Option 1: "Yes, install" - "Full hunk filtering with grepdiff/filterdiff. Most reliable."
   - Option 2: "No, use fallback" - "Pure-bash parsing. --pattern and --range modes unavailable."
4. If user chooses install, use the OS value from Preprocessed context:
   - Darwin: `brew install patchutils`
   - Linux: `sudo apt-get install -y patchutils`
5. If user chooses fallback, pass `--fallback` to all subsequent script calls.
6. Read [references/patchutils-guide.md](references/patchutils-guide.md) for patchutils command reference before advising on installation.
7. If git or python3 are missing, report and stop.

### Phase 3: Execute mode

Run the script with the user's requested mode. Always pass `--table` for human-readable output:

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --file src/auth.ts --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --split --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --split H3
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3 --dry-run --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3 --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H3.1,H3.2 --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H3:5-10 --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --pattern 'handleAuth' --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --file src/auth.ts --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --range src/auth.ts:45-60 --table
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --verify --table
```

Add `--fallback` if the user declined patchutils in Phase 2.

Mixed hunk IDs are supported in a single `--hunk` call: plain IDs (H1), sub-hunk IDs (H3.2), and line-select IDs (H5:10-15) are processed in separate batches internally.

### Phase 4: Present results

With `--table`, output is already formatted as a markdown table. Present directly.

For NDJSON output (no `--table`), read [references/output-format.md](references/output-format.md) for the schema of each mode.

If the summary includes `"fallback":true`, note that `--pattern` and `--range` modes are unavailable without patchutils.

### Phase 5: Verify (optional)

After staging, optionally run `--verify` to show what ended up staged vs unstaged:

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --verify --table
```

## Hunk ID scheme

**WARNING: Hunk IDs shift after staging or committing.** Always re-list before using IDs from a previous run.

Global sequential IDs: H1, H2, H3, ... assigned by alphabetical file order, then position within each file. Stable within a single diff snapshot.

### Sub-hunk IDs

Format: `H{parent}.{sub}` where parent is the global hunk number and sub is 1-indexed within the parent. Example: H3.1, H3.2, H3.3.

Sub-hunks are derived by re-running the diff with `--inter-hunk-context=0 --unified=0` to produce the finest possible hunks, then mapping fine hunks back to their parent's line range.

Sub-hunks are terminal - no recursive splitting. Use line-select (`H3:5-10`) for finer control within any hunk.

### Line-select IDs

Format: `H{id}:{start}-{end}` where start and end are 1-based line numbers relative to the hunk body (line 1 = first line after the @@ header). Example: H3:5-10.

Read [references/split-hunk-guide.md](references/split-hunk-guide.md) for splitting mechanics, header recalculation, and edge cases.

## Error handling

- Empty diff: script outputs `{"error":"no_unstaged_changes"}` and exits 0.
- Invalid hunk IDs: script warns about bad IDs, stages valid ones.
- Apply conflicts: script tries bulk apply first, falls back to per-file, then per-hunk. Each result reported individually.
- Index lock: script detects "index.lock" in git apply stderr and emits `{"error":"index_locked"}`.
- Binary files: silently skipped during hunk indexing.
- Not splittable: `--split H3` returns `{"splittable":false}` with suggestion to use line-select. Not an error.

## Dependencies

- git (required)
- python3 (required, for JSON encoding and `scripts/split-hunk.py` sub-hunk extraction)
- patchutils (optional, provides lsdiff/filterdiff/grepdiff)

Read [references/patchutils-guide.md](references/patchutils-guide.md) for patchutils usage details.

## Example invocations

```
/stage-hunk --list --table
/stage-hunk --list --file src/auth.ts --table
/stage-hunk --list --split --table
/stage-hunk --split H3
/stage-hunk --hunk H1,H3 --table
/stage-hunk --hunk H2 --dry-run --table
/stage-hunk --hunk H3.1,H3.2 --table
/stage-hunk --hunk H3:5-10 --table
/stage-hunk --hunk H1,H3.2,H5:10-15 --table
/stage-hunk --pattern 'TODO|FIXME' --table
/stage-hunk --file src/auth.ts,src/db.ts --table
/stage-hunk --range src/auth.ts:45-60 --table
/stage-hunk --verify --table
```
