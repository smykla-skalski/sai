---
name: gh-review-comments
description: List, reply to, resolve, unresolve, and create GitHub PR review comment threads using gh CLI scripts.
---

# GH Review Comments

Use this skill when the user wants to manage pull request review threads on GitHub (list, reply, resolve, unresolve, or create a review with inline comments).

## Inputs to infer from natural-language requests

Extract these values from the user request or current repository context:

- `owner/repo` (required)
- PR number (required)
- optional reviewer filter: `--author <login>`
- optional target thread: `--thread-id <PRRT_...>`
- optional action details:
  - `--reply <message>`
  - `--resolve`
  - `--unresolve`
  - `--create-review`
  - `--unresolved-only`

If action details are missing, default to listing threads first and ask a focused follow-up question.

## Auth and sandbox preflight (Codex-specific)

Before any script call:

1. Run `gh auth status`.
2. If the command fails due sandbox/network restrictions, rerun the same command with `sandbox_permissions=require_escalated` and a short justification.
3. If auth is not valid, ask the user to authenticate with `gh auth login`, then re-run `gh auth status`.
4. If a later `gh api` call fails due sandbox/network restrictions, rerun that command with escalation.

## Script directory

Resolve `SKILL_DIR` to this skill's own directory (the folder that holds `scripts/`). Do not hardcode another machine's absolute path:

```bash
# From a sai checkout the repo-relative path works; otherwise locate the installed
# copy under the Codex plugins cache.
SKILL_DIR="codex/gh-review-comments"
if [ ! -d "$SKILL_DIR/scripts" ]; then
  found="$(find "${CODEX_HOME:-$HOME/.codex}/plugins" -type f -name list-threads.sh -path '*gh-review-comments*' 2>/dev/null | head -n1)"
  [ -n "$found" ] && SKILL_DIR="$(dirname "$(dirname "$found")")"
fi
```

Run scripts from that directory so behavior is consistent:

```bash
"$SKILL_DIR/scripts/<script>.sh" [args...]
```

## Scripts

### `scripts/list-threads.sh`

```bash
"$SKILL_DIR/scripts/list-threads.sh" <owner> <repo> <pr_number> [--author <login>] [--unresolved-only]
```

Output: one JSON line per thread with `thread_id`, `comment_id`, `author`, `body`, `path`, `line`, `is_resolved`, `is_outdated`, `reply_count`.

### `scripts/reply-thread.sh`

```bash
"$SKILL_DIR/scripts/reply-thread.sh" <owner> <repo> <pr_number> <comment_id> <body>
```

- `comment_id` must be the integer top-level comment ID from `list-threads.sh`.

### `scripts/resolve-thread.sh`

```bash
"$SKILL_DIR/scripts/resolve-thread.sh" <thread_id>
```

- `thread_id` must be the GraphQL node ID (`PRRT_...`) from `list-threads.sh`.

### `scripts/unresolve-thread.sh`

```bash
"$SKILL_DIR/scripts/unresolve-thread.sh" <thread_id>
```

### `scripts/create-review.sh`

```bash
"$SKILL_DIR/scripts/create-review.sh" <owner> <repo> <pr_number> <event> <body> [<comments_json>|-]
```

- `event`: `COMMENT`, `APPROVE`, or `REQUEST_CHANGES`
- `comments_json`: array of objects with `path`, `line`, `body`, optional `side` (defaults to `RIGHT`)
- pass `-` to read comments JSON from stdin

## Workflow

### 1. Interpret intent

Map user request to one of:

- List threads
- Reply to threads
- Resolve threads
- Reply then resolve
- Unresolve threads
- Create review with inline comments

For reply/resolve operations, enable unresolved filtering unless the user explicitly asks otherwise.

### 2. List threads

1. Run `list-threads.sh` with required args and any filters.
2. If `--thread-id` is provided, filter to that thread.
3. Present thread summary (id, author, file/line, resolution status, short body preview, reply count).

If no action is requested, stop here.

### 3. Execute thread actions

For each matched thread:

- Reply: use `comment_id` with `reply-thread.sh`
- Resolve: use `thread_id` with `resolve-thread.sh`
- Unresolve: use `thread_id` with `unresolve-thread.sh`
- Reply + Resolve: run reply first, then resolve

Continue processing remaining threads if one fails; report partial failures clearly.

### 4. Create review (alternative path)

When the user asks to create a review:

1. Collect `event`, review body, and inline comments.
2. Validate each inline comment target against files/lines in the PR diff.
3. Run `create-review.sh` exactly once.
4. If it exits 0, treat it as success for the full review payload.

Do not automatically retry `create-review.sh` after a successful run because that creates duplicate reviews.

### 5. Verify and summarize

- For reply/resolve/unresolve: re-run `list-threads.sh` and compare before/after states.
- For create-review: use `create-review.sh` success output as source of truth.

Report:

- total matched threads
- actions executed
- verification results (successes/failures)
- relevant GitHub URLs

## Error handling

- If `--thread-id` matches nothing, report no matching thread.
- If one thread operation fails, continue with remaining matches and summarize failures.
- If `create-review.sh` fails, report error and likely cause (for example invalid `path`/`line` targets).

Read `references/gh-api-guide.md` before taking action to avoid ID mismatches between REST integer IDs and GraphQL node IDs.

## Example user requests (Codex style)

- "List all review threads on `smykla-skalski/sai` PR `4`."
- "Show only unresolved threads by `Automaat` on `smykla-skalski/sai` PR `4`."
- "Reply `Fixed in latest push` to unresolved threads by `Automaat` on PR `4`."
- "Resolve thread `PRRT_kwDOCnTGG85tgSD3` on `smykla-skalski/sai` PR `4`."
- "Reply `Done, thanks!` and resolve thread `PRRT_kwDOCnTGG85tgSD3` on PR `4`."
- "Create a `REQUEST_CHANGES` review on `smykla-skalski/sai` PR `4` with inline comments."
