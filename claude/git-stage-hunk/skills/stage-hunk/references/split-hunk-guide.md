# Split hunk reference

## Contents

- [Zero-context splitting](#zero-context-splitting)
- [Sub-hunk ID scheme](#sub-hunk-id-scheme)
- [Line-select semantics](#line-select-semantics)
- [Header recalculation](#header-recalculation)
- [The split-hunk.py helper](#the-split-hunkpy-helper)
- [Edge cases](#edge-cases)
- [Apply flags](#apply-flags)

## Zero-context splitting

Normal `git diff` merges nearby changes into one hunk when they share overlapping context (default 3 lines). Two independent edits 5 lines apart appear as a single hunk.

Setting `--inter-hunk-context=0 --unified=0` produces the finest possible hunks. Each contiguous block of changed lines becomes its own hunk with zero context lines. This is "Tier 1" splitting - it works when independent changes are a few lines apart but git merged them.

Before (default diff - one hunk):

```diff
--- a/src/config.ts
+++ b/src/config.ts
@@ -10,12 +10,12 @@
   const timeout = 30;
   const retries = 3;
-  const host = "localhost";
+  const host = "0.0.0.0";
   const port = 8080;
   const debug = false;
   const verbose = true;
-  const logLevel = "info";
+  const logLevel = "debug";
   const format = "json";
```

After (`--inter-hunk-context=0 --unified=0` - two hunks):

```diff
--- a/src/config.ts
+++ b/src/config.ts
@@ -12,1 +12,1 @@
-  const host = "localhost";
+  const host = "0.0.0.0";
@@ -17,1 +17,1 @@
-  const logLevel = "info";
+  const logLevel = "debug";
```

Each change is now independently stageable.

## Sub-hunk ID scheme

Format: `H{parent}.{sub}` where parent is the global hunk number and sub is 1-indexed within the parent.

Examples: `H3.1`, `H3.2`, `H7.1`.

IDs are stable within a single diff snapshot. They shift if the working tree changes between invocations (same behavior as parent IDs).

Sub-hunks are terminal - no recursive splitting. If a sub-hunk still contains mixed changes on consecutive lines, use line-select for finer control.

All ID types are mixable in one `--hunk` call:

```
--hunk H1,H3.2,H5:10-15
```

This stages parent hunk H1, sub-hunk H3.2, and lines 10-15 of hunk H5 in a single operation.

## Line-select semantics

For truly unsplittable hunks (all changed lines are consecutive), the user can pick a line range within the hunk body:

```
--hunk H3:5-10
```

Lines are 1-based, relative to the hunk body. Line 1 is the first line after the `@@` header.

Transformation rules for non-selected lines:

- Non-selected `+` lines are dropped. They don't exist in the old file (index), so they can't appear as context.
- Non-selected `-` lines become context lines (leading `-` replaced with space). They exist in the old file and git apply needs them for position matching.
- Context lines (lines starting with space) from the original hunk are always preserved.

Example - hunk body with lines numbered:

```
1:  const a = 1;        (context)
2: -const b = 2;        (removal)
3: +const b = 3;        (addition)
4: +const c = 4;        (addition)
5: +const d = 5;        (addition)
6:  const e = 6;        (context)
```

With `--hunk H1:1-3`, lines 4-5 are outside the range:

```
1:  const a = 1;        (context, kept)
2: -const b = 2;        (removal, kept)
3: +const b = 3;        (addition, kept)
                        (lines 4-5 were +, dropped)
4:  const e = 6;        (context, kept)
```

## Header recalculation

Both sub-hunk extraction and line-select produce partial patches that need recalculated `@@` headers.

The `@@` header format: `@@ -old_start,old_count +new_start,new_count @@`

Rules:

- `old_start` and `new_start` come from the original hunk (adjusted for sub-hunk offset)
- `old_count` = number of context lines + number of `-` lines in the final body
- `new_count` = number of context lines + number of `+` lines in the final body

Example - extracting a sub-hunk:

Original hunk `@@ -10,8 +10,9 @@` gets split. The second sub-hunk starts at what was originally line 15 in the old file and line 16 in the new file. It has 1 context line, 1 removal, 1 addition:

```
old_count = 1 (context) + 1 (removal) = 2
new_count = 1 (context) + 1 (addition) = 2
```

Result: `@@ -15,2 +16,2 @@`

Example - line-select dropping non-selected additions:

Original hunk `@@ -10,4 +10,6 @@` has 2 context, 1 removal, 3 additions. After line-select keeps only 1 addition, the other 2 are dropped (they don't exist in the old file):

```
old_count = 2 (context) + 1 (removal) = 3
new_count = 2 (context) + 1 (addition) = 3
```

Result: `@@ -10,3 +10,3 @@`.

## The split-hunk.py helper

Three modes, all invoked via the script path:

### --find-subhunks

Input: normal diff and fine diff (zero-context), null-byte separated on stdin. Plus `--parent-id` and `--parent-range` (old start/end lines) as arguments.

Finds which fine hunks fall within the parent hunk's line range. Outputs NDJSON to stdout:

```json
{"parent":"H3","sub":1,"id":"H3.1","old_start":12,"old_count":1,"new_start":12,"new_count":1,"splittable":true}
{"parent":"H3","sub":2,"id":"H3.2","old_start":17,"old_count":1,"new_start":17,"new_count":1,"splittable":true}
```

### --extract-patch

Input: fine diff on stdin. Arguments: `--sub-id H3.2`, `--file-header` (the `--- a/` and `+++ b/` lines).

Extracts the matching fine hunk and outputs a complete patch to stdout, ready for `git apply`.

### --line-select

Input: normal diff on stdin. Arguments: `--hunk-id H3`, `--lines 5-10`, `--file-header`.

Constructs a partial patch by applying the line-select transformation rules. Non-selected `+` lines are dropped, non-selected `-` lines become context. Recalculates the `@@` header. Outputs a complete patch to stdout.

### Error output

All errors go to stderr as JSON:

```json
{"error":"sub_hunk_not_found","id":"H3.5","max_sub":2}
```

## Edge cases

- **Not splittable**: parent hunk maps to only 1 fine hunk. Output includes `"splittable":false`. Suggest line-select to the user instead.
- **Line range covers entire hunk**: works normally, logs `"note":"full_hunk_selected"` in the output.
- **Line range has no changes**: error `no_changes_in_range`. The selected range contained only context lines.
- **Line range out of bounds**: error `line_range_out_of_bounds`. Includes `max_line` in the error object.
- **Sub-hunk index out of range**: error `sub_hunk_not_found`. Includes `max_sub` in the error object.
- **Pure additions (no old lines)**: the parent hunk has no `-` lines, only `+` lines. Overlap check between parent and fine hunks uses new-file line ranges instead of old-file ranges.
- **Fallback mode (no patchutils)**: split works because the zero-context diff comes from `git diff` directly, not patchutils. The Python helper extracts and constructs patches without any patchutils dependency.

## Apply flags

Different ID types produce patches with different context characteristics:

| ID type      | Apply command                            | Reason                                  |
| ------------ | ---------------------------------------- | --------------------------------------- |
| Sub-hunk     | `git apply --cached --unidiff-zero`      | Zero context lines from fine diff       |
| Plain hunk   | `git apply --cached`                     | Normal context from standard diff       |
| Line-select  | `git apply --cached`                     | Preserves original context structure    |

Mixed IDs in one `--hunk` call are processed in separate batches. Sub-hunks go first with `--unidiff-zero`, then plain hunks and line-selects with normal apply. Each batch is a separate `git apply` invocation.
