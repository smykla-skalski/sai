---
name: ship-it
description: End-to-end ship a change or coordinate an approved complex plan — implement, run risk-selected validation gates, open PR, address feedback, and merge. Accepts a plain task description, a GitHub issue URL, or a Jira ticket URL. Use when asked to implement and ship a change end to end.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and an authenticated gh CLI with push and merge rights on the target repository. Uses the adversarial-review and adversarial-test skills when installed. Jira tickets are read through Atlassian MCP tools, acli, or the jira CLI when one is available.
argument-hint: "[--issue] [--risk low|medium|high] <task description | github-issue-url | jira-url>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill ToolSearch Write
user-invocable: true
metadata:
  short-description: Ship a change, issue, or Jira ticket to merge
---

# Ship It

Take a change to a merged PR, or coordinate independently shippable issues from an approved complex plan.

**Mode:** autonomous. Ask only when ambiguity cannot be resolved from the repository. Keep polling selected hosted gates until merged or a hard stop.

**Other agents:** Read [references/fallbacks.md](references/fallbacks.md) when not in Claude Code or an agent feature is missing.

Invocation: `/ship-it [--issue] [--risk low|medium|high] <task description | github-issue-url | jira-url>` (`$ship-it` in Codex). Runs only when invoked by name or asked to ship a change. Claude Code appends the arguments; if none are appended, take them from the user's request.

## Workflow contract

- Run the phases below in order; do not skip a gate because a harness lacks a preferred tool.
- Before each phase, read [references/capabilities.md](references/capabilities.md) and [references/capabilities.json](references/capabilities.json), select its profile and satisfy the machine-readable preflight before any side effect.
- Load each phase reference immediately before that phase, not during initial skill discovery.
- Read [references/checkpoint.md](references/checkpoint.md) after resolving the task source. Create or resume its durable checkpoint before repository changes, then keep it current through completion.
- After checkpoint reconciliation, read [references/telemetry.md](references/telemetry.md) and record the run through completion.
- Read [references/evidence.md](references/evidence.md) when the first task revision is committed. Evidence due at each PR or merge gate must pass for the exact current revision.
- Read [references/risk.md](references/risk.md) after exploration. Select and report the revision's risk, policy source and required gates before validation.
- Repository instructions override generic branch, review, release and merge defaults.
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
| 5 — Review | [references/review.md](references/review.md) |
| 6 — Test | [references/test.md](references/test.md) |
| 7–10 — PR loop | [references/pr-loop.md](references/pr-loop.md) |
| 11 — Complete | [references/completion.md](references/completion.md) |

## Phase 1 — Resolve the task

Classify the input, resolve its source and acceptance criteria, and create or resume its durable checkpoint outside the repository. No branch, edit or commit until resolution and checkpoint reconciliation succeed.

If the input is an approved complex plan or an umbrella issue with subissues, read [references/orchestration.md](references/orchestration.md) and follow its parent coordinator workflow. The parent never implements a child issue. An ordinary implementation issue, including a worker's assigned issue, follows the single-change phases below. In Sail mode, absent worker or review/test gate subagents pause the run; never use inline gate fallbacks.

## Phase 2 — Explore

Discover repository instructions, affected code and required quality gates before editing.

## Phase 3 — Branch

Start from the current default branch in an isolated conventional branch or assigned Sail worktree.

## Phase 4 — Implement

Implement the smallest complete change, add behavior tests, run relevant gates and create signed conventional commits.

## Phase 5 — Review

Run the selected review gates for the current committed revision.

## Phase 6 — Test

Run the selected test gates for the review-clean committed revision.

## Phases 7–10 — PR, wait, fix, merge

Push and open the PR, wait for selected hosted gates, resolve every required thread, revalidate changed revisions, then merge through the repository's documented convention.

## Phase 11 — Close, report, clean up

Verify delivery, close only the GitHub issue, report evidence and clean up when safe.

## Hard stops

Stop and name the exact next human action when: a phase capability preflight fails; input is empty, unrecognized or unreachable; the GitHub issue is closed or actively owned; the Jira ticket is finished; branch protection needs approvals or admin action; a selected hosted reviewer neither reviewed nor has a pending request after ~30 min; a required review thread loops more than 3 times; a test requires disabling a check; a selected test gate returns BLOCKED; the review/test round cap is hit and the user can be asked; or the task needs a product/design decision the repository cannot answer.
