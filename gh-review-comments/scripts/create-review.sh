#!/usr/bin/env bash
# create-review.sh — Create a PR review with line-level comments via REST API.
#
# Usage:
#   ./create-review.sh <owner> <repo> <pr_number> <event> <body> [<comments_json>]
#
# Arguments:
#   owner         — Repository owner (e.g., "smykla-skalski")
#   repo          — Repository name (e.g., "sai")
#   pr_number     — Pull request number
#   event         — Review event: COMMENT, APPROVE, or REQUEST_CHANGES
#   body          — Review body text (use "" for no body)
#   comments_json — JSON array of comment objects (optional, read from stdin if "-")
#
# Comment object format:
#   {"path": "file.go", "line": 42, "body": "Fix this", "side": "RIGHT"}
#
# The "side" field defaults to "RIGHT" if omitted.
#
# Output: JSON with review id, html_url, state, and number of comments submitted.
#
# Examples:
#   # Review with inline body and comments
#   ./create-review.sh owner repo 123 COMMENT "LGTM overall" \
#     '[{"path":"main.go","line":10,"body":"Nit: unused import"}]'
#
#   # Review with comments from stdin
#   echo '[{"path":"main.go","line":10,"body":"Fix this"}]' | \
#     ./create-review.sh owner repo 123 REQUEST_CHANGES "Needs fixes" -
#
#   # Approve with no comments
#   ./create-review.sh owner repo 123 APPROVE "Looks good!"
#
# Dependencies: gh (GitHub CLI), python3 (for JSON encoding)
set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> <event> <body> [<comments_json>|-]" >&2
  echo "  event: COMMENT, APPROVE, or REQUEST_CHANGES" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
EVENT="$4"
BODY="$5"
COMMENTS_SOURCE="${6:-}"

# Validate event
case "$EVENT" in
  COMMENT|APPROVE|REQUEST_CHANGES) ;;
  *)
    echo "Error: event must be COMMENT, APPROVE, or REQUEST_CHANGES (got: $EVENT)" >&2
    exit 1
    ;;
esac

# Build the review JSON payload
if [[ "$COMMENTS_SOURCE" == "-" ]]; then
  COMMENTS_JSON=$(cat)
elif [[ -n "$COMMENTS_SOURCE" ]]; then
  COMMENTS_JSON="$COMMENTS_SOURCE"
else
  COMMENTS_JSON="[]"
fi

# Validate: COMMENT/REQUEST_CHANGES require either body or comments
if [[ "$EVENT" != "APPROVE" && -z "$BODY" && ("$COMMENTS_JSON" == "[]" || -z "$COMMENTS_JSON") ]]; then
  echo "Error: $EVENT review requires a body or comments (got neither)" >&2
  exit 1
fi

# Use python3 to safely construct the full JSON payload
PAYLOAD=$(python3 -c "
import json, sys

body = sys.argv[1]
event = sys.argv[2]
comments_raw = sys.argv[3]

comments = json.loads(comments_raw) if comments_raw.strip() else []

# Ensure each comment has 'side' defaulting to 'RIGHT'
for c in comments:
    c.setdefault('side', 'RIGHT')

payload = {'event': event, 'comments': comments}
if body:
    payload['body'] = body

print(json.dumps(payload))
" "$BODY" "$EVENT" "$COMMENTS_JSON")

echo "$PAYLOAD" | gh api "repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/reviews" \
  --input - \
  --jq '{id: .id, html_url: .html_url, state: .state, comment_count: (.comments // [] | length)}'
