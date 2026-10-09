---
name: gh-review-comments
description: List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Use when managing code review feedback, replying to reviewer remarks, resolving review conversations, creating reviews with line-level comments, or bulk-processing threads by author.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs bash, gh (authenticated), jq, python3 and network access to the GitHub API.
argument-hint: "<owner/repo> <pr-number> [--author <login>] [--reply <message>] [--resolve] [--unresolve] [--create-review] [--thread-id <id>] [--unresolved-only]"
allowed-tools: AskUserQuestion Agent Bash Read
user-invocable: true
metadata:
  short-description: Manage GitHub PR review threads with gh
---

<!-- justify: CF-side-effect All gh API operations target a specific PR the user is actively working on -->

# GH Review Comments

Wraps `gh api` (REST and GraphQL) via bash scripts to operate on PR review threads. Each action maps to a script in `scripts/`.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take `owner/repo`, the PR number, and the flags from the user's request. If either required value is still missing, ask for it before Phase 2 |
| Skill directory substitution | Claude Code replaces the placeholder at the start of every script command with this skill's absolute directory. If a script path below does not start with `/`, replace everything before `/scripts/` with the absolute path of the directory holding this SKILL.md. Never search plugin caches or the working directory for the scripts |
| AskUserQuestion | Ask the question in plain text and wait for the answer. If you cannot wait, stop and report what input is missing |
| Subagent tool (Agent) | Run the Phase 4 verification inline: re-run `scripts/list-threads.sh` yourself and compare before/after state. On Codex always run it inline, since Codex subagent fan-out is unreliable |
| `context: fork` | Not used; the skill runs in the main agent loop everywhere |

In Codex, run `gh auth status` before the first script call. If it or a later `gh api` call fails because of sandbox or network restrictions, rerun the same command with escalation (`sandbox_permissions=require_escalated`) and a short reason. If auth is invalid, ask the user to run `gh auth login`.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: `owner/repo` (e.g., `smykla-skalski/sai`) — **required**
- Second positional arg: PR number — **required**
- `--author <login>` — Filter threads by reviewer username
- `--thread-id <id>` — Target a specific thread by GraphQL node ID (`PRRT_...`)
- `--reply <message>` — Reply to matched threads with this message
- `--resolve` — Resolve matched threads (after replying if `--reply` also set)
- `--unresolve` — Unresolve (reopen) matched threads
- `--unresolved-only` — Only show/act on unresolved threads (auto-enabled with `--reply` or `--resolve`)
- `--create-review` — Enter review creation mode (see Phase 3 alternative)

## Actions Overview

| Mode | Flags | Behavior |
| :-- | :-- | :-- |
| List | (no action flags) | Display threads with IDs, author, body, resolution status |
| Reply | `--reply <msg>` | Reply to matched threads |
| Resolve | `--resolve` | Resolve matched threads |
| Reply + Resolve | `--reply <msg> --resolve` | Reply then resolve each thread |
| Unresolve | `--unresolve` | Reopen resolved threads |
| Create review | `--create-review` | Interactively create a review with line-level comments |

## Scripts

All scripts live in `scripts/` relative to this skill's base directory. Run them directly so users can allow-list by path pattern:

```
"${CLAUDE_SKILL_DIR}/scripts/<script>.sh" [args...]
```

### `scripts/list-threads.sh`

List review threads with metadata via GraphQL.

```
"${CLAUDE_SKILL_DIR}/scripts/list-threads.sh" <owner> <repo> <pr_number> [--author <login>] [--unresolved-only]
```

Output: one JSON line per thread with `thread_id`, `comment_id`, `author`, `body`, `path`, `line`, `is_resolved`, `is_outdated`, `reply_count`.

### `scripts/reply-thread.sh`

Reply to a review thread via REST API.

```
"${CLAUDE_SKILL_DIR}/scripts/reply-thread.sh" <owner> <repo> <pr_number> <comment_id> <body>
```

- `comment_id`: integer database ID of the **top-level** comment (from `list-threads.sh` `comment_id` field)
- Handles special characters (apostrophes, backticks, newlines) via JSON encoding

### `scripts/resolve-thread.sh`

Resolve a review thread via GraphQL.

```
"${CLAUDE_SKILL_DIR}/scripts/resolve-thread.sh" <thread_id>
```

