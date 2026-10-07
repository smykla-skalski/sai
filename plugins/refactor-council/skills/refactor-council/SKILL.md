---
name: refactor-council
description: >-
  Use when the user wants a refactoring review of code, an app, a module, or a
  diff. Scans the target for code smells and git hotspots, reviews it through seven
  opposed refactoring lenses (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout,
  Tornhill), synthesizes a safety-first sequenced refactoring plan, then runs a
  separate adversarial agent that red-teams the plan before returning it. Triggers
  on "refactor this", "how should I refactor", "refactoring review", "what should I
  clean up here", "is this worth refactoring".
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs python3 for the scan scripts and git for hotspot analysis.
argument-hint: "<path|@file|directory> [--no-scan] [--no-adversary] [--since 12.month] [--personas a,b,c]"
allowed-tools: Agent AskUserQuestion Bash Edit Glob Grep Read Write
user-invocable: true
metadata:
  short-description: Refactoring review through opposed persona lenses
---


# Refactoring Council

Summon seven sourced refactoring-and-architecture persona agents to review a target, then produce a **safety-first, sequenced refactoring plan** that a separate adversarial agent has stress-tested. Each persona argues from the writer's actual published positions, with their actual phrases. They disagree with each other on purpose - the disagreement is the value.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Why this exists
2. The roster (7 + adversary)
3. Agent compatibility
4. Arguments
5. Workflow
6. Sequential mode (Codex, Copilot CLI, opencode)
7. Persona output contract
8. <Persona name> review
9. Constraints on personas
10. Synthesis output shape
11. Convergence (high-confidence signals)
12. Disagreement (real tradeoffs you must decide)
13. Per-persona top-3
14. Safety net status
15. Refactoring plan (sequenced, smallest-first)
16. Do NOT refactor (and why)
17. Risks the council missed (from the adversary)
18. Adversary verdict
19. Privacy / scope
20. Examples
21. Adding a persona

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
