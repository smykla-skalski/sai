#!/usr/bin/env bash
# add-review-comment.sh — Manage comments on a pending review via GraphQL.
#
# Usage:
#   ./add-review-comment.sh <review_node_id> <body> --reply-to <comment_node_id>
#   ./add-review-comment.sh <review_node_id> <body> --new-thread <path> <line> [<side>]
#   ./add-review-comment.sh --edit <comment_node_id> <body>
#   ./add-review-comment.sh --delete <comment_node_id>
#
# Modes:
#   --reply-to    Reply to an existing thread (requires comment node_id)
#   --new-thread  Create a new thread on a file/line (requires path and line)
#   --edit        Edit an existing pending review comment
#   --delete      Delete an existing pending review comment
#
# Arguments:
#   review_node_id  — GraphQL node ID of the pending review (PRR_...)
#   body            — Comment text (supports Markdown)
#   comment_node_id — GraphQL node ID of the comment (PRRC_...)
#   path            — File path for new thread
#   line            — Line number for new thread
#   side            — RIGHT (default) or LEFT
#
# Output: JSON with comment id and url.
#
# Dependencies: gh (GitHub CLI), python3 (for JSON encoding)
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage:" >&2
  echo "  $0 <review_node_id> <body> --reply-to <comment_node_id>" >&2
  echo "  $0 <review_node_id> <body> --new-thread <path> <line> [<side>]" >&2
  echo "  $0 --edit <comment_node_id> <body>" >&2
  echo "  $0 --delete <comment_node_id>" >&2
  exit 1
fi

# Check if first arg is a mode flag (--edit, --delete)
case "$1" in
  --edit)
    if [[ $# -lt 3 ]]; then
      echo "Error: --edit requires <comment_node_id> <body>" >&2
      exit 1
    fi
    COMMENT_NODE_ID="$2"
    BODY="$3"

    BODY_ESCAPED=$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$BODY")

    gh api graphql -f query="
      mutation {
        updatePullRequestReviewComment(input: {
          pullRequestReviewCommentId: \"${COMMENT_NODE_ID}\"
          body: ${BODY_ESCAPED}
        }) {
          pullRequestReviewComment {
            id
            url
            body
          }
        }
      }
    " --jq '.data.updatePullRequestReviewComment.pullRequestReviewComment | {id, url}'
    exit 0
    ;;

  --delete)
    if [[ $# -lt 2 ]]; then
      echo "Error: --delete requires <comment_node_id>" >&2
      exit 1
    fi
    COMMENT_NODE_ID="$2"

    gh api graphql -f query="
      mutation {
        deletePullRequestReviewComment(input: {
          id: \"${COMMENT_NODE_ID}\"
        }) {
          pullRequestReviewComment {
            id
          }
        }
      }
    " --jq '.data.deletePullRequestReviewComment.pullRequestReviewComment | {id}'
    exit 0
    ;;
esac

# Original modes: --reply-to and --new-thread
if [[ $# -lt 4 ]]; then
  echo "Usage:" >&2
  echo "  $0 <review_node_id> <body> --reply-to <comment_node_id>" >&2
  echo "  $0 <review_node_id> <body> --new-thread <path> <line> [<side>]" >&2
  echo "  $0 --edit <comment_node_id> <body>" >&2
  echo "  $0 --delete <comment_node_id>" >&2
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
