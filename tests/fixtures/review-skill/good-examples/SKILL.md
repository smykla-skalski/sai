---
name: good-examples
description: Fixture with tagged examples and clear boundaries. Use when validating positive best-practice signals.
allowed-tools: Read
user-invocable: true
---

# Good examples

Review input and produce a small structured summary.

## Scope and safety

- Use this skill for small markdown summaries.
- When not to use: large multi-file refactors.
- Limitations: this fixture does not write files.

## Workflow

### Phase 1: Read

1. Read the input markdown file.

### Phase 2: Parse

1. Parse section headers and bullet points.

### Phase 3: Report

1. Return a concise summary with section counts.

## Error handling

- If the file path is missing, return a path error.
- If parsing fails, return a parse error with line context.

## Examples

<example>
Input: `/good-examples notes.md`
Output: Returns section count and bullet count for `notes.md`.
</example>

<example>
Input: `/good-examples broken.md`
Output: Returns parse error with the failing line number.
</example>

<example>
Input: `/good-examples empty.md`
Output: Returns zero counts and an empty-content note.
</example>
