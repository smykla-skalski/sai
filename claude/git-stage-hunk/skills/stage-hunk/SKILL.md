---
name: stage-hunk
description: >-
  Commit only some changes from a file, split a mixed diff into
  separate commits, or avoid committing unrelated changes.
  Use when multiple agents or sessions modified the same file,
  when you need to separate changes from different tasks into
  distinct commits, or when you want to selectively stage
  functions or blocks. Non-interactive alternative to git add -p
  for scripted and non-TTY environments. Also for partial staging,
  stage specific hunks, or selective git add by pattern, file,
  or line range.
argument-hint: "[--list [--split]] [--split H3] [--hunk H1,H3.1,H5:5-10] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--verify] [--dry-run]"
allowed-tools: AskUserQuestion, Bash
user-invocable: true
disable-model-invocation: true
---

# stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Replaces `git add -p` in scripted and multi-agent environments.

The heavy lifting happens in the shell script at `${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh`. Your first action MUST be Bash - run the script, parse the NDJSON output, present results to the user. Do not re-implement git diff/apply logic yourself.

## Preprocessed context

- OS: !`uname -s`

## Arguments

Parse from `$ARGUMENTS`:

| Flag                | Default | Purpose                                          |
|:--------------------|:--------|:-------------------------------------------------|
| `--list`            | -       | List all unstaged hunks with IDs and previews    |
| `--list --split`    | -       | List all hunks with sub-hunk breakdown           |
| `--split H3`        | -       | Show sub-hunks for one specific hunk             |
| `--hunk H1,H2,...`  | -       | Stage specific hunks by global ID                |
| `--hunk H3.1,H3.2`  | -       | Stage sub-hunks by dot-notation ID               |
| `--hunk H3:5-10`    | -       | Stage hunk-relative lines 5-10 of H3            |
| `--pattern REGEX`   | -       | Stage hunks matching regex content               |
| `--file PATH`       | -       | Stage all hunks for file(s), comma-separated     |
| `--range FILE:S-E`  | -       | Stage hunks overlapping line range               |
| `--dry-run`         | off     | Preview without applying                         |
| `--verify`          | -       | Show staged vs unstaged summary                  |

If no mode flag is provided, default to `--list`.

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

