---
name: kubecon-cfp
description: Interactive KubeCon CFP submission writer. Guides through topic selection, title crafting, abstract writing, and benefits section using acceptance data from 1,100+ talks across 7 KubeCon events (2024-2025). Use when preparing a conference talk proposal for KubeCon/CloudNativeCon, writing a CFP, or asking about KubeCon submission strategy.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. No scripts needed; the optional competitive analysis uses web search when the agent has it.
argument-hint: "[topic or talk idea] [--track AI|Security|Platform|Observability|...] [--format session|lightning|tutorial|panel] [--review]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Agent AskUserQuestion Read Write
metadata:
  short-description: Draft and refine KubeCon CFPs
---


# KubeCon CFP Submission Writer

Craft a high-quality KubeCon CFP submission using data-driven insights from 1,100+ accepted talks and official reviewer criteria.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Arguments
3. Workflow
4. Scope
5. Error Handling
6. Quality Standards
7. Example Invocations

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
