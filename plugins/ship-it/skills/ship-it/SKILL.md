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

Take one change to a merged PR autonomously. The change comes from a plain task description, a GitHub issue, or a Jira ticket. Implement, review, manually test, open PR, wait for Copilot and CI, fix feedback, merge, and close the GitHub issue when there is one.

**Role:** Senior engineer owning the full lifecycle of one change.

**Mode:** Autonomous. Ask no clarifying questions unless the task is ambiguous and the repository cannot resolve it. Default to the most reasonable interpretation and ship.

## Agent compatibility

The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | Claude Code appends the arguments to this skill. If none are appended, take the description, URL and flags from the user's request |
| ToolSearch (Jira via Atlassian MCP, Phase 1) | Codex, Copilot CLI, opencode: use Atlassian MCP tools only when the session already lists them. No MCP tools: use the `acli` or `jira` CLI fallbacks Phase 1 gives |
| Skill tool (Phases 5 and 6) | Codex: invoke `$adversarial-review` and `$adversarial-test` (plugins `adversarial-review@sai`, `adversarial-test@sai`) with the same arguments. Copilot CLI: `/adversarial-review`, `/adversarial-test`. opencode: load the skill of the same name. Not installed: run the passes each phase describes yourself |
| Named agents `adversarial-review:code-adversary`, `adversarial-review:findings-adversary`, `adversarial-test:test-adversary` | Registered only where their plugin is installed in Claude Code or Copilot CLI. Codex and opencode do not register them; there, or whenever the type is unknown, spawn a generic subagent with the fallback mandate the phase gives |
| Subagent tool (Agent) | Codex: `spawn_agent`, waited on and closed before the next pass. opencode: the `task` tool. Copilot CLI: its agent tool. Always one subagent at a time, never in parallel: the Findings Adversary starts only after the Code Adversary returns. No subagent tool: run each pass inline yourself, in order, and reread the source for the refutation pass instead of trusting the first pass |
| AskUserQuestion | Not used; a hard-stop question or a request to paste a Jira ticket goes to the user as plain text, then end the turn |
| `context: fork` | Not used |
| Explicit invocation | This skill pushes, merges and closes issues, so it runs only when the user invokes it by name. Codex enforces this through `agents/openai.yaml` (`allow_implicit_invocation: false`). On other agents, start only when the user asked to ship a change or invoked `/ship-it` or `$ship-it` |

On agents with a command sandbox (Codex), the user's request to ship the change authorizes normal branch, commit, push, PR, review-reply, merge and issue-close actions in the target repository. If a networked `git`, `gh`, `acli` or `jira` command fails because of the sandbox, rerun it with escalation and a one-line justification. After each state-changing step, inspect the git or GitHub state before continuing.

## Invocation

```text
/ship-it <task description>
/ship-it --issue <task description>
/ship-it <github-issue-url>
/ship-it <jira-url>
```

In Codex use `$ship-it` with the same arguments.

## Phase 1 — Resolve the task

If the first token is `--issue`, strip it and remember the flag; an `--issue` anywhere else is part of the description ("add support for --issue"). Then classify the rest. Make no repository changes (no branch, edit or commit) until this phase succeeds.

| Input | Source | Example |
| :-- | :-- | :-- |
| Empty | Stop and ask for a task description, a GitHub issue URL, or a Jira URL | |
| GitHub issue URL (github.com or a GitHub Enterprise host `gh` is authenticated for), `owner/repo#N`, or `#N` in the current repository | GitHub issue | `https://github.com/owner/repo/issues/123` |
| Jira issue URL | Jira ticket | `https://<site>.atlassian.net/browse/KEY-123`, or any `atlassian.net` or Jira URL whose path ends in a `KEY-123` segment (`.../projects/KEY/issues/KEY-123`, service-desk queue links) or that has `selectedIssue=KEY-123` |
| A lone URL or reference that matches neither (GitHub PR, commit, discussion, a host that is neither GitHub nor Jira) | Unrecognized: stop | `https://github.com/owner/repo/pull/7` |
| Anything else | Task description | `add a --json flag to the export command` |

A task description that embeds a GitHub issue URL, an `owner/repo#N` reference, or a Jira issue URL uses that source and treats the rest as extra context. A bare `#N` inside free text ("make #333 the default color") is a GitHub issue only when the text calls it one ("fixes #42", "issue #42") and either the text is little more than that reference ("fix #42") or the issue's title matches the task; otherwise it stays part of the description, so merging never closes an unrelated issue. `--issue` applies only to task descriptions; with a URL, say it is ignored and continue.

