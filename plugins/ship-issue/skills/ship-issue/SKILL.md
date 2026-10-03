---
name: ship-issue
description: End-to-end ship a GitHub issue — implement, two-pass adversarial code review via the adversarial-review skill, adversarial manual testing via the adversarial-test skill, open PR, wait for Copilot review + green CI, address feedback, merge, close issue. Use when given a GitHub issue URL or a plain task description (an issue is created automatically) and asked to implement and ship it.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and an authenticated gh CLI with push and merge rights on the target repository. Uses the adversarial-review and adversarial-test skills when installed.
argument-hint: "<github-issue-url | task description>"
allowed-tools: Agent Bash Edit Glob Grep Read Skill Write
user-invocable: true
metadata:
  short-description: Ship a GitHub issue through merge
---

# Ship Issue

Take a GitHub issue, or a plain task description that becomes one, to a merged PR autonomously. Implement, review, manually test, open PR, wait for Copilot and CI, fix feedback, merge, and close.

**Role:** Senior engineer owning the full lifecycle of one ticket.

**Mode:** Autonomous. Ask no clarifying questions unless the issue is ambiguous and the repository cannot resolve it. Default to the most reasonable interpretation and ship.

## Agent compatibility

The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | Claude Code appends the arguments to this skill. If none are appended, take the issue URL or task description from the user's request |
| Skill tool (Phases 5 and 6) | Codex: invoke `$adversarial-review` and `$adversarial-test` (plugins `adversarial-review@sai`, `adversarial-test@sai`) with the same arguments. Copilot CLI: `/adversarial-review`, `/adversarial-test`. opencode: load the skill of the same name. Not installed: run the passes each phase describes yourself |
| Named agents `adversarial-review:code-adversary`, `adversarial-review:findings-adversary`, `adversarial-test:test-adversary` | Registered only where their plugin is installed in Claude Code or Copilot CLI. Codex and opencode do not register them; there, or whenever the type is unknown, spawn a generic subagent with the fallback mandate the phase gives |
| Subagent tool (Agent) | Codex: `spawn_agent`, waited on and closed before the next pass. opencode: the `task` tool. Copilot CLI: its agent tool. Always one subagent at a time, never in parallel: the Findings Adversary starts only after the Code Adversary returns. No subagent tool: run each pass inline yourself, in order, and reread the source for the refutation pass instead of trusting the first pass |
| AskUserQuestion | Not used; a hard-stop question goes to the user as plain text, then end the turn |
| `context: fork` | Not used |
| Explicit invocation | This skill pushes, merges and closes issues, so it runs only when the user invokes it by name. Codex enforces this through `agents/openai.yaml` (`allow_implicit_invocation: false`). On other agents, start only when the user asked to ship an issue or invoked `/ship-issue` or `$ship-issue` |

On agents with a command sandbox (Codex), the user's request to ship the issue authorizes normal branch, commit, push, PR, review-reply, merge and issue-close actions in the target repository. If a networked `git` or `gh` command fails because of the sandbox, rerun it with escalation and a one-line justification. After each state-changing step, inspect the git or GitHub state before continuing.

## Invocation

```text
/ship-issue <github-issue-url>
/ship-issue <task description>
```

In Codex use `$ship-issue` with the same arguments.

## Phase 1 — Resolve the issue

Classify the input:

- **Issue URL** (or `owner/repo#N`, `#N` in the current repository): use it.
- **Anything else is a task description.** If it contains an issue reference, use that issue and treat the rest as extra context. Otherwise create the issue yourself as described below. A missing linked issue is never a reason to stop or ask.
- **Empty input:** stop and ask for an issue URL or a description.

### Creating the issue from a description

1. Resolve the target repository from the current directory with `gh repo view --json nameWithOwner`.
2. Search for an existing open issue that already covers the task: `gh issue list --state open --search "<key terms>" --json number,title,url --limit 10`. Reuse it only when it is clearly the same work; otherwise create a new one.
3. Write a title (plain English, ≤70 characters, no conventional-commit prefix) and a body with `## Motivation`, `## Scope`, and `## Acceptance criteria` (testable, one per bullet). Infer scope from the description and the repository; do not invent requirements the description does not imply. Use the `issue-authoring` skill for the writing when it is available.
4. `gh issue create --title "<title>" --body "<body>" --label <label>` with a label only when one that fits already exists (`gh label list`). Capture the number and URL.
5. Continue with the created issue as if it had been supplied. Do not ask for confirmation.

### Reading the issue

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

Before pushing, write the issue title and body to a context file outside the repository, then run the `adversarial-review` skill against the branch:

```text
Skill: adversarial-review:adversarial-review
Args:  --base origin/<default> --context <issue-context-file>
```

It runs two clean-context subagents: a Code Adversary that hunts concrete failures, including unmet acceptance criteria, and a fresh Findings Adversary that refutes false positives. Its reply starts with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`.

If the skill is not installed, run the same two passes yourself:

1. Spawn `adversarial-review:code-adversary` (fallback: `general-purpose` told to assume the change is broken and prove each finding with a failing input, `file:line`, and fix) with the diff command, changed files, and issue context.
2. Spawn a **new** `adversarial-review:findings-adversary` (fallback: `general-purpose` told to refute each finding against the source) with the same inputs plus only the numbered findings, never the first agent's reasoning.

On NEEDS_FIXES, fix every surviving `blocking:` and `issue:`, rerun quality gates, and rerun the review against the new tip. Stop and ask the user after three rounds that still return NEEDS_FIXES. Put surviving `question:` findings you cannot settle from the code in the PR body rather than silently blocking. Do not start Phase 6 until the verdict is CLEAN.

## Phase 6 — Adversarial manual testing

From the branch tip after Phase 5, run the `adversarial-test` skill with the same issue context file:

```text
Skill: adversarial-test:adversarial-test
Args:  --base origin/<default> --context <issue-context-file>
```

It spawns a clean-context Test Adversary that derives acceptance criteria from the issue, runs the real changed product surface in isolated state (service + probe, real CLI, sandbox), attacks happy paths, boundaries, malformed input, repeated/concurrent use, and adjacent flows, then reruns every reproduction to drop false failures. Automated tests, lint, build, and grep count only as supporting evidence. Its reply starts with `Test Verdict: PASS`, `Test Verdict: FAIL`, or `Test Verdict: BLOCKED`.

In the Sybra repository, invoke `sybra-test` instead.

If the skill is not installed, spawn `adversarial-test:test-adversary` (fallback: `general-purpose` told to prove the change does not satisfy the issue by running the real surface in isolated temp state, and to report self-contained reproductions) with the repository, diff command, changed files, and issue context only; then rerun each reproduction yourself before acting on it.

On FAIL, treat every surviving reproduction as a blocker: fix it, add a regression test, rerun quality gates, and rerun the skill against the new tip. After more than three unsuccessful fixes for the same reproduction, stop and ask the user. On BLOCKED, stop and surface the named human action. Do not open a PR until PASS.

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

Verify that `Closes #<number>` closed the issue. If it did not, close it with a completion comment. Report: issue (mark it `created` when Phase 1 created it), PR link, commits, CI status, Copilot threads resolved/total, and merged/closed status.

## Phase 12 — Return to the default branch

After merge, switch to the default branch, fast-forward it, and delete the local feature branch when safe.

## Hard stops

Stop and surface the exact next human action when the issue is already closed or actively owned, branch protection blocks merging, a Copilot thread loops more than three times, tests require disabling a check, `adversarial-test` returns BLOCKED, or the issue needs a product/design decision that the repository cannot answer.
