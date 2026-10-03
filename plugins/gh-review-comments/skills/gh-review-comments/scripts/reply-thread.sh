#!/usr/bin/env bash
# reply-thread.sh — Reply to a PR review comment thread via REST API.
#
# Usage:
#   ./reply-thread.sh <owner> <repo> <pr_number> <comment_id> <body>
#
# Arguments:
#   owner       — Repository owner (e.g., "smykla-skalski")
#   repo        — Repository name (e.g., "sai")
#   pr_number   — Pull request number
#   comment_id  — Integer database ID of the TOP-LEVEL comment in the thread
#   body        — Reply text (supports Markdown)
#
# Output: JSON with id, html_url, body of the created reply.
#
# IMPORTANT: comment_id must be a top-level comment (where in_reply_to_id is null).
#            Use list-threads.sh to get the correct comment_id for each thread.
#
# Dependencies: gh (GitHub CLI), python3 (for JSON encoding)
set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> <comment_id> <body>" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
COMMENT_ID="$4"
BODY="$5"

# JSON-encode the body to handle special characters, then pipe to gh api
BODY_JSON=$(python3 -c "import json,sys; print(json.dumps({'body': sys.argv[1]}))" "$BODY")

echo "$BODY_JSON" | gh api "repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/comments/${COMMENT_ID}/replies" \
  --input - \
  --jq '{id: .id, html_url: .html_url, body: .body}'
