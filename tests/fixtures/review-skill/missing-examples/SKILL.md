---
name: missing-examples
description: Fixture with no <example> tags. Use when validating best-practice checks for examples and over-prompting.
allowed-tools: Read
user-invocable: true
---

# Missing examples

This fixture intentionally omits XML-style examples.

## Workflow

### Phase 1: Gather input

1. Read the target file.
2. You MUST collect every field before moving on.

### Phase 2: Validate

1. CRITICAL: enforce schema checks exactly.
2. ALWAYS reject unknown keys.

### Phase 3: Build output

1. Transform validated fields.
2. NEVER skip required output keys.

### Phase 4: Return result

1. Print a short result summary.
2. End the workflow.

## Example Invocations

```bash
/missing-examples --dry-run
```
