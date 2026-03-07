---
name: limited-examples
description: Fixture with two tagged examples. Use when validating BP-example-tags informational threshold.
allowed-tools: Read
user-invocable: true
---

# Limited examples

## Workflow

1. Read one input file.
2. Return one summary.

## Examples

<example>
Input: `/limited-examples file-a.md`
Output: Returns summary for file-a.md.
</example>

<example>
Input: `/limited-examples file-b.md`
Output: Returns summary for file-b.md.
</example>
