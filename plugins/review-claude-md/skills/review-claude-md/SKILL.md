---
name: review-claude-md
description: Audit and fix CLAUDE.md files using a tiered binary checklist based on official Anthropic best practices and community guidelines. Use when the user asks to "review CLAUDE.md", "audit CLAUDE.md", "score CLAUDE.md", "improve CLAUDE.md", or "fix CLAUDE.md". Not for generic markdown cleanup or for reviewing skills and agents.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. The bundled validation scripts need bash, grep, sed and awk.
argument-hint: "[path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: Agent Bash Edit Glob Read Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Audit and fix CLAUDE.md files
---


# Review CLAUDE.md

Evaluate any CLAUDE.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix all failing checks and re-evaluate.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Verdict logic
4. Workflow
5. Good vs Bad Examples
6. Example Invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
