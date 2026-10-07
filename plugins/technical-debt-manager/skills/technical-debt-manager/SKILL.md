---
name: technical-debt-manager
description: Analyze repo for technical debt, research language-specific best practices, create umbrella tracker issue with one subissue per finding. On re-runs, reuses an existing umbrella and dedupes findings against its subissues.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and an authenticated GitHub CLI (gh 2.94 or newer for native sub-issue flags; older gh falls back to GraphQL). Uses network access for web research and for creating GitHub issues.
argument-hint: "[--focus area] [--label label-name]"
allowed-tools: Bash Glob Grep Read WebFetch WebSearch Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Audit tech debt into a GitHub issue tracker
---


# Technical Debt Manager

Analyze current repo for technical debt by exploring codebase and researching version-specific best practices. Produce an umbrella ☂️ tracker issue plus one subissue per finding, all rated across 4 axes (impact, effort, contagion, business alignment) with concrete, actionable fix descriptions. Subissues are linked to the umbrella with the GitHub CLI's native sub-issue support (`gh issue create --parent`), so no extra helper scripts are needed.

**Re-run aware:** if an umbrella tracker issue already exists, the skill reuses it — new findings are deduplicated against existing subissues, and only genuinely new debt is filed as fresh subissues linked to the existing umbrella. It never opens a second umbrella.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Requirements
3. Arguments
4. Scope
5. Workflow
6. Error Handling
7. Actionability Standard
8. Quality Checklist

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
