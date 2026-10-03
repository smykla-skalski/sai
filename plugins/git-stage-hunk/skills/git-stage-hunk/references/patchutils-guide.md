# patchutils reference

## Contents

- [lsdiff](#lsdiff)
- [filterdiff](#filterdiff)
- [grepdiff](#grepdiff)
- [Git diff prefix handling](#git-diff-prefix-handling)
- [Hunk numbering](#hunk-numbering)

## lsdiff

List files modified in a unified diff:

```
git diff | lsdiff                    # list modified files
git diff | lsdiff --strip=1         # strip a/ b/ prefixes
git diff | lsdiff -H                # list hunk headers with file names
```

`-H` outputs one line per hunk with file and hunk header, useful for building a global hunk index.

## filterdiff

Extract hunks from a unified diff by file or hunk number:

```
git diff | filterdiff -i 'a/src/auth.ts'              # all hunks for one file
git diff | filterdiff -i 'a/src/auth.ts' --hunks=1,3  # hunks 1 and 3 only
git diff | filterdiff -x 'a/tests/*'                   # exclude test files
git diff | filterdiff --lines=45-60 -i 'a/src/auth.ts' # hunks overlapping lines 45-60
```

File patterns use `a/` prefix (git diff default). Hunk numbers are per-file, starting at 1. The `--hunks` flag accepts comma-separated numbers or ranges like `1-3`.

## grepdiff

Find hunks whose added/removed lines match a regex:

```
git diff | grepdiff 'handleAuth' --output-matching=hunk  # hunks containing pattern
git diff | grepdiff 'TODO' --output-matching=file         # entire file diffs containing pattern
```

`--output-matching=hunk` outputs only matching hunks (with their file headers). Without it, grepdiff just lists file names.

## Git diff prefix handling

Git diff uses `a/` and `b/` prefixes by default. patchutils expects these prefixes in file patterns:

- `filterdiff -i 'a/path/to/file'` matches the "old" side
- `lsdiff --strip=1` removes the prefixes for clean file names
- `git diff --no-prefix` removes prefixes but breaks patchutils compatibility

Always use `git diff` with default prefixes when piping to patchutils.

## Hunk numbering

patchutils numbers hunks per-file, not globally. Hunk 1 in `src/auth.ts` and hunk 1 in `src/db.ts` are different hunks. The stage-hunk script maps these to global sequential IDs (H1, H2, ...) by processing files in alphabetical order.
