# Resolving the ship-it input

How ship-it turns its arguments into a task source. Make no repository changes (no branch, edit or commit) until the input is resolved.

## Flags

If the first token is `--issue`, strip it and remember the flag. An `--issue` anywhere else is part of the description ("add support for --issue"). `--issue` applies only to task descriptions; with a URL or reference, say it is ignored and continue.

## Classification

| Input | Source | Example |
| :-- | :-- | :-- |
| Empty | Stop and ask for a task description, a GitHub issue URL, or a Jira URL | |
| Explicitly approved complex plan | Orchestration: preserve its approved scope and acceptance criteria; resolve or create its umbrella and implementation subissues | Approved plan in the conversation or a supplied plan file |
| GitHub umbrella issue with implementation subissues | Orchestration: read native subissues and their dependencies; reuse the umbrella | `https://github.com/owner/repo/issues/123` |
| GitHub issue URL (github.com or a GitHub Enterprise host `gh` is authenticated for), `owner/repo#N`, or `#N` in the current repository | GitHub issue | `https://github.com/owner/repo/issues/123` |
| Jira issue URL | Jira ticket | `https://<site>.atlassian.net/browse/KEY-123`, or any `atlassian.net` or Jira URL whose path ends in a `KEY-123` segment (`.../projects/KEY/issues/KEY-123`, service-desk queue links) or that has `selectedIssue=KEY-123` |
| A lone URL or reference that matches neither (GitHub PR, commit, discussion, a host that is neither GitHub nor Jira) | Unrecognized: stop | `https://github.com/owner/repo/pull/7` |
| Anything else | Task description | `add a --json flag to the export command` |

Edge cases:

- A task description that embeds a GitHub issue URL, an `owner/repo#N` reference, or a Jira issue URL uses that source and treats the rest as extra context. An explicitly approved complex plan takes precedence; its issue links identify the umbrella or children.
- A plan must be explicitly approved. A draft, proposed, or merely pasted plan is not an approved plan. A GitHub issue is an umbrella only when it contains native implementation subissues or explicitly describes itself as the parent of an approved plan. A lone implementation issue stays on the single-change path, even if its title mentions orchestration.
- A bare `#N` inside free text ("make #333 the default color") is a GitHub issue only when the text calls it one ("fixes #42", "issue #42") **and** either the text is little more than that reference ("fix #42") or the issue's title matches the task. Otherwise it stays part of the description, so merging never closes an unrelated issue.
- Every stop while resolving the input names what was received and what the skill accepts, then ends the turn.

## Task description

Without `--issue`, ship the description as is: no issue is created and none is searched for. Derive a short title and testable acceptance criteria from the description and the repository; do not invent requirements the description does not imply.

With `--issue`:

1. Resolve the target repository from the current directory with `gh repo view --json nameWithOwner`.
2. Search for an existing open issue that already covers the task: `gh issue list --state open --search "<key terms>" --json number,title,url --limit 10`. Reuse it only when it is clearly the same work; otherwise create a new one.
3. Write a title (plain English, ≤70 characters, no conventional-commit prefix) and a body with `## Motivation`, `## Scope`, and `## Acceptance criteria` (testable, one per bullet). Use the `issue-authoring` skill for the writing when it is available.
4. `gh issue create --title "<title>" --body "<body>"`, adding `--label <label>` only when a fitting label already exists (`gh label list`). Capture the number and URL.
5. Continue with the created issue as a GitHub issue source and mark it `created` for the final report. Do not ask for confirmation.

## GitHub issue

Parse the owner, repository, and issue number, then inspect the issue with `gh issue view` including title, body, labels, assignees, milestone, state, comments, and subissues. If this `gh` version cannot return subissues, query `repository.issue.subIssues` through `gh api graphql -H "GraphQL-Features: sub_issues"`; paginate until all children are known. If neither read works, stop rather than assume the issue is a leaf. If `gh` cannot find or read the issue, stop and report the error. Stop if it is closed. Extract scope hints from labels and linked PRs from comments. Route an umbrella to orchestration even if assigned to its maintainer; assess each child's ownership and PR before dispatch. Route an implementation issue to the single-change lifecycle, but stop if it is actively owned by someone else.

## Jira ticket

Extract the key case-insensitively (`[A-Za-z][A-Za-z0-9_]+-[0-9]+`; Jira accepts `/browse/proj-123`), uppercase it (`PROJ-123`), and take the site (the URL's host). Use only sources that target that site: the same key can exist on another site, so a source logged into a different site would read the wrong ticket. Read the ticket with the first site-matching source that works, moving to the next on a missing tool, an auth error, or a not-found answer (Jira returns the same not-found for a ticket the account cannot see):

1. Atlassian MCP tools. In Claude Code load them with ToolSearch (query `atlassian jira`); on Codex, Copilot CLI and opencode use them only when the session already lists them. Skip them when the site is not among the sites they can reach (for example `getAccessibleAtlassianResources`); otherwise use the issue-read tool (for example `getJiraIssue`) with the key and that site.
2. `acli jira workitem view <KEY>` when `command -v acli` succeeds and `acli jira auth status` shows the URL's site.
3. `jira issue view <KEY> --plain` when `command -v jira` succeeds and the `server` in its config (`~/.config/.jira/.config.yml`, or `JIRA_CONFIG_FILE`) is the URL's site.
4. No site-matching source worked: ask the user to paste the ticket summary and description as plain text, then end the turn. Continue when they reply.

After a read, confirm the ticket's own link points at the URL's site; a mismatch counts as that source missing.

Capture the key, summary, description, status, and acceptance criteria.

- Not found: if every site-matching source answers not-found, stop and report that the ticket does not exist or none of the configured accounts can see it, and name the sources tried. Do not fall through to the paste request.
- Done: if the ticket is finished, stop and report it. Finished means its status category is Done (`statusCategory.key` is `done`), or, when the source shows only a status name, the name is Done, Closed, Resolved, or Won't Do.
- Read-only: never transition, assign, comment on, or edit the ticket unless the user asks.

## Durable task checkpoint

After resolving the task source, read the checkpoint contract linked by the skill. Derive its canonical task key, then create or resume the corresponding checkpoint before exploring or changing the repository. The checkpoint replaces the temporary task context file and is the `--context <file>` passed to review and test gates.

Do not overwrite an existing checkpoint during resolution. Validate it, verify its task source and repository identity, and reconcile it with Git and GitHub as the contract requires. A completed checkpoint is a delivered task, not a fresh run. Invalid, mismatched or irreconcilable state is a hard stop with the recovery action from the contract.
