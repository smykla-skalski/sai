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
argument-hint: "[--list] [--hunk H1,H2] [--pattern REGEX] [--file PATH] [--range FILE:S-E] [--dry-run]"
allowed-tools: Bash, AskUserQuestion
user-invocable: true
---

# stage-hunk

Non-interactive hunk staging for selective `git add` without a TTY. Replaces `git add -p` in scripted and multi-agent environments.

The heavy lifting happens in the shell script at `$SKILL_DIR/scripts/stage-hunk.sh`. Your first action MUST be Bash - run the script, parse the NDJSON output, present results to the user. Do not re-implement git diff/apply logic yourself.

## Arguments

Parse from `$ARGUMENTS`:

| Flag                | Default | Purpose                                       |
|:--------------------|:--------|:----------------------------------------------|
| `--list`            | -       | List all unstaged hunks with IDs and previews |
| `--hunk H1,H2,...`  | -       | Stage specific hunks by global ID             |
| `--pattern REGEX`   | -       | Stage hunks matching regex content            |
| `--file PATH`       | -       | Stage all hunks for file(s), comma-separated  |
| `--range FILE:S-E`  | -       | Stage hunks overlapping line range            |
| `--dry-run`         | off     | Preview without applying                      |
| `--verify`          | -       | Show staged vs unstaged summary               |

If no mode flag is provided, default to `--list`.

## Workflow

### Phase 1: Setup

1. Parse `$ARGUMENTS` for mode flags and options.
2. Resolve `$SKILL_DIR` for script paths.

### Phase 2: Dependency check

1. Run the script with `--check-deps`:

   ```
   "$SKILL_DIR/scripts/stage-hunk.sh" --check-deps
   ```

2. Parse the NDJSON output. Each line is a dependency status.
3. If the script exits with code 3 (patchutils missing), use AskUserQuestion:
   - Question: "patchutils is not installed. Install it now?"
   - Option 1: "Yes, install" - "Full hunk filtering with grepdiff/filterdiff. Most reliable."
   - Option 2: "No, use fallback" - "Pure-bash parsing. --pattern and --range modes unavailable."
4. If user chooses install:
   - macOS: `brew install patchutils`
   - Debian/Ubuntu: `sudo apt-get install -y patchutils`
   - Detect OS via `uname -s`.
5. If user chooses fallback, pass `--fallback` to all subsequent script calls.
6. If git or python3 are missing, report and stop.

### Phase 3: Execute mode

Run the script with the user's requested mode:

```
"$SKILL_DIR/scripts/stage-hunk.sh" --list
"$SKILL_DIR/scripts/stage-hunk.sh" --hunk H1,H3 --dry-run
"$SKILL_DIR/scripts/stage-hunk.sh" --hunk H1,H3
"$SKILL_DIR/scripts/stage-hunk.sh" --pattern 'handleAuth'
"$SKILL_DIR/scripts/stage-hunk.sh" --file src/auth.ts
"$SKILL_DIR/scripts/stage-hunk.sh" --range src/auth.ts:45-60
"$SKILL_DIR/scripts/stage-hunk.sh" --verify
```

Add `--fallback` if the user declined patchutils in Phase 2.

### Phase 4: Present results

Parse the NDJSON output from the script. Each line is one JSON object.

For `--list` mode, present a table:

| ID  | File         | Lines     | +/- | Preview                       |
|:----|:-------------|:----------|:----|:------------------------------|
| H1  | src/auth.ts  | 45-56     | +4/-2 | `+  function handleAuth() {` |
| H2  | src/auth.ts  | 102-110   | +3/-1 | `+  const token = ...`       |

For staging modes, report each hunk result and the summary.

If the summary includes `"fallback":true`, note that `--pattern` and `--range` modes are unavailable without patchutils.

### Phase 5: Verify (optional)

After staging, optionally run `--verify` to show what ended up staged vs unstaged:

```
"$SKILL_DIR/scripts/stage-hunk.sh" --verify
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

## Error handling

- Empty diff: script outputs `{"error":"no_unstaged_changes"}` and exits 0.
- Invalid hunk IDs: script warns about bad IDs, stages valid ones.
- Apply conflicts: script tries bulk apply first, falls back to per-file, then per-hunk. Each result reported individually.
- Index lock: script detects "Unable to create index.lock" and reports it.
- Binary files: silently skipped during hunk indexing.

## Dependencies

- git (required)
- python3 (required, for JSON encoding)
- patchutils (optional, provides lsdiff/filterdiff/grepdiff)

See `references/patchutils-guide.md` for patchutils usage details.

## Example invocations

```
/stage-hunk --list
/stage-hunk --hunk H1,H3
/stage-hunk --hunk H2 --dry-run
/stage-hunk --pattern 'TODO|FIXME'
/stage-hunk --file src/auth.ts,src/db.ts
/stage-hunk --range src/auth.ts:45-60
/stage-hunk --verify
```
