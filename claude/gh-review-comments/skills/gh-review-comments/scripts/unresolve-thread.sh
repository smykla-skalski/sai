#!/usr/bin/env bash
# unresolve-thread.sh — Unresolve (reopen) a resolved PR review thread via GraphQL.
#
# Usage:
#   ./unresolve-thread.sh <thread_id>
#
# Arguments:
#   thread_id — GraphQL node ID of the thread (e.g., "PRRT_kwDOCnTGG85tgSD3")
#               Obtain from list-threads.sh output (thread_id field).
#
# Output: JSON confirming unresolve {thread_id, is_resolved}.
#
# Dependencies: gh (GitHub CLI)
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <thread_id>" >&2
  exit 1
fi

THREAD_ID="$1"

# shellcheck disable=SC2016
MUTATION='mutation($threadId: ID!) {
  unresolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}'

gh api graphql \
  -f threadId="$THREAD_ID" \
  -f query="$MUTATION" \
  --jq '{thread_id: .data.unresolveReviewThread.thread.id, is_resolved: .data.unresolveReviewThread.thread.isResolved}'