- `thread_id`: GraphQL node ID (`PRRT_...`) from `list-threads.sh` `thread_id` field

### `scripts/unresolve-thread.sh`

Reopen a resolved review thread via GraphQL.

```
"${CLAUDE_SKILL_DIR}/scripts/unresolve-thread.sh" <thread_id>
```

### `scripts/add-review-comment.sh`

Manage comments on a pending review via GraphQL.
Supports adding (reply/new thread), editing, and deleting comments.

```
"${CLAUDE_SKILL_DIR}/scripts/add-review-comment.sh" <review_node_id> <body> --reply-to <comment_node_id>
"${CLAUDE_SKILL_DIR}/scripts/add-review-comment.sh" <review_node_id> <body> --new-thread <path> <line> [--start-line <start_line>] [<side>]
"${CLAUDE_SKILL_DIR}/scripts/add-review-comment.sh" --edit <comment_node_id> <body>
"${CLAUDE_SKILL_DIR}/scripts/add-review-comment.sh" --delete <comment_node_id>
```

- `review_node_id`: GraphQL node ID of the pending review (`PRR_...`)
- `comment_node_id`: GraphQL node ID of the comment (`PRRC_...`)
- `--reply-to`: reply to an existing thread
- `--new-thread`: create a new thread on a file/line (single-line or multi-line)
- `--start-line`: (optional, with `--new-thread`) start line for multi-line comments. Required for suggestion blocks that span multiple lines.
- `--edit`: edit an existing pending review comment body
- `--delete`: delete an existing pending review comment
- `side`: `RIGHT` (default) or `LEFT`

### `scripts/create-pending-review.sh`

Get or create the viewer's pending review on a PR via GraphQL.

```
"${CLAUDE_SKILL_DIR}/scripts/create-pending-review.sh" <owner> <repo> <pr_number> [<body>]
```

- GitHub allows one pending review per user per PR. If the viewer already has one, the script returns it (`created: false`) and creates nothing, so it is safe to re-run
- `body`: review body for a newly created review, ignored when one exists
- Output: `review_id` (`PRR_...`, pass it to `add-review-comment.sh`), `url`, `created`

### `scripts/create-review.sh`

Create and submit a PR review with line-level comments in one REST call.

```
"${CLAUDE_SKILL_DIR}/scripts/create-review.sh" <owner> <repo> <pr_number> <event> <body> [<comments_json>|-]
```

- `event`: `PENDING`, `COMMENT`, `APPROVE`, or `REQUEST_CHANGES`. `PENDING` omits the event field from the API payload, creating a draft review that is not yet submitted. Prefer `create-pending-review.sh` for drafts: `create-review.sh` fails if the viewer already has a pending review on the PR
- Output: `id`, `node_id` (`PRR_...`), `html_url`, `state`, `comment_count`
- `comments_json`: JSON array of comment objects, each with `path`, `line`, `body` (and optional `side`, defaults to `RIGHT`)
- Pass `-` as last arg to read comments from stdin

## Workflow

### Phase 1: Parse Arguments

1. Parse `$ARGUMENTS` for `owner/repo`, PR number, and flags
2. Split `owner/repo` into separate `OWNER` and `REPO` variables
3. Validate: both `owner/repo` and PR number are required
4. When `--reply` or `--resolve` is set, auto-enable `--unresolved-only`

### Phase 2: List Threads

1. Run `"${CLAUDE_SKILL_DIR}/scripts/list-threads.sh"` with owner, repo, PR number, and filters (`--author`, `--unresolved-only`)
2. If `--thread-id` is specified, filter output to only that thread
3. Display results to the user in a readable format:
   - Thread ID
   - Author
   - File path and line number
   - Resolution status
   - Body preview (first 80 chars)
   - Reply count

If no action flags are set, stop here.

### Phase 3: Execute Action

Read [references/gh-api-guide.md](references/gh-api-guide.md) for ID type mapping (REST integer IDs vs GraphQL node IDs), reply endpoint constraints, and shell quoting patterns.

For each matched thread, execute the requested action:

**Reply** (`--reply`):

1. Extract `comment_id` from the thread data
2. Run `"${CLAUDE_SKILL_DIR}/scripts/reply-thread.sh"` with owner, repo, PR number, comment_id, and the reply message
3. Report the created reply URL

**Resolve** (`--resolve`):

