# Output format reference

All script output is NDJSON (one JSON object per line). The final line is
always a summary with `"summary":true`. When `--table` is passed, output
is a pre-formatted markdown table instead.

## Table of contents

- [NDJSON schemas](#ndjson-schemas)
- [Table output (--table)](#table-output---table)

## NDJSON schemas

### List mode

Per hunk:

```json
{"id":"H1","file":"src/auth.ts","hunk_num":1,"old_start":45,"old_count":8,"new_start":45,"new_count":12,"added":4,"removed":2,"preview":"+  function handleAuth() {"}
```

### Stage mode

Per hunk on success:

```json
{"id":"H1","file":"src/auth.ts","action":"staged","status":"ok"}
```

Per hunk on failure:

```json
{"id":"H2","file":"src/auth.ts","action":"stage_failed","status":"error","detail":"patch does not apply"}
```

Dry run:

```json
{"id":"H1","file":"src/auth.ts","action":"would_stage","status":"dry_run"}
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

### Verify mode

Overall counts:

```json
{"staged_files":2,"unstaged_files":3,"staged_hunks":4,"unstaged_hunks":8}
```

Per file:

```json
{"file":"src/auth.ts","staged_hunks":2,"unstaged_hunks":3}
```

### Summary

Staging summary (hunk/file/pattern/range modes):

```json
{"summary":true,"total_hunks":5,"staged":3,"failed":0,"dry_run":false,"fallback":false}
```

List summary:

```json
{"summary":true,"total_hunks":5,"mode":"list","fallback":false}
```

### Dependency check

```json
{"dep":"patchutils","found":false,"install":"brew install patchutils (macOS) or apt install patchutils (Debian/Ubuntu)"}
```

### Error objects

Empty diff:

```json
{"error":"no_unstaged_changes","detail":"git diff is empty"}
```

No hunks for file filter:

```json
{"error":"no_hunks_for_file","detail":"no unstaged hunks match the file filter"}
```

Index locked:

```json
{"error":"index_locked","detail":"...git error..."}
```

## Table output (--table)

When `--table` is passed, the script outputs pre-formatted markdown tables
instead of NDJSON. The format is self-explanatory when displayed.

List mode table columns: ID, File, Lines, +/-, Preview.
Stage mode table columns: ID, File, Status.
Verify mode table columns: File, Staged, Unstaged.

Each table ends with a plain-text summary line.
