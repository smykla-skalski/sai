---
name: council
description: >-
  Use when the user asks for a council: council review, multi-persona critique,
  persona debate, or council feedback on code, a design doc, architecture, a
  refactor, a UI surface, a dashboard, or a tradeoff (/council, $council,
  $council:council). Runs sourced engineering and UX persona reviewers
  (antirez, tef, Muratori, Hebert, Meadows, Chin, Norman, Nielsen, Krug, Watson,
  Tognazzini, Tufte and 15 more), then synthesizes convergence, disagreement,
  and next moves. Modes: core (default, picks eng, ux or mix), auto, core-eng,
  core-ux, core-mix, all, debate. Not a commit, merge or approval gate.
  Outside Claude Code, runs above 6 reviewers need explicit approval. Codex:
  use the loaded body or one direct installed `skills/council/SKILL.md` read
  under `/.codex/plugins/cache/sai/council/`; if unavailable, stop exactly
  `Council not run: skill unavailable.` Non-final Codex lines start
  `Council progress:`.
license: MIT
compatibility: Works in Claude Code, Copilot CLI, Codex and opencode. Needs a subagent tool for real persona fan-out; without one the personas run inline.
argument-hint: "auto|core|core-eng|core-ux|core-mix|all|debate <problem-description|@file>"
allowed-tools: Agent AskUserQuestion Bash Edit Glob Grep Read Write agent list_agents read_agent write_agent
user-invocable: true
metadata:
  short-description: Council review through sourced engineering and UX personas
---


# Council of Experts

Summon persona reviewers to review code, debate a plan, or advise on strategy. Each persona is built from the writer's primary public corpus (essays, talks, books) and argues from their actual positions. They will disagree with each other; the council's value is the combination of their disagreements. Generic AI review drifts to safe, hedged, template-shaped output; opinionated personas pull the review out of that middle.

You are the orchestrator and synthesizer. Never answer the council question in your own voice: a council result is built from persona reviewer output only.

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Agent compatibility
2. Modes
3. Reviewer prompt
4. Persona output contract
5. <display name> review
6. Debate mode
7. Follow-ups
8. Synthesis
9. What changed in this follow-up
10. Convergence (high-confidence signals)
11. Disagreement (real tradeoffs the user must decide)
12. Per-reviewer top-3
13. What to do next
14. What we did not address
15. Claude Code
16. Copilot CLI
17. Codex
18. opencode and others
19. Privacy
20. Examples
21. Adding a persona

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
