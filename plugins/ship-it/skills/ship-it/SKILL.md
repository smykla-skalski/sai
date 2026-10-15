---
name: ship-it
description: Ship a change or approved complex plan through risk-selected gates, PR feedback, and merge. Accepts task text, a GitHub issue, or Jira ticket.
license: MIT
compatibility: Claude Code, Codex, opencode and Copilot CLI; git and authenticated gh.
argument-hint: "[--issue] [--risk low|medium|high] <task description | github-issue-url | jira-url>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill ToolSearch Write
user-invocable: true
metadata:
  short-description: Ship a change, issue, or Jira ticket to merge
---

# Ship It

Merge changes or coordinate approved plans.

**Mode:** autonomous. Ask only on material ambiguity. Use blocking waiters until merged or a hard stop; never foreground-poll.

Read [references/fallbacks.md](references/fallbacks.md) for missing agent features.

Invocation: `/ship-it [--issue] [--risk low|medium|high] <task|GitHub issue|Jira URL>` (`$ship-it` in Codex). If arguments are absent, use the request.

## Workflow contract

- Run phases in order; never skip gates.
- Read this entry once and each selected phase reference once before its phase; checkpoint its rules. Do not reread a reference on phase transitions. On resume, load missing guidance only.
- Resolve capabilities from tools and phase guidance. Read [references/capabilities.md](references/capabilities.md) and [references/capabilities.json](references/capabilities.json) only on missing/changed capability or fallback; rerun preflight.
- Phase references name routine routes. Read [references/roles.md](references/roles.md) and [references/roles.json](references/roles.json) only for unresolved aliases or policy overrides. Give each gate its mandate by path or inline exactly once in fresh context.
- Use available capacity before waiting; apply [orchestration.md](references/orchestration.md) to issue workers and nested gates.
- Before dispatch, read [references/worker-events.md](references/worker-events.md) once; it governs every worker and waiter.
- Maintain the checkpoint through the helper. Read [references/checkpoint.md](references/checkpoint.md) only for migration, recovery or validation error. Claims/evidence default off; read [references/claims.md](references/claims.md) or [references/evidence.md](references/evidence.md) only when enabled. Telemetry defaults on; read [references/telemetry.md](references/telemetry.md) after policy resolution unless repository policy disables it.
- Routine guidance includes selected phase references, [references/risk-policy.json](references/risk-policy.json), [references/release-policy.json](references/release-policy.json) and [references/convergence-policy.json](references/convergence-policy.json): keep it under 12k input tokens. After compaction, read only the checkpoint and current phase reference.
- Read [references/risk.md](references/risk.md) or [references/release.md](references/release.md) only on override/ambiguity; read [references/convergence.md](references/convergence.md) only after failure, recovery or exhaustive opt-in. Checkpoint gates, release policy and budget before validation.
- Before validation or integration read [validation-reuse.md](references/validation-reuse.md). Reuse only verified results with current-head provenance.
- Never bypass hooks, suppress checks, force-push after the first push, or force-merge.
- If connected tools expose Sail, read [references/sail.md](references/sail.md) before resolution. Otherwise do not load it.
- For file-by-file helper delivery, read [references/helper-loading.md](references/helper-loading.md).

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

Resolve the source, criteria and scoped authorization, then create or resume the checkpoint before changes.

For an approved complex plan or umbrella, read [references/orchestration.md](references/orchestration.md); the parent never implements a child. Ordinary issues follow the phases below.

## Phase 2 — Explore

Discover instructions, affected code and gates.

## Phase 3 — Branch

Use an isolated branch from the current default branch or assigned host worktree.

## Phase 4 — Implement

Implement the smallest complete change with behavior tests and signed conventional commits.

## Phase 5 — Publish draft PR

After the first committed revision passes local checks, push it and open a draft PR so CI starts. The draft remains pending review and test gates.

## Phase 6 — Review

Run the selected review gates for the current committed revision.

## Phase 7 — Test

Run each selected broad test gate once, only for the review-clean committed revision.

## Phases 8–10 — Wait, fix, ready, merge

Resolve hosted gates and threads; revalidate changes. Mark ready when review, test and CI pass for one head, then merge as documented.

## Phase 11 — Close, report, clean up

Verify delivery, close the GitHub issue, report evidence and clean up safely.

## Hard stops

Stop and name the exact next human action when: a capability preflight fails; the source is invalid or ownership conflicts; a required control cannot pass; a hosted requirement exceeds its deadline; a delivery blocker survives scoped acceptance recovery; a selected test is BLOCKED; or the repository cannot answer a required product decision.
