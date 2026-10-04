---
name: ship-it
description: End-to-end ship a change — implement, two-pass adversarial code review via the adversarial-review skill, adversarial manual testing via the adversarial-test skill, open PR, wait for Copilot review + green CI, address feedback, merge. Accepts a plain task description (no issue is created unless --issue is passed), a GitHub issue URL (closed on merge), or a Jira ticket URL (read-only; the key goes in the PR). Use when asked to implement and ship a change end to end.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and an authenticated gh CLI with push and merge rights on the target repository. Uses the adversarial-review and adversarial-test skills when installed. Jira tickets are read through Atlassian MCP tools, acli, or the jira CLI when one is available.
argument-hint: "[--issue] <task description | github-issue-url | jira-url>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill ToolSearch Write
user-invocable: true
metadata:
  short-description: Ship a change, issue, or Jira ticket to merge
---

# Ship It

Take one change (task description, GitHub issue, or Jira ticket) to a merged PR, closing the GitHub issue if any.

**Role:** senior engineer owning the full lifecycle of one change.

**Mode:** autonomous. Ask only when the task is ambiguous and the repository cannot resolve it. Never end the turn while CI or Copilot is pending: keep polling (background waits are fine) until merged or a hard stop.

**Other agents:** Codex, opencode and Copilot CLI invoke skills and subagents differently, run one subagent at a time, and may need sandbox escalation. Read [references/fallbacks.md](references/fallbacks.md) at the start when not in Claude Code, or whenever a skill, named agent, or subagent tool is missing.

Invocation: `/ship-it [--issue] <task description | github-issue-url | jira-url>` (`$ship-it` in Codex). Runs only when invoked by name or asked to ship a change. Claude Code appends the arguments; if none are appended, take them from the user's request.

## Phase 1 — Resolve the task

Read [references/inputs.md](references/inputs.md) before Phase 1. Classify the input, create the issue for `--issue`, read the GitHub issue or Jira ticket, and write the task context file outside the repository. No branch, edit or commit until this phase succeeds.

## Phase 2 — Explore

Read root `CLAUDE.md`, `AGENTS.md` and `CONTRIBUTING.md` when present, including the merge convention. Identify the stack, the lint, format, type-check, test and build commands, the affected code and its tests.

## Phase 3 — Branch

Fetch origin, resolve the default branch with `gh repo view`, fast-forward it, branch: `<type>/issue-<n>-<slug>` (GitHub issue), `<type>/<jira-key-lowercase>-<slug>` (Jira), `<type>/<slug>` (description). `<type>` is a conventional type; `<slug>` is kebab-case, ~50 chars. Work in another repository happens in a new worktree of it, never in its main checkout.

## Phase 4 — Implement

Small focused commits following repository patterns; add behavior-focused tests. Before every commit run formatter, linter, type checker, build and tests. Never use suppressions or `--no-verify`; fix the root cause.

Signed conventional commits, scope required, title ≤50 chars, no AI attribution or PR refs. Footer: `Refs #<n>` (`Refs owner/repo#<n>` cross-repo) for a GitHub issue, `Refs <KEY-123>` for Jira, none for a description.

## Phase 5 — Adversarial review

Run `adversarial-review:adversarial-review` with `--base origin/<default> --context <task-context-file>`. Reply starts `Review Verdict: CLEAN` or `NEEDS_FIXES`. On NEEDS_FIXES fix every surviving `blocking:` and `issue:`, rerun gates and the review on the new tip. Unsettled `question:` findings go in the PR body. Phase 6 only after CLEAN.

## Phase 6 — Adversarial test

From the Phase 5 tip run `adversarial-test:adversarial-test` with the same args. Reply starts `Test Verdict: PASS`, `FAIL` or `BLOCKED`. On FAIL each surviving reproduction is a blocker: fix, add a regression test, rerun gates and the skill. BLOCKED is a hard stop. PR only after PASS.

**Round cap (Phases 5–6):** after 3 failing rounds (or more than 3 failed fixes of one reproduction), stop and ask. If the user cannot be asked, continue only while each round finds smaller concrete issues, and say so in the report.

## Phases 7–10 — PR, wait, fix, merge

Read [references/pr-loop.md](references/pr-loop.md) before Phase 7. In short:

7. Squash repeated version-bump commits, push, open the PR, request Copilot.
8. Poll CI and Copilot every 5–10 min; fix CI failures.
9. Fix or answer every Copilot thread, then resolve it.
10. Merge when CI is green, Copilot reviewed once, all threads resolved, via the repo's documented convention (e.g. a `squash` comment). Never force-push or rebase after the first push; use a signed `git merge origin/<default>`.

## Phase 11 — Close, report, clean up

GitHub issue: confirm `Closes` closed it, else close it with a completion comment. Jira: leave it untouched; say it is ready to transition. Report source (`created` if Phase 1 made the issue; Jira key; or description), PR link, commits, CI status, Copilot threads resolved/total, merged/closed status, and any round-cap overrun. Then switch to the default branch, fast-forward, and delete the local branch (or worktree) when safe.

## Hard stops

Stop and name the exact next human action when: input is empty, unrecognized or unreachable; the GitHub issue is closed or actively owned; the Jira ticket is finished; branch protection needs approvals or admin action; Copilot neither reviewed nor has a pending request after ~30 min (ask whether to merge without it); a Copilot thread loops more than 3 times; a test requires disabling a check; `adversarial-test` returns BLOCKED; the review/test round cap is hit and the user can be asked; or the task needs a product/design decision the repository cannot answer.
