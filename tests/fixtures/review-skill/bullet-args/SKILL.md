---
name: bullet-args
description: Test fixture using bullet-list argument format instead of tables. Use when verifying bullet-list parsing.
argument-hint: "[--dry-run] [--verbose] [--output PATH]"
allowed-tools: Bash, Read
user-invocable: true
---

# Bullet args

Run a task with bullet-list arguments.

## Arguments

Parse from `$ARGUMENTS`:

- `--dry-run` - Preview changes without applying
- `--verbose` - Show detailed output during execution
- `--output` - Path to write results (default: stdout)

## Workflow

### Phase 1: Setup

1. Parse `--dry-run`, `--verbose`, and `--output` from arguments
2. Read the target file

### Phase 2: Execute

1. If `--dry-run` is set, preview the task and skip changes
2. If `--verbose` is set, include extra detail in output
3. Write results to `--output` path or stdout

## Error handling

- If the input path is missing, stop and report the path error

<example>
Input: `/bullet-args --dry-run --verbose`
Output: Previews task with detailed output and skips writes.
</example>

<example>
Input: `/bullet-args --output /tmp/out.txt`
Output: Writes results to the specified path.
</example>

<example>
Input: `/bullet-args --dry-run --output /tmp/out.txt --verbose`
Output: Previews with detail, writes preview to the specified path.
</example>

## Example Invocations

```bash
/bullet-args --dry-run
/bullet-args --verbose --output /tmp/results.txt
/bullet-args --dry-run --verbose
```