Every stop in this phase names what was received and what the skill accepts, then ends the turn.

### Task description

Without `--issue`, ship the description as is: no issue is created and none is searched for. Derive a short title and testable acceptance criteria from the description and the repository; do not invent requirements the description does not imply.

With `--issue`:

1. Resolve the target repository from the current directory with `gh repo view --json nameWithOwner`.
2. Search for an existing open issue that already covers the task: `gh issue list --state open --search "<key terms>" --json number,title,url --limit 10`. Reuse it only when it is clearly the same work; otherwise create a new one.
3. Write a title (plain English, ≤70 characters, no conventional-commit prefix) and a body with `## Motivation`, `## Scope`, and `## Acceptance criteria` (testable, one per bullet). Use the `issue-authoring` skill for the writing when it is available.
4. `gh issue create --title "<title>" --body "<body>" --label <label>` with a label only when one that fits already exists (`gh label list`). Capture the number and URL.
5. Continue with the created issue as a GitHub issue source. Do not ask for confirmation.

### GitHub issue

Parse the owner, repository, and issue number, then inspect the issue with `gh issue view` including title, body, labels, assignees, milestone, state, and comments. If `gh` cannot find or read it, stop and report the error. Stop and report if it is closed. Extract scope hints from labels and linked PRs from comments.

### Jira ticket

