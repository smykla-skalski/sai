---
name: council
description: >-
  Run the council workflow from a normal Copilot session. Use when the user asks
  for council review, multi-persona critique, debate, design review, code
  review, architecture feedback, UX review, or tradeoff analysis. Accept the
  same mode syntax as the council custom agent:
  `core|auto|core-eng|core-ux|core-mix|all|debate <problem|@file>`.
allowed-tools:
  - agent
---

Use this skill as the **normal entrypoint** for council reviews inside an existing Copilot session.

## Goal

Keep the user in their current working session, but hand the actual council orchestration to the native `council` custom agent and its bundled reviewer agents.

## How to use this skill

1. If the user invoked `/council` with arguments, forward the request to the `council:council` custom agent with those arguments unchanged apart from removing the leading `/council`.
2. If the user invoked `/council` with no extra arguments, build a compact review brief from the current task context:
   - the user's current goal
   - the files, diffs, snippets, or plans already in scope
   - any explicit constraints or tradeoffs already discussed
3. Then invoke the `council:council` custom agent with that brief.

## Delegation rules

- Do not run the full council synthesis in the main session when this skill is used.
- Do not recreate reviewer personas inline. The `council:council` custom agent and bundled reviewer custom agents are the source of truth.
- Prefer bounded current-task context over fresh broad repo discovery.
- If the user explicitly asks for a direct council-only session, suggest `/agent council:council` or `copilot --agent council:council --prompt ...`, but keep `/council` as the default recommendation for in-the-flow review work.

## Expected result

Return the integrated council review from the delegated `council` custom agent:

- convergence across lenses
- real disagreements and tradeoffs
- per-reviewer top signals
- concrete next moves
- explicit gaps in council coverage
