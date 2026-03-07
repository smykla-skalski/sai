---
name: side-effect-no-dmi
description: Fixture with write side effects but no DMI guard. Use when validating side-effect detection and unused-tool checks.
allowed-tools: Bash, Read, Write, Glob
user-invocable: true
---

# Side effect no dmi

Write a generated report file to disk.

## Workflow

### Phase 1: Read

1. Read the input notes file.

### Phase 2: Write output

1. Write output file `report.md` with the generated summary.
2. Save file and report the output path.
