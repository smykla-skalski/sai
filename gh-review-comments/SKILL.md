---
name: gh-review-comments
description: List, reply to, resolve, and create GitHub PR review comment threads using gh CLI scripts. Use when managing code review feedback, replying to reviewer remarks, resolving review conversations, creating reviews with line-level comments, or bulk-processing threads by author.
argument-hint: "<owner/repo> <pr-number> [--author <login>] [--reply <message>] [--resolve] [--unresolve] [--create-review] [--thread-id <id>] [--unresolved-only]"
allowed-tools: Bash, Read, Grep, Glob
user-invocable: true
---

# GH Review Comments

Wraps `gh api` (REST and GraphQL) via bash scripts to operate on PR review threads. Each action maps to a script in `scripts/`.

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

| Mode            | Flags                     | Behavior                                                  |
|:----------------|:--------------------------|:----------------------------------------------------------|
| List            | (no action flags)         | Display threads with IDs, author, body, resolution status |
| Reply           | `--reply <msg>`           | Reply to matched threads                                  |
| Resolve         | `--resolve`               | Resolve matched threads                                   |
| Reply + Resolve | `--reply <msg> --resolve` | Reply then resolve each thread                            |
| Unresolve       | `--unresolve`             | Reopen resolved threads                                   |
| Create review   | `--create-review`         | Interactively create a review with line-level comments    |

## Scripts

All scripts live in `scripts/` relative to this skill's base directory. **Always run with `bash` explicitly** (execute bits may not survive plugin cache):

```
SKILL_DIR="<this skill's base directory>"
bash "$SKILL_DIR/scripts/<script>.sh" [args...]
```

### `scripts/list-threads.sh`

List review threads with metadata via GraphQL.

```
bash "$SKILL_DIR/scripts/list-threads.sh" <owner> <repo> <pr_number> [--author <login>] [--unresolved-only]
```

Output: one JSON line per thread with `thread_id`, `comment_id`, `author`, `body`, `path`, `line`, `is_resolved`, `is_outdated`, `reply_count`.

### `scripts/reply-thread.sh`

Reply to a review thread via REST API.

```
bash "$SKILL_DIR/scripts/reply-thread.sh" <owner> <repo> <pr_number> <comment_id> <body>
```

- `comment_id`: integer database ID of the **top-level** comment (from `list-threads.sh` `comment_id` field)
- Handles special characters (apostrophes, backticks, newlines) via JSON encoding

### `scripts/resolve-thread.sh`

Resolve a review thread via GraphQL.

```
bash "$SKILL_DIR/scripts/resolve-thread.sh" <thread_id>
```

- `thread_id`: GraphQL node ID (`PRRT_...`) from `list-threads.sh` `thread_id` field

### `scripts/unresolve-thread.sh`

Reopen a resolved review thread via GraphQL.

```
bash "$SKILL_DIR/scripts/unresolve-thread.sh" <thread_id>
```

### `scripts/create-review.sh`

Create a PR review with line-level comments via REST API.

```
bash "$SKILL_DIR/scripts/create-review.sh" <owner> <repo> <pr_number> <event> <body> [<comments_json>|-]
```

- `event`: `COMMENT`, `APPROVE`, or `REQUEST_CHANGES`
- `comments_json`: JSON array of comment objects, each with `path`, `line`, `body` (and optional `side`, defaults to `RIGHT`)
- Pass `-` as last arg to read comments from stdin

## Workflow

### Phase 1: Parse Arguments

1. Parse `$ARGUMENTS` for `owner/repo`, PR number, and flags
2. Split `owner/repo` into separate `OWNER` and `REPO` variables
3. Validate: both `owner/repo` and PR number are required
4. When `--reply` or `--resolve` is set, auto-enable `--unresolved-only`
5. Resolve `SKILL_DIR` — the base directory of this skill (where SKILL.md lives)

### Phase 2: List Threads

1. Run `bash "$SKILL_DIR/scripts/list-threads.sh"` with owner, repo, PR number, and filters (`--author`, `--unresolved-only`)
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

For each matched thread, execute the requested action:

**Reply** (`--reply`):

1. Extract `comment_id` from the thread data
2. Run `bash "$SKILL_DIR/scripts/reply-thread.sh"` with owner, repo, PR number, comment_id, and the reply message
3. Report the created reply URL

**Resolve** (`--resolve`):

1. Extract `thread_id` from the thread data
2. Run `bash "$SKILL_DIR/scripts/resolve-thread.sh"` with thread_id
3. Report success

**Reply + Resolve** (`--reply` and `--resolve` together):

1. Reply first (as above)
2. Resolve second (as above)
3. Report both results

**Unresolve** (`--unresolve`):

1. Extract `thread_id` from the thread data
2. Run `bash "$SKILL_DIR/scripts/unresolve-thread.sh"` with thread_id
3. Report success

### Phase 3 (alternative): Create Review

When `--create-review` is specified, skip Phase 2 actions and instead:

1. Ask the user for the review event type (COMMENT, APPROVE, or REQUEST_CHANGES)
2. Ask for the review body text
3. Ask for inline comments — for each comment, collect:
   - File path (validate it exists in the PR diff)
   - Line number
   - Comment body
4. Build the comments JSON array
5. Run `bash "$SKILL_DIR/scripts/create-review.sh"` with the collected data
6. Report the created review URL

### Phase 4: Verify and Summarize

1. After mutations (reply/resolve/unresolve), re-run `bash "$SKILL_DIR/scripts/list-threads.sh"` to confirm the operations took effect
2. Compare before/after thread states — flag any threads that failed to change

Report:

- Total threads matched/acted on
- Actions taken (replies sent, threads resolved/unresolved, review created)
- Verification result (all succeeded vs. failures with details)
- Link to the PR on GitHub

## Error Handling

- If a thread operation fails, log the error and continue with remaining threads
- If `--thread-id` matches no thread, report "No matching thread found"

## References

Read [references/gh-api-guide.md](references/gh-api-guide.md) for detailed API documentation including ID type mapping, REST vs GraphQL differences, permissions, rate limits, and practical gotchas.

## Example Invocations

```bash
# List all review threads on a PR
/gh-review-comments smykla-skalski/sai 4

# List only unresolved threads
/gh-review-comments smykla-skalski/sai 4 --unresolved-only

# List threads from a specific reviewer
/gh-review-comments smykla-skalski/sai 4 --author Automaat

# Reply to all unresolved threads from a reviewer
/gh-review-comments smykla-skalski/sai 4 --author Automaat --reply "Fixed in latest push"

# Reply and resolve all threads from a reviewer
/gh-review-comments smykla-skalski/sai 4 --author bartsmykla --reply "Done" --resolve

# Resolve a specific thread without replying
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --resolve

# Reply to and resolve a specific thread
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --reply "Done, thanks!" --resolve

# Unresolve a thread (reopen it)
/gh-review-comments smykla-skalski/sai 4 --thread-id PRRT_kwDOCnTGG85tgSD3 --unresolve

# Create a review with line-level comments
/gh-review-comments smykla-skalski/sai 4 --create-review
```
