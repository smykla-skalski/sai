#!/usr/bin/env bash
# add-review-comment.sh — Add a comment to an existing pending review via GraphQL.
#
# Usage:
#   ./add-review-comment.sh <review_node_id> <body> --reply-to <comment_node_id>
#   ./add-review-comment.sh <review_node_id> <body> --new-thread <path> <line> [<side>]
#
# Modes:
#   --reply-to    Reply to an existing thread (requires comment node_id)
#   --new-thread  Create a new thread on a file/line (requires path and line)
#
# Arguments:
#   review_node_id  — GraphQL node ID of the pending review (PRR_...)
#   body            — Comment text (supports Markdown)
#   comment_node_id — GraphQL node ID of the comment to reply to (PRRC_...)
#   path            — File path for new thread
#   line            — Line number for new thread
#   side            — RIGHT (default) or LEFT
#
# Output: JSON with comment id and url.
#
# Dependencies: gh (GitHub CLI), python3 (for JSON encoding)
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage:" >&2
  echo "  $0 <review_node_id> <body> --reply-to <comment_node_id>" >&2
  echo "  $0 <review_node_id> <body> --new-thread <path> <line> [<side>]" >&2
  exit 1
fi

REVIEW_NODE_ID="$1"
BODY="$2"
MODE="$3"

case "$MODE" in
  --reply-to)
    if [[ $# -lt 4 ]]; then
      echo "Error: --reply-to requires <comment_node_id>" >&2
      exit 1
    fi
    COMMENT_NODE_ID="$4"

    BODY_ESCAPED=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$BODY")

    gh api graphql -f query="
      mutation {
        addPullRequestReviewComment(input: {
          pullRequestReviewId: \"${REVIEW_NODE_ID}\"
          body: ${BODY_ESCAPED}
          inReplyTo: \"${COMMENT_NODE_ID}\"
        }) {
          comment {
            id
            url
          }
        }
      }
    " --jq '.data.addPullRequestReviewComment.comment | {id, url}'
    ;;

  --new-thread)
    if [[ $# -lt 5 ]]; then
      echo "Error: --new-thread requires <path> <line> [<side>]" >&2
      exit 1
    fi
    PATH_ARG="$4"
    LINE="$5"
    SIDE="${6:-RIGHT}"

    BODY_ESCAPED=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$BODY")

    gh api graphql -f query="
      mutation {
        addPullRequestReviewThread(input: {
          pullRequestReviewId: \"${REVIEW_NODE_ID}\"
          path: \"${PATH_ARG}\"
          line: ${LINE}
          side: ${SIDE}
          body: ${BODY_ESCAPED}
        }) {
          thread {
            id
            comments(first: 1) {
              nodes {
                id
                url
              }
            }
          }
        }
      }
    " --jq '.data.addPullRequestReviewThread.thread | {thread_id: .id, comment_id: .comments.nodes[0].id, url: .comments.nodes[0].url}'
    ;;

  *)
    echo "Error: mode must be --reply-to or --new-thread (got: $MODE)" >&2
    exit 1
    ;;
esac
