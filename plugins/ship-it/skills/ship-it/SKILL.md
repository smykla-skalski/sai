---
name: ship-it
description: Ship a change or coordinate an approved complex plan through risk-selected gates, PR feedback and merge. Accepts a task description, GitHub issue or Jira ticket. Use for end-to-end shipping.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and authenticated gh. Uses adversarial-review and adversarial-test when installed.
argument-hint: "[--issue] [--risk low|medium|high] <task description | github-issue-url | jira-url>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill ToolSearch Write
user-invocable: true
metadata:
  short-description: Ship a change, issue, or Jira ticket to merge
---

# Ship It

Take a change to a merged PR, or coordinate independently shippable issues from an approved complex plan.

**Mode:** autonomous. Ask only for unresolved material ambiguity. Wait for hosted gates through blocking waiters until merged or a hard stop; never poll in the foreground.

**Other agents:** Read [references/fallbacks.md](references/fallbacks.md) when not in Claude Code or an agent feature is missing.

Invocation: `/ship-it [--issue] [--risk low|medium|high] <task|GitHub issue|Jira URL>` (`$ship-it` in Codex). If arguments are absent, use the request.

## Workflow contract

- Run phases below in order; do not skip a gate because a harness lacks a preferred tool.
- Read this entry once. Read each selected phase reference once, immediately before that phase, and keep its rules in the checkpoint. Do not reread a reference on phase transitions.
- Read [references/capabilities.md](references/capabilities.md) and [references/capabilities.json](references/capabilities.json) once during resolve, select every phase profile, and rerun only the machine-readable preflight when runtime facts change.
- Read [references/roles.md](references/roles.md) and [references/roles.json](references/roles.json) once before the first dispatch. Give each gate its mandate by path or inline exactly once in a fresh context without orchestrator history.
- After each subagent dispatch, use one blocking wait of at least ten minutes unless the worker returns sooner. Do not list agents or read status between waits; close the worker after its verdict.
- Always maintain [references/checkpoint.md](references/checkpoint.md). Claims, revision evidence and telemetry default off; read [references/claims.md](references/claims.md), [references/evidence.md](references/evidence.md) or [references/telemetry.md](references/telemetry.md) only when repository or explicit user policy enables that feature.
- Keep routine guidance under 12k input tokens. After compaction, read only the checkpoint and current phase reference.
- After exploration read [references/risk.md](references/risk.md), [references/release.md](references/release.md), then [references/convergence.md](references/convergence.md) and [references/convergence-policy.json](references/convergence-policy.json). Checkpoint the selected gates, release policy and shared budget before validation.
- Every source change invalidates completion evidence from the previous revision.
- Never bypass hooks, suppress checks, force-push after the first push, or force-merge.
- In Sail mode, missing worker or gate subagents pause the run; never replace them with inline work.

## Phase reference index

| Phase | Read immediately before starting |
| :-- | :-- |
| 1 — Resolve | [references/inputs.md](references/inputs.md) |
| 2 — Explore | [references/explore.md](references/explore.md) |
| 3 — Branch | [references/branch.md](references/branch.md) |
| 4 — Implement | [references/implementation.md](references/implementation.md) |
| 5 — Publish draft | [references/publish.md](references/publish.md) |
| 6 — Review | [references/review.md](references/review.md) |
| 7 — Test | [references/test.md](references/test.md) |
| 8–10 — PR loop | [references/pr-loop.md](references/pr-loop.md) |
| 11 — Complete | [references/completion.md](references/completion.md) |

## Phase 1 — Resolve the task

Resolve the source and acceptance criteria, then create or resume the durable checkpoint before repository changes.

For an approved complex plan or umbrella, read [references/orchestration.md](references/orchestration.md); the parent never implements a child. Ordinary issues use the phases below. In Sail, missing workers or gates pause the run.

## Phase 2 — Explore

Discover repository instructions, affected code and gates.

## Phase 3 — Branch

Use an isolated branch from the current default branch or assigned Sail worktree.

## Phase 4 — Implement

Implement the smallest complete change with behavior tests and signed conventional commits.

## Phase 5 — Publish draft PR

After the first committed revision passes local checks, push it and open a draft PR so CI starts. The draft remains pending review and test gates.

## Phase 6 — Review

Run the selected review gates for the current committed revision.

## Phase 7 — Test

Run each selected broad test gate once, only for the review-clean committed revision.

## Phases 8–10 — Wait, fix, ready, merge

Resolve hosted gates and threads, revalidate changes, mark ready only when review, test and CI pass for one head, then use the documented merge convention.

## Phase 11 — Close, report, clean up

Verify delivery, close only the GitHub issue, report evidence and clean up when safe.

## Hard stops

Stop and name the exact next human action when: a capability preflight fails; the source is invalid or ownership conflicts; a required control cannot pass; a hosted requirement exceeds its deadline; a delivery blocker survives the convergence budget; a selected test is BLOCKED; or the repository cannot answer a required product decision.
