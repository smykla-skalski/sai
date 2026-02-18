# GitHub PR Review Comments: API Reference

Practical reference for listing, replying to, and resolving pull request review comment threads using `gh api` (REST and GraphQL).

## Table of Contents

- [ID Types](#id-types)
- [REST Endpoints](#rest-endpoints)
- [GraphQL Mutations](#graphql-mutations)
- [Practical Gotchas](#practical-gotchas)
- [Permissions](#permissions)

## ID Types

| What | Format Example | Where Used |
|------|----------------|------------|
| REST comment ID | `2815685985` (integer) | REST reply endpoint |
| Thread node ID | `PRRT_kwDOCnTGG85tgSD3` (string) | GraphQL resolve/unresolve |
| Comment node ID | `PRRC_kwDOCnTGG86l3xmZ` (string) | GraphQL reply mutation |
| GraphQL `databaseId` | Same as REST integer ID | Bridges REST ↔ GraphQL |

## REST Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List PR review comments | GET | `/repos/{owner}/{repo}/pulls/{pull_number}/comments` |
| Get single review comment | GET | `/repos/{owner}/{repo}/pulls/comments/{comment_id}` |
| Reply to review comment | POST | `/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies` |

### Reply Constraint

The `comment_id` in the reply endpoint **must** be a top-level comment (`in_reply_to_id == null`). Replying to a reply returns an error.

### `gh pr view` Limitations

- `--json reviews` shows review-level data (approve/comment/request changes) but NOT individual comments or thread resolution.
- `--json comments` shows PR conversation comments, NOT review comments on code lines.
- **For review thread data, use `gh api` directly.**

## GraphQL Mutations

| Operation | Mutation | Key Input |
|-----------|----------|-----------|
| Resolve thread | `resolveReviewThread` | `threadId` (ID!) |
| Unresolve thread | `unresolveReviewThread` | `threadId` (ID!) |
| Reply to thread | `addPullRequestReviewThreadReply` | `pullRequestReviewThreadId` (ID!), `body` (String!) |

Thread resolution is **GraphQL only** — no REST equivalent.

## Practical Gotchas

### GraphQL `$` Variables in Queries

Bash interprets `$owner`, `$repo` in query strings before `gh` sees them, causing `UNKNOWN_CHAR` errors. Two solutions:

1. **Hardcode values** directly in the query string (simplest)
2. **Use shell variable substitution** via heredoc with double quotes

Variables **do** work for mutations (`-f threadId=...`) because the variable names are passed via `-f` flags, not embedded in the query string with `$`.

### Use `--jq` Over External Parsers

`gh api graphql` can output data that breaks external JSON parsers. Use the built-in `--jq` flag instead of piping to `jq` or `python3`.

### Shell Quoting for Apostrophes

For reply bodies with apostrophes, either:
- JSON-encode the body (what `reply-thread.sh` does)
- Use `'\''` escape pattern in `-f body='...'`
- Use `--input` with a heredoc

## Permissions

- **PAT (classic):** needs `repo` scope
- **Fine-grained PAT:** needs `Pull requests: Read and write`
- **Rate limiting:** GraphQL has 5000 points/hour. Mutations cost 1 point each.
