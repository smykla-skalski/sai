---
name: overdeclared-tools
description: Test fixture with unused tools in allowed-tools. Use when verifying CF-tools-usage detection.
allowed-tools: Bash, Read, Task, ToolSearch
user-invocable: true
---

# Overdeclared tools

Some tools are declared but never used.

## Workflow

### Phase 1: Execute

1. Read the input file
2. Run a bash command
