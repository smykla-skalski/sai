---
name: attributed-examples
description: Test skill with attributed example tags. Use when testing example tag detection.
allowed-tools: Bash, Read
user-invocable: true
argument-hint: "[--verbose] [--dry-run] [--format]"
---

# Attributed Examples

## Arguments

- `--verbose` -- Show detailed output
- `--dry-run` -- Preview without applying
- `--format` -- Output format (default: text)

## Workflow

1. Parse arguments from `$ARGUMENTS`
2. Read the input data
3. Process and output results

Use --verbose and --dry-run and --format in workflow.

<example description="Basic usage">
Input: /attributed-examples
Output: Processed result in default format
</example>

<example description="Verbose with dry-run">
Input: /attributed-examples --verbose --dry-run
Output: Detailed preview without changes
</example>

<example description="Custom format">
Input: /attributed-examples --format json
Output: {"status": "ok"}
</example>
