---
name: justified-side-effect
description: Fixture with write side effects and a justify override. Use when validating justify mechanism.
allowed-tools: Bash, Read, Write, Glob
user-invocable: true
---

<!-- justify: CF-side-effect Edit/Write are used on user files, not infrastructure - safe to auto-invoke -->

# Justified side effect

Write a generated report file to disk.

## Workflow

### Phase 1: Read

1. Read the input notes file.

### Phase 2: Write output

1. Write output file `report.md` with the generated summary.
2. Save file and report the output path.
