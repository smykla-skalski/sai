---
name: agent-issues
description: Write, improve and split GitHub issues, and write task briefs for subagents, so that coding agents can implement them without asking questions. Interviews for missing facts, verifies every pointer in the repo, states runnable done-checks, non-goals and stop-and-flag triggers, cuts oversized work into self-contained vertical slices, and runs a cold-read review when size or risk warrants it. Use when asked to write an issue or ticket, file work for an agent, turn context into issues, improve or split an existing issue, or brief a subagent. Triggers on "write an issue for", "file a ticket", "make this agent-ready", "split this issue", "break this down", "brief a subagent", or a pasted issue URL to tighten. Not for implementing an issue.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs the gh CLI to file or edit GitHub issues; without it the skill produces the draft only. A subagent tool is optional (the cold-read review falls back to an inline pass).
argument-hint: "[description | issue url/number] [--draft] [--file] [--brief] [--cold-read | --no-cold-read]"
allowed-tools: Agent AskUserQuestion Bash Glob Grep Read Write
user-invocable: true
metadata:
  short-description: Write issues that coding agents can finish
---

# Agent issues

An issue written for a coding agent is the agent's whole prompt. The implementer will not reliably ask what is missing, may start with no memory of the author, and will read a hint as an instruction. This skill produces issues and briefs that are complete, checkable and honest about what is verified.

Four jobs share one rule set:

- Create an issue from a description or pasted context.
- Improve an existing issue.
- Split an oversized issue or goal into self-contained slices.
- Write a brief for a subagent (not filed anywhere).

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. When a named tool, agent or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Arguments

Invocation arguments: `$ARGUMENTS`

These are the description, issue URL or number and flags the user gave on invocation. The workflow reads them from here, not from its own text. If the line above is empty or still shows the literal placeholder, the client passed none: take the same values from the user's request.

## Core flow

1. Detect the mode and read the repository's conventions
2. Interview for missing facts, then research and verify every claim
3. Decide whether the work is one issue or several
4. Draft with the issue rules, or the repo's template
5. Run the self-check, then the cold-read gate if the threshold is met
6. Run the writing pass
7. Show the draft, get a go-ahead, file with native relationships
8. Read the result back

## Execution contract

- Resolve the mode and flags before any side effect.
- Execute the workflow sections in order. Load each reference at the step that names it, not before.
- Never put an unverified fact in an issue as if it were verified. Mark it as a hypothesis or an open item.
- Never file, edit or comment on GitHub before the user has seen the full draft and said go, unless the invocation carried `--file`.
- Stop at every hard stop the workflow names and state the next action needed.