1. Extract `thread_id` from the thread data
2. Run `"${CLAUDE_SKILL_DIR}/scripts/resolve-thread.sh"` with thread_id
3. Report success

**Reply + Resolve** (`--reply` and `--resolve` together):

1. Reply first (as above)
2. Resolve second (as above)
3. Report both results

**Unresolve** (`--unresolve`):

1. Extract `thread_id` from the thread data
2. Run `"${CLAUDE_SKILL_DIR}/scripts/unresolve-thread.sh"` with thread_id
3. Report success

### Phase 3 (alternative): Create Review

When `--create-review` is specified, skip Phase 2 actions and instead:

1. Use AskUserQuestion for the review event type (PENDING, COMMENT, APPROVE, or REQUEST_CHANGES)
2. Use AskUserQuestion for the review body text
3. Use AskUserQuestion for inline comments - for each comment, collect:
   - File path (validate it exists in the PR diff)
   - Line number
   - Comment body
4. For `PENDING`: run `"${CLAUDE_SKILL_DIR}/scripts/create-pending-review.sh"` with owner, repo, PR number, and body, then add each comment with `add-review-comment.sh <review_id> <body> --new-thread <path> <line>`. If it returns `created: false`, tell the user their comments go into their existing pending review. Report the review URL and comment count, then skip steps 5-7
5. Otherwise build the comments JSON array and run `"${CLAUDE_SKILL_DIR}/scripts/create-review.sh"` **exactly once** with the collected data
6. The script returns `comment_count` from the submitted payload (not from the API response). If the script exits 0, the review and all comments were submitted atomically - treat it as fully successful
7. Report the created review URL and comment count

**NEVER re-run `create-review.sh` after it exits 0.** The GitHub review creation API is atomic: if the call succeeds, the review body and all inline comments were attached.
Running it again creates a duplicate review. There is no partial success - it either all works or the script fails with a non-zero exit.

### Phase 4: Verify and Summarize

**For reply/resolve/unresolve actions:** spawn a `general-purpose` verification agent with the Agent tool (without a subagent tool, run the same checks inline). Pass it:

- The PR identifier (`owner/repo#number`)
- The action performed (`reply`, `resolve`, `unresolve`, or combination)
- The before-state thread data captured in Phase 2 (thread IDs with their resolution status and reply counts)
- The absolute path to the list-threads script (resolved as described in [Agent compatibility](#agent-compatibility)): `"${CLAUDE_SKILL_DIR}/scripts/list-threads.sh"`

The agent must:

1. Re-run `list-threads.sh` with the same owner, repo, PR number, and filters used in Phase 2
2. Compare before/after state for each acted-on thread (resolution status for resolve/unresolve, reply count for reply)
3. Return ONLY: verification result (`success`, `partial`, or `failed`), count of successful operations, count of failed operations, and a list of any failed thread IDs with the reason

Display the agent's verification summary to the user along with:

- Total threads matched/acted on
- Actions taken (replies sent, threads resolved/unresolved)
- Link to the PR on GitHub

**For create-review:** do NOT spawn a verification agent. Do NOT re-list threads.
The `create-review.sh` script output is the sole source of truth.
If it exited 0 and returned a `comment_count` and `html_url`, the review was created with all comments attached.
Report the review URL and comment count directly.

## Error Handling

- If a thread operation fails, log the error and continue with remaining threads
- If `--thread-id` matches no thread, report "No matching thread found"
- If `create-review.sh` fails (non-zero exit), report the error to the user. Do not retry automatically - the most common cause is invalid file paths or line numbers not present in the PR diff. Ask the user to verify the comment targets before re-attempting

## Example Invocations

<example>
List threads (read-only):

```bash
/gh-review-comments smykla-skalski/sai 4
/gh-review-comments smykla-skalski/sai 4 --unresolved-only
/gh-review-comments smykla-skalski/sai 4 --author Automaat
```
</example>

<example>
Reply and resolve:

```bash
/gh-review-comments smykla-skalski/sai 4 --author Automaat --reply "Fixed in latest push"
/gh-review-comments smykla-skalski/sai 4 --author bartsmykla --reply "Done" --resolve
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --resolve
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --reply "Done, thanks!" --resolve
```
</example>

<example>
Unresolve or create a new review:

```bash
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --unresolve
/gh-review-comments smykla-skalski/sai 4 --create-review
```
</example>
