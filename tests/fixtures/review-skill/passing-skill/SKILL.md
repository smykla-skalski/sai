---
name: passing-skill
description: A test fixture that passes all checks. Use when verifying the validator works on clean input.
argument-hint: "[--dry-run]"
allowed-tools: Bash, Read
user-invocable: true
---

# Passing skill

Run a simple task with no issues.

## Arguments

Parse from `$ARGUMENTS`:

- `--dry-run` -- Preview changes without applying

## Workflow

### Phase 1: Setup

1. Read the target file
2. Parse arguments

### Phase 2: Execute

1. If `--dry-run` is set, preview the task and skip changes
2. Report results

## Error handling

- If the input path is missing, stop and report the path error
- If parsing fails, report the parse error and keep files unchanged

## Good examples

<example>
Input: `/passing-skill --dry-run`
Output: Prints a preview and skips file writes.
</example>

<example>
Input: `/passing-skill`
Output: Runs the task and reports completion.
</example>

<example>
Input: `/passing-skill --dry-run --dry-run`
Output: Treats duplicate flag as idempotent and continues.
</example>

## Example Invocations

```bash
/passing-skill --dry-run
```
