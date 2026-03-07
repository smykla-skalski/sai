---
name: example-flags-good-coverage
description: Fixture with sufficient example flag coverage. Use when validating FC-example-flags pass behavior.
argument-hint: "[--alpha] [--beta] [--gamma] [--delta]"
allowed-tools: Read
user-invocable: true
---

# Example flags good coverage

## Arguments

- `--alpha` -- First flag
- `--beta` -- Second flag
- `--gamma` -- Third flag
- `--delta` -- Fourth flag

## Workflow

1. Parse flags `--alpha`, `--beta`, `--gamma`, and `--delta`.

## Example Invocations

```bash
/example-flags-good-coverage --alpha --beta
```
