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

# --- GraphQL query (hardcoded values to avoid bash $ interpolation issues) ---
QUERY=$(cat <<GRAPHQL
{
  repository(owner: "${OWNER}", name: "${REPO}") {
    pullRequest(number: ${PR_NUMBER}) {
      reviewThreads(first: 100) {
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
}
GRAPHQL
)

# --- Build jq filter ---
JQ_FILTER='.data.repository.pullRequest.reviewThreads.nodes[]'

# Filter: unresolved only
if [[ "$UNRESOLVED_ONLY" == "true" ]]; then
  JQ_FILTER="${JQ_FILTER} | select(.isResolved == false)"
fi

# Filter: by author (first comment author)
if [[ -n "$AUTHOR_FILTER" ]]; then
  JQ_FILTER="${JQ_FILTER} | select(.comments.nodes[0].author.login == \"${AUTHOR_FILTER}\")"
fi

# Format output
JQ_FILTER="${JQ_FILTER} | {thread_id: .id, comment_id: .comments.nodes[0].databaseId, author: .comments.nodes[0].author.login, body: .comments.nodes[0].body, path: .path, line: .line, is_resolved: .isResolved, is_outdated: .isOutdated, reply_count: (.comments.nodes | length - 1)}"

# --- Execute ---
gh api graphql -f query="$QUERY" --jq "$JQ_FILTER"
