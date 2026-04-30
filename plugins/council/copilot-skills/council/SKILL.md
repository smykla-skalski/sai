---
name: council
description: >-
  Run the council workflow from a normal Copilot session only when the user
  explicitly asks for council review, multi-persona critique, debate, design
  review, code review, architecture feedback, UX review, or tradeoff analysis.
  Do not use it for commit, stage, merge, approval, or generic pre-commit
  requests. Accept the same mode syntax as the council custom agent:
  `core|auto|core-eng|core-ux|core-mix|all|debate <problem|@file>`.
allowed-tools:
  - agent
---

Use this skill as the **normal entrypoint** for council reviews inside an existing Copilot session.

## Goal

Keep the user in their current working session, but hand the actual council orchestration to the native `council` custom agent and its bundled reviewer agents.

## Wrapper contract

- You are a transport wrapper, not the reviewer.
- After explicit council intent is confirmed, delegate to `council:council` and return only the delegated result.
- Do not paraphrase, summarize, shorten, restyle, or add your own verdict on top of the delegated result.
- Invalid wrapper outputs include lines like `Council debate is underway`, `Council consensus:`, `I will share the findings`, reviewer lists, `Convergence`/`Tradeoff` summaries that do not begin with `# Council review:`, or any other preamble/status text.

## Trigger gate

- Run this skill only when the user explicitly asks for council. Valid signals include `/council`, `use council`, `run a council review`, `multi-persona critique`, `debate`, or naming council reviewers or modes.
- Do not invoke this skill for generic coding work, commit/stage/merge/ship requests, ordinary diff review, or approval/sign-off gates unless the user explicitly asked for council.
- If this skill was loaded without explicit council intent, do not delegate to `council:council`. Continue with the user's actual task instead.

## How to use this skill

1. If the user did not explicitly ask for council, stop here and continue with the user's actual task without using council.
2. If the user invoked `/council` with arguments, forward the request to the `council:council` custom agent with those arguments unchanged apart from removing the leading `/council`.
3. If the user invoked `/council` with no extra arguments, build a compact review brief from the current task context:
   - the user's current goal
   - the files, diffs, snippets, or plans already in scope
   - any explicit constraints or tradeoffs already discussed
4. If the user explicitly asked for council without slash syntax, build the same compact review brief from the current task context.
5. Then invoke the `council:council` custom agent with that brief.

## Delegation rules

- Council is advisory, not a required gate. Do not present it as a mandatory pre-commit, pre-merge, or approval workflow.
- Do not run the full council synthesis in the main session when this skill is used.
- Do not recreate reviewer personas inline. The `council:council` custom agent and bundled reviewer custom agents are the source of truth.
- Prefer bounded current-task context over fresh broad repo discovery.
- Use one council pass per explicit user request. Do not automatically ask council for a second "final approval" round after your own edits; rerun only when the user explicitly asks for follow-up council review.
- After invoking `council:council`, do not emit any wrapper prose, status updates, "council is underway" text, reviewer-selection narration, or reformatted summaries. Return only the delegated council result.
- If the user explicitly asks for a direct council-only session, suggest `/agent council:council` or `copilot --agent council:council --prompt ...`, but keep `/council` as the default recommendation for in-the-flow review work.

## Expected result

When council is explicitly requested, return the delegated `council:council` result exactly as received.

- The first non-empty line must be `# Council review:`
- Keep the delegated headings and wording intact
- Do not convert it into a shorter summary, bullet digest, `Convergence`/`Tradeoff` outline, or wrapper narration
