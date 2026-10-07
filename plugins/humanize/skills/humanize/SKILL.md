---
name: humanize
description: Identify and remove AI writing patterns to make text sound natural and human-written. Use when humanizing commit messages, PR descriptions, review comments, docs, changelogs, or release notes. Also for de-slopping text that sounds robotic, has AI vibes, or reads like ChatGPT output.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. No scripts or network access needed.
argument-hint: "[file-path] [--score-only] [--dry-run]"
allowed-tools: AskUserQuestion Agent Edit Read Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Rewrite text to sound natural
---


# Humanize

Remove AI writing patterns from text and replace them with natural, human-sounding alternatives. Uses two complementary sources:

- **Detection**: Wikipedia's "Signs of AI writing" guide (WikiProject AI Cleanup) - what to remove
- **Composition**: William Strunk Jr.'s "The Elements of Style" (1918) - how to write the replacement well

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Scope
2. Agent compatibility
3. Arguments
4. Pattern categories
5. Workflow
6. Example

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
