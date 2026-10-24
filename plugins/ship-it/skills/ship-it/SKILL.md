---
name: ship-it
description: Ship changes or approved plans through selected gates and merge. Accepts task text, GitHub issues or Jira tickets.
license: MIT
compatibility: Claude Code, Codex, opencode and Copilot CLI; git and authenticated gh.
argument-hint: "[--issue] [--risk low|medium|high] <task description | github-issue-url | jira-url>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill ToolSearch Write
user-invocable: true
metadata:
  short-description: Ship tasks and issues to merge
---

# Ship It

## Active bundle bootstrap

Read [bootstrap.md](references/bootstrap.md) before any other reference/helper. Use its pinned root or explicit unsupported-platform fallback.

**Mode:** autonomous; ask on material ambiguity. Block on events until merged or stopped; never foreground-poll.

Read [references/fallbacks.md](references/fallbacks.md) for missing agent features.

Invocation: `/ship-it [--issue] [--risk low|medium|high] <task|GitHub issue|Jira URL>` (`$ship-it` in Codex); absent arguments use the request.

## Workflow contract

- Run phases in order; never skip gates.
- Read this entry once and each phase reference before its phase; checkpoint rules. Do not reread a reference on phase transitions; resume loads missing guidance only.
- On missing/changed capability or fallback, read [references/capabilities.md](references/capabilities.md) and [references/capabilities.json](references/capabilities.json), then rerun preflight.
- Read [roles.md](references/roles.md) and [roles.json](references/roles.json) only for unresolved aliases or overrides. Give each gate its mandate by path or inline exactly once in fresh context.
- Use capacity before waiting; follow [orchestration.md](references/orchestration.md) for workers/gates.
- Before dispatch, read [worker-events](references/worker-events.md) for every worker/waiter.
- Update checkpoints through the helper. Read [references/checkpoint.md](references/checkpoint.md) for migration/recovery/validation errors. Claims/evidence default off; read [references/claims.md](references/claims.md)/[references/evidence.md](references/evidence.md) when enabled. Telemetry defaults on; read [telemetry.md](references/telemetry.md) after policy resolution unless disabled by repository policy.
- Keep routine guidance under 12k input tokens: bootstrap, selected phases, [risk-policy](references/risk-policy.json), [release-policy](references/release-policy.json), [references/convergence-policy.json](references/convergence-policy.json). After compaction, read only the checkpoint and current phase reference.
- Read [references/risk.md](references/risk.md) or [references/release.md](references/release.md) for small-code selection, overrides or phase triggers; read [references/convergence.md](references/convergence.md) only after failure, recovery or exhaustive opt-in. Checkpoint gates, release policy and budget before validation.
- Before validation or integration read [validation-reuse.md](references/validation-reuse.md). Reuse only verified results with current-head provenance.
- Never bypass hooks, suppress checks, force-push after the first push, or force-merge.
- If connected tools expose Sail, read [references/sail.md](references/sail.md) before resolution. Otherwise do not load it.
- For file-by-file helpers, read [file delivery](references/helper-loading.md).

Resolve source, criteria, authority and checkpoint before changes. For approved plans/umbrellas, read [orchestration.md](references/orchestration.md); parents never implement children.

Phase 5 — Publish draft PR precedes Phase 6 — Review; Phase 7 — Test runs once after clean review.

## Phase reference index

| Phase | Read before starting |
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

## Hard stops

Name the required human action and stop for invalid source/ownership, failed preflight/control, hosted deadline, BLOCKED test, unresolved product choice, or when a delivery blocker survives scoped acceptance recovery.
