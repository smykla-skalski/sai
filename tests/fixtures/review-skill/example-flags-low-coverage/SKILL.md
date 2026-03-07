---
name: example-flags-low-coverage
description: Fixture with low example flag coverage. Use when validating FC-example-flags fail behavior.
argument-hint: "[--alpha] [--beta] [--gamma] [--delta]"
allowed-tools: Read
user-invocable: true
---

# Example flags low coverage

## Arguments

- `--alpha` -- First flag
- `--beta` -- Second flag
- `--gamma` -- Third flag
- `--delta` -- Fourth flag

## Workflow

1. Parse flags `--alpha`, `--beta`, `--gamma`, and `--delta`.

## Example Invocations

```bash
/example-flags-low-coverage --alpha
```
