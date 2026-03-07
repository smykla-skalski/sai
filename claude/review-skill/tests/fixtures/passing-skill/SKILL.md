---
name: passing-skill
description: A test fixture that passes all checks. Use when verifying the validator works on clean input.
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

1. Run the task
2. Report results

## Example Invocations

```bash
/passing-skill --dry-run
```
