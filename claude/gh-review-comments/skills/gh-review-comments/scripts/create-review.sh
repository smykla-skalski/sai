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
#   event         — Review event: PENDING, COMMENT, APPROVE, or REQUEST_CHANGES
#                   PENDING omits the event field, creating a draft review.
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
#   # Pending (draft) review
#   ./create-review.sh owner repo 123 PENDING "WIP review" \
#     '[{"path":"main.go","line":10,"body":"Nit: unused import"}]'
#
# Dependencies: gh (GitHub CLI), python3 (for JSON encoding)
set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> <event> <body> [<comments_json>|-]" >&2
  echo "  event: PENDING, COMMENT, APPROVE, or REQUEST_CHANGES" >&2
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
  PENDING|COMMENT|APPROVE|REQUEST_CHANGES) ;;
  *)
    echo "Error: event must be PENDING, COMMENT, APPROVE, or REQUEST_CHANGES (got: $EVENT)" >&2
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
if [[ "$EVENT" != "APPROVE" && "$EVENT" != "PENDING" && -z "$BODY" && ("$COMMENTS_JSON" == "[]" || -z "$COMMENTS_JSON") ]]; then
  echo "Error: $EVENT review requires a body or comments (got neither)" >&2
  exit 1
fi

# Use python3 to safely construct the full JSON payload and count comments.
# Outputs two lines: first is the comment count, second is the JSON payload.
# This avoids a separate python invocation for counting.
PYTHON_SCRIPT='
import json, sys

body = sys.argv[1]
event = sys.argv[2]
comments_raw = sys.argv[3]

comments = json.loads(comments_raw) if comments_raw.strip() else []

# Ensure each comment has "side" defaulting to "RIGHT"
for c in comments:
    c.setdefault("side", "RIGHT")

payload = {"comments": comments}
# PENDING omits the event field so GitHub creates a draft review
if event != "PENDING":
    payload["event"] = event
if body:
    payload["body"] = body

print(len(comments))
print(json.dumps(payload))
'
BUILT=$(python3 -c "$PYTHON_SCRIPT" "$BODY" "$EVENT" "$COMMENTS_JSON")

# Split the two-line output: line 1 = comment count, line 2 = JSON payload
COMMENT_COUNT=$(head -n1 <<< "$BUILT")
[[ "${COMMENT_COUNT}" =~ ^[0-9]+$ ]] || {
  echo "Error: expected numeric comment count, got: $COMMENT_COUNT" >&2
  echo "Python output was:" >&2
  echo "$BUILT" >&2
  exit 1
}
PAYLOAD=$(tail -n1 <<< "$BUILT")
[[ "${PAYLOAD}" =~ ^\{.+[0-9] ]] || {
  echo "Error: expected JSON object payload, got: $PAYLOAD" >&2
  echo "Python output was:" >&2
  echo "$BUILT" >&2
  exit 1
}

# Submit the review. The API response does NOT include the comments array, so
# we build the jq filter with the known count from the payload we just sent.
# If the API call succeeds (set -euo pipefail), all comments were attached.
JQ_FILTER='{id: .id, html_url: .html_url, state: .state, comment_count: '"$COMMENT_COUNT"'}'
echo "$PAYLOAD" | gh api "repos/${OWNER}/${REPO}/pulls/${PR_NUMBER}/reviews" \
  --input - \
  --jq "$JQ_FILTER"
