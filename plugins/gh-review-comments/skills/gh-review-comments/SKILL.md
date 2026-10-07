---
name: gh-review-comments
description: List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Use when managing code review feedback, replying to reviewer remarks, resolving review conversations, creating reviews with line-level comments, or bulk-processing threads by author.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs bash, gh (authenticated), jq, python3 and network access to the GitHub API.
argument-hint: "<owner/repo> <pr-number> [--author <login>] [--reply <message>] [--resolve] [--unresolve] [--create-review] [--thread-id <id>] [--unresolved-only]"
allowed-tools: AskUserQuestion Agent Bash Read
user-invocable: true
metadata:
  short-description: Manage GitHub PR review threads with gh
---


# GH Review Comments

Wraps `gh api` (REST and GraphQL) via bash scripts to operate on PR review threads. Each action maps to a script in `scripts/`.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Actions Overview
4. Scripts
5. Workflow
6. Error Handling
7. Example Invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
