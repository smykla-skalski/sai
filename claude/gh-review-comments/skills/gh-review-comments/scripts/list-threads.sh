#!/usr/bin/env bash
# list-threads.sh — List PR review threads with IDs, resolution status, and metadata.
#
# Usage:
#   ./list-threads.sh <owner> <repo> <pr_number> [--author <login>] [--unresolved-only]
#
# Output: One JSON object per line with thread_id, comment_id, author, body, path,
#         line, is_resolved, is_outdated.
#
# Dependencies: gh (GitHub CLI)
set -euo pipefail

# --- Argument parsing ---
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> [--author <login>] [--unresolved-only]" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
shift 3

AUTHOR_FILTER=""
UNRESOLVED_ONLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --author)
      AUTHOR_FILTER="$2"
      shift 2
      ;;
    --unresolved-only)
      UNRESOLVED_ONLY="true"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# --- GraphQL query with variables (avoids injection into query string) ---
# shellcheck disable=SC2016
QUERY='query($owner: String!, $repo: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          comments(first: 10) {
            nodes {
              databaseId
              body
              author { login }
              createdAt
            }
          }
        }
      }
    }
  }
}'

# --- Build jq filter ---
JQ_FILTER='.data.repository.pullRequest.reviewThreads.nodes[]'

# Filter: unresolved only
if [[ "$UNRESOLVED_ONLY" == "true" ]]; then
  JQ_FILTER="${JQ_FILTER} | select(.isResolved == false)"
fi

# Filter: by author (first comment author) — use --arg to avoid jq injection
JQ_AUTHOR_ARGS=()
if [[ -n "$AUTHOR_FILTER" ]]; then
  JQ_FILTER="${JQ_FILTER} | select(.comments.nodes[0].author.login == \$author)"
  JQ_AUTHOR_ARGS=(--arg author "$AUTHOR_FILTER")
fi

# Format output
JQ_FILTER="${JQ_FILTER} | {thread_id: .id, comment_id: .comments.nodes[0].databaseId, author: .comments.nodes[0].author.login, body: .comments.nodes[0].body, path: .path, line: .line, is_resolved: .isResolved, is_outdated: .isOutdated, reply_count: (.comments.nodes | length - 1)}"

# --- Execute with cursor-based pagination ---
CURSOR=""
while true; do
  ARGS=(
    -f query="$QUERY"
    -f owner="$OWNER"
    -f repo="$REPO"
    -F number="$PR_NUMBER"
  )
  if [[ -n "$CURSOR" ]]; then
    ARGS+=(-f cursor="$CURSOR")
  fi

  RESPONSE=$(gh api graphql "${ARGS[@]}")

  # Emit matching threads from this page
  echo "$RESPONSE" | jq -r ${JQ_AUTHOR_ARGS[@]+"${JQ_AUTHOR_ARGS[@]}"} "$JQ_FILTER"

  # Check for next page
  HAS_NEXT=$(echo "$RESPONSE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')
  if [[ "$HAS_NEXT" != "true" ]]; then
    break
  fi
  CURSOR=$(echo "$RESPONSE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor')
done