Run the script with the user's requested mode:

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --list --split
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --split H3
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3 --dry-run
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H3.1,H3.2
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H3:5-10
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --hunk H1,H3.2,H5:10-15
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --pattern 'handleAuth'
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --file src/auth.ts
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --range src/auth.ts:45-60
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --verify
```

Add `--fallback` if the user declined patchutils in Phase 2.

Mixed hunk IDs are supported in a single `--hunk` call: plain IDs (H1), sub-hunk IDs (H3.2), and line-select IDs (H5:10-15) are processed in separate batches internally.

### Phase 4: Present results

Parse the NDJSON output from the script. Each line is one JSON object.

For `--list` mode, present a table:

| ID  | File         | Lines     | +/- | Preview                       |
|:----|:-------------|:----------|:----|:------------------------------|
| H1  | src/auth.ts  | 45-56     | +4/-2 | `+  function handleAuth() {` |
| H2  | src/auth.ts  | 102-110   | +3/-1 | `+  const token = ...`       |

For `--list --split` mode, present a hierarchical table. Parent hunks show `splittable` status and sub-hunk count. Sub-hunks are indented under their parent:

| ID    | File         | Lines   | +/-   | Preview                       |
|:------|:-------------|:--------|:------|:------------------------------|
| H1    | src/auth.ts  | 45-80   | +8/-4 | `+  function handleAuth() {` |
|  H1.1 | src/auth.ts  | 45-52   | +3/-1 | `+  function handleAuth() {` |
|  H1.2 | src/auth.ts  | 70-80   | +5/-3 | `+  validateToken(tok) {`    |
| H2    | src/auth.ts  | 102-110 | +3/-1 | (not splittable)             |

For `--split H3` mode, present the sub-hunks for that specific hunk. If `"splittable":false`, suggest using `--hunk H3:START-END` for line-level selection instead.

For staging modes, report each hunk result and the summary.

If the summary includes `"fallback":true`, note that `--pattern` and `--range` modes are unavailable without patchutils.

### Phase 5: Verify (optional)

After staging, optionally run `--verify` to show what ended up staged vs unstaged:

```
"${CLAUDE_SKILL_DIR}/scripts/stage-hunk.sh" --verify
```

Present the staged/unstaged breakdown per file.

## Script output format

All output is NDJSON (one JSON object per line). The final line is always a summary object with `"summary":true`.

### List mode

Per hunk:
```json
{"id":"H1","file":"src/auth.ts","hunk_num":1,"old_start":45,"old_count":8,"new_start":45,"new_count":12,"added":4,"removed":2,"preview":"+  function handleAuth() {"}
```

### Stage mode

Per hunk:
```json
{"id":"H1","file":"src/auth.ts","action":"staged","status":"ok"}
```

On failure:
```json
{"id":"H2","file":"src/auth.ts","action":"stage_failed","status":"error","detail":"patch does not apply"}
```

### Split mode

Per sub-hunk (when splittable):
```json
{"id":"H3.1","parent":"H3","file":"src/auth.ts","old_start":45,"old_count":2,"new_start":45,"new_count":3,"added":1,"removed":0,"preview":"+  new line"}
```

When not splittable:
```json
{"parent":"H3","splittable":false,"reason":"single_hunk","suggestion":"use H3:START-END for line-level selection"}
```

### List-split mode

Parent hunks include split info:
```json
{"id":"H1","file":"src/auth.ts","hunk_num":1,"old_start":45,"old_count":36,"new_start":45,"new_count":40,"added":8,"removed":4,"preview":"+  ...","splittable":true,"sub_hunks":2}
```

Summary includes split counts:
```json
{"summary":true,"total_hunks":5,"splittable_hunks":2,"total_sub_hunks":5,"mode":"list-split","fallback":false}
```

### Summary

```json
{"summary":true,"total_hunks":5,"staged":3,"failed":0,"dry_run":false,"fallback":false}
```

### Dependency check

```json
{"dep":"patchutils","found":false,"install":"brew install patchutils (macOS) or apt install patchutils (Debian/Ubuntu)"}
```

## Hunk ID scheme

Global sequential IDs: H1, H2, H3, ... assigned by alphabetical file order, then position within each file. Stable within a single diff snapshot - IDs shift if files are added/removed between invocations.

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
- Index lock: script detects "index.lock" in git apply stderr and emits `{"error":"index_locked"}` NDJSON.
- Binary files: silently skipped during hunk indexing.
- Sub-hunk not found: Python helper emits `{"error":"sub_hunk_not_found"}` to stderr.
- Line range out of bounds: Python helper emits `{"error":"line_range_out_of_bounds"}` to stderr.
- No changes in range: Python helper emits `{"error":"no_changes_in_range"}` to stderr.
- Not splittable: `--split H3` returns `{"splittable":false}` with suggestion to use line-select. Not an error.

## Dependencies

- git (required)
- python3 (required, for JSON encoding and `scripts/split-hunk.py` sub-hunk extraction)
- patchutils (optional, provides lsdiff/filterdiff/grepdiff)

Read [references/patchutils-guide.md](references/patchutils-guide.md) for patchutils usage details.

## Example invocations

```
/stage-hunk --list
/stage-hunk --list --split
/stage-hunk --split H3
/stage-hunk --hunk H1,H3
/stage-hunk --hunk H2 --dry-run
/stage-hunk --hunk H3.1,H3.2
/stage-hunk --hunk H3:5-10
/stage-hunk --hunk H1,H3.2,H5:10-15
/stage-hunk --pattern 'TODO|FIXME'
/stage-hunk --file src/auth.ts,src/db.ts
/stage-hunk --range src/auth.ts:45-60
/stage-hunk --verify
```
