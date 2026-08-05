---
name: ship-issue
description: End-to-end ship a GitHub issue — implement, adversarial code review via subagent, adversarial manual testing via subagent, open PR, wait for Copilot review + green CI, address feedback, merge, close issue. Use when given a GitHub issue URL and asked to implement and ship it.
argument-hint: "<github-issue-url>"
user-invocable: true
allowed-tools:
  - Agent
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
---

# Ship Issue

Take a GitHub issue from URL to merged PR autonomously. Implement, review, manually test, open PR, wait for Copilot and CI, fix feedback, merge, and close.

**Role:** Senior engineer owning the full lifecycle of one ticket.

**Mode:** Autonomous. Ask no clarifying questions unless the issue is ambiguous and the repository cannot resolve it. Default to the most reasonable interpretation and ship.

## Invocation

```text
/ship-issue <github-issue-url>
```

## Phase 1 — Read the issue

Parse the owner, repository, and issue number from the URL, then inspect the open issue with `gh issue view` including title, body, labels, assignees, milestone, state, and comments. Stop and report if it is closed. Extract scope hints from labels and linked PRs from comments.

## Phase 2 — Explore the repository

- Read the root `CLAUDE.md` when present.
- Identify the primary stack from its manifests.
- Find the project’s lint, format, type-check, test, and build commands.
- Locate the affected code and existing tests before editing.

## Phase 3 — Branch

Fetch origin, resolve the repository default branch with `gh repo view`, fast-forward it, then create:

```text
<type>/issue-<number>-<slug>
```

Infer `<type>` from the issue (`feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `ci`, `build`, `style`, or `revert`), and make `<slug>` a kebab-case, roughly 50-character title summary.

## Phase 4 — Implement

Work in small, focused commits and follow the repository’s established patterns. Add or extend behavior-focused tests. Before every commit run the relevant formatter, linter, type checker, build, and tests. Never use a lint/type suppression or `--no-verify`; fix the root cause.

Use signed conventional commits with a required scope and a title of at most 50 characters:

```text
<type>(<scope>): <description>

Refs #<number>
```

Do not add AI attribution or PR references to commit titles.

## Phase 5 — Adversarial code review

Before pushing, use `staff-code-review:code-adversary` when available, otherwise a general-purpose subagent, to red-team the branch. Provide the issue body, `git diff <default>...HEAD`, and changed-file list. The reviewer must assume the change is broken and identify concrete failures: unsolved acceptance criteria, edge cases, races, error handling, security/regressions, weak tests, and convention violations. Each finding must include severity, location, failing scenario, and exact fix; no praise.

Apply blocker and should-fix findings, then rerun quality gates. Investigate uncertain findings; put genuinely unresolved questions in the PR body rather than silently blocking.

## Phase 6 — Adversarial manual testing

Spawn a fresh general-purpose tester from the current branch tip after Phase 5. The tester must derive acceptance criteria from the issue and run the real changed product surface: start a service and probe it, run the real CLI in isolated state, exercise a sandbox, or otherwise execute the strongest user-visible behavior. Automated tests, lint, build, and grep are supporting evidence only.

For pure refactors, internal helpers, or documentation changes with no runnable product surface, use the strongest behavioral regression evidence available; static review or grep alone is insufficient. In the Sybra repository, invoke `sybra-test` instead of improvising the test harness.

The tester must attack happy paths, boundaries, malformed input, repeated/concurrent use, and adjacent flows and finish with exactly one line:

```text
TEST_VERDICT: PASS
```

or

```text
TEST_VERDICT: FAIL
```

On FAIL, treat every reproduction as a blocker: fix it, add a regression test, rerun quality gates, and respawn the tester against the new tip. After more than three unsuccessful fixes for the same reproduction, stop and ask the user. Do not open a PR until PASS.

## Phase 7 — Push and open the PR

Push the branch, create a PR against the default branch, and use the conventional lead-commit title. The body must have `## Motivation`, `## Implementation information`, `Closes #<number>`, and a changelog line. Capture the PR number.

Request a Copilot review when configured, using `github-copilot[bot]` and the Copilot review app fallback. Failure to request either must not fail the PR creation.

## Phase 8 — Wait for Copilot and CI

Poll every 5–10 minutes; do not busy-loop. On each poll inspect `gh pr checks` and unresolved non-outdated Copilot review threads. Never merge before all checks succeed **and** Copilot has actually submitted a review, including a no-comments review.

If CI fails, inspect the failed run logs, fix and push, then restart the wait. If after roughly 30 minutes Copilot has neither reviewed nor has a pending review request, stop and ask whether to merge without it; never silently skip the Copilot wait.

## Phase 9 — Address Copilot feedback

For every unresolved Copilot thread:

- Apply valid actionable feedback, commit it, reply, and resolve the thread.
- For questionable feedback, use the codebase to disambiguate; otherwise ask only when necessary.
- For invalid feedback, reply with a concise rationale and resolve it.

Push fixes and return to Phase 8 until CI is green and no Copilot thread remains. Stop for a human decision if the same thread loops more than three times.

## Phase 10 — Merge

Merge with squash and delete the branch only when CI is successful, Copilot has posted a review, and every Copilot comment has been answered and resolved. Do not force-merge. If branch protection requires additional approvals or admin action, report the state and stop.

## Phase 11 — Close and report

Verify that `Closes #<number>` closed the issue. If it did not, close it with a completion comment. Report: issue, PR link, commits, CI status, Copilot threads resolved/total, and merged/closed status.

## Phase 12 — Return to the default branch

After merge, switch to the default branch, fast-forward it, and delete the local feature branch when safe.

## Hard stops

Stop and surface the exact next human action when the issue is already closed or actively owned, branch protection blocks merging, a Copilot thread loops more than three times, tests require disabling a check, or the issue needs a product/design decision that the repository cannot answer.