Extract the key (`[A-Z][A-Z0-9_]+-[0-9]+`) and the site (the URL's host). Use only sources that target that site: the same key can exist on another site, so a source logged into a different site would read the wrong ticket. Read the ticket with the first site-matching source that works, moving to the next on a missing tool, an auth error, or a not-found answer (Jira returns the same not-found for a ticket the account cannot see):

1. Atlassian MCP tools. In Claude Code load them with ToolSearch (query `atlassian jira`). Skip them when the site is not among the sites they can reach (for example `getAccessibleAtlassianResources`); otherwise use the issue-read tool (for example `getJiraIssue`) with the key and that site.
2. `acli jira workitem view <KEY>` when `command -v acli` succeeds and `acli jira auth status` shows the URL's site.
3. `jira issue view <KEY> --plain` when `command -v jira` succeeds and the `server` in its config (`~/.config/.jira/.config.yml`, or `JIRA_CONFIG_FILE`) is the URL's site.
4. No site-matching source worked: ask the user to paste the ticket summary and description, then end the turn. Continue when they reply.

After a read, confirm the ticket's own link points at the URL's site; a mismatch counts as that source missing.

Capture the key, summary, description, status, and acceptance criteria. If every site-matching source answers not-found, stop and report that the ticket does not exist or none of the configured accounts can see it, and name the sources tried; do not fall through to the paste request. If the ticket is finished, stop and report it: its status category is Done (`statusCategory.key` is `done`), or, when the source shows only a status name, the name is Done, Closed, Resolved, or Won't Do.

Treat the ticket as read-only: never transition, assign, comment on, or edit it unless the user asks.

### Task context file

Write the task title, body or description, acceptance criteria, and source (with the issue URL or Jira key) to a context file outside the repository. Phases 5 and 6 pass it to the review and test gates.

## Phase 2 — Explore the repository

- Read the root `CLAUDE.md` when present.
- Identify the primary stack from its manifests.
- Find the project’s lint, format, type-check, test, and build commands.
- Locate the affected code and existing tests before editing.

## Phase 3 — Branch

Fetch origin, resolve the repository default branch with `gh repo view`, fast-forward it, then create a branch named after the source:

| Source | Branch |
| :-- | :-- |
| GitHub issue | `<type>/issue-<number>-<slug>` |
| Jira ticket | `<type>/<jira-key-lowercase>-<slug>` |
| Task description | `<type>/<slug>` |

Infer `<type>` from the task (`feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `ci`, `build`, `style`, or `revert`), and make `<slug>` a kebab-case, roughly 50-character title summary.

## Phase 4 — Implement

Work in small, focused commits and follow the repository’s established patterns. Add or extend behavior-focused tests. Before every commit run the relevant formatter, linter, type checker, build, and tests. Never use a lint/type suppression or `--no-verify`; fix the root cause.

Use signed conventional commits with a required scope and a title of at most 50 characters:

```text
<type>(<scope>): <description>

Refs #<number>
```

The footer is `Refs #<number>` for a GitHub issue (`Refs owner/repo#<number>` when the issue lives in another repository), `Refs <KEY-123>` for a Jira ticket, and omitted for a task description. Do not add AI attribution or PR references to commit titles.

## Phase 5 — Adversarial code review

Before pushing, run the `adversarial-review` skill against the branch with the task context file from Phase 1:

```text
Skill: adversarial-review:adversarial-review
Args:  --base origin/<default> --context <task-context-file>
```

It runs two clean-context subagents: a Code Adversary that hunts concrete failures, including unmet acceptance criteria, and a fresh Findings Adversary that refutes false positives. Its reply starts with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`.

If the skill is not installed, run the same two passes yourself:

1. Spawn `adversarial-review:code-adversary` (fallback: `general-purpose` told to assume the change is broken and prove each finding with a failing input, `file:line`, and fix) with the diff command, changed files, and task context.
2. Spawn a **new** `adversarial-review:findings-adversary` (fallback: `general-purpose` told to refute each finding against the source) with the same inputs plus only the numbered findings, never the first agent's reasoning.

On NEEDS_FIXES, fix every surviving `blocking:` and `issue:`, rerun quality gates, and rerun the review against the new tip. Stop and ask the user after three rounds that still return NEEDS_FIXES. Put surviving `question:` findings you cannot settle from the code in the PR body rather than silently blocking. Do not start Phase 6 until the verdict is CLEAN.

## Phase 6 — Adversarial manual testing

From the branch tip after Phase 5, run the `adversarial-test` skill with the same task context file:

```text
Skill: adversarial-test:adversarial-test
Args:  --base origin/<default> --context <task-context-file>
```

It spawns a clean-context Test Adversary that derives acceptance criteria from the task, runs the real changed product surface in isolated state (service + probe, real CLI, sandbox), attacks happy paths, boundaries, malformed input, repeated/concurrent use, and adjacent flows, then reruns every reproduction to drop false failures. Automated tests, lint, build, and grep count only as supporting evidence. Its reply starts with `Test Verdict: PASS`, `Test Verdict: FAIL`, or `Test Verdict: BLOCKED`.

In the Sybra repository, invoke `sybra-test` instead.

If the skill is not installed, spawn `adversarial-test:test-adversary` (fallback: `general-purpose` told to prove the change does not satisfy the task by running the real surface in isolated temp state, and to report self-contained reproductions) with the repository, diff command, changed files, and task context only; then rerun each reproduction yourself before acting on it.

On FAIL, treat every surviving reproduction as a blocker: fix it, add a regression test, rerun quality gates, and rerun the skill against the new tip. After more than three unsuccessful fixes for the same reproduction, stop and ask the user. On BLOCKED, stop and surface the named human action. Do not open a PR until PASS.

## Phase 7 — Push and open the PR

Push the branch, create a PR against the default branch, and use the conventional lead-commit title. The body must have `## Motivation`, `## Implementation information`, and a changelog line, plus the source link:

| Source | PR title or body must contain |
| :-- | :-- |
| GitHub issue | `Closes #<number>` (`Closes owner/repo#<number>` when the issue lives in another repository) |
| Jira ticket | The Jira key, as a link to the ticket, in the body (and in the title when the repository's convention puts it there). Never `Closes` |
| Task description | No issue reference |

Capture the PR number.

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

For a GitHub issue, verify that `Closes #<number>` closed it. If it did not, close it with a completion comment. For a Jira ticket, leave it untouched and tell the user it is ready to transition. Report: source (GitHub issue, marked `created` when Phase 1 created it; Jira key; or task description), PR link, commits, CI status, Copilot threads resolved/total, and merged/closed status.

## Phase 12 — Return to the default branch

After merge, switch to the default branch, fast-forward it, and delete the local feature branch when safe.

## Hard stops

Stop and surface the exact next human action when the input is empty, unrecognized, or unreachable; the GitHub issue is already closed or actively owned; the Jira ticket is already finished; branch protection blocks merging; a Copilot thread loops more than three times; tests require disabling a check; `adversarial-test` returns BLOCKED; or the task needs a product/design decision that the repository cannot answer.
