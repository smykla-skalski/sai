---
name: test-writer
description: Write tests that verify behavior (not implementation), use table-driven/parameterized patterns, and minimize mocking. Triggers when asked to write tests, add test coverage, or create test files. Also triggers when reviewing existing tests for quality.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Writes test files and may run the project's test command; no network access needed.
argument-hint: "[file-or-function-to-test] [--review] [--lang go|python|ts|java|rust]"
user-invocable: true
allowed-tools: Bash Glob Grep Read Write
context: fork
agent: general-purpose
metadata:
  short-description: Write behavior-first tests
---


# Test Writer

Write tests that survive refactoring, catch real bugs, and don't waste maintenance effort.

**Philosophy:** Test what the code does, not how it does it. If you refactor internals and tests break — the tests are wrong, not the code.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Phase 1: Understand the Code
4. Phase 2: Design Test Structure
5. Phase 3: Write Tests
6. Phase 4: Quality Check
7. Phase 5: Review Mode (--review)
8. Test Review: [file]
9. Hard Rules

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
