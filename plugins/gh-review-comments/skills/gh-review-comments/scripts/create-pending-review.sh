#!/usr/bin/env bash
# create-pending-review.sh — Get or create the viewer's pending review on a PR via GraphQL.
#
# Usage:
#   ./create-pending-review.sh <owner> <repo> <pr_number> [<body>]
#
# Arguments:
#   owner      — Repository owner (e.g., "smykla-skalski")
#   repo       — Repository name (e.g., "sai")
#   pr_number  — Pull request number
#   body       — Review body for a newly created review (optional, ignored when one exists)
#
# GitHub allows one pending review per user per PR. If the viewer already has one,
# its id is returned and nothing is created, so the script is safe to re-run.
# Add comments to the returned review with add-review-comment.sh.
#
# Output: JSON with review_id (PRR_... node id), url, and created (true if new).
#
# Dependencies: gh (GitHub CLI)
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <owner> <repo> <pr_number> [<body>]" >&2
  exit 1
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"
BODY="${4:-}"

LOOKUP=$(gh api graphql \
  -F owner="$OWNER" -F repo="$REPO" -F number="$PR_NUMBER" \
  -f query='
    query($owner: String!, $repo: String!, $number: Int!) {
      viewer { login }
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          id
          reviews(states: [PENDING], first: 10) {
            nodes { id url author { login } }
          }
        }
      }
    }
  ' \
  --jq '.data as $d
    | ($d.repository.pullRequest.reviews.nodes
        | map(select(.author.login == $d.viewer.login)) | first) as $existing
    | {pr_id: $d.repository.pullRequest.id, review_id: ($existing.id // ""), url: ($existing.url // "")}')

EXISTING_ID=$(jq -r '.review_id' <<< "$LOOKUP")
if [[ -n "$EXISTING_ID" ]]; then
  jq -c '{review_id, url, created: false}' <<< "$LOOKUP"
  exit 0
fi

PR_ID=$(jq -r '.pr_id' <<< "$LOOKUP")

gh api graphql \
  -f pr="$PR_ID" -f body="$BODY" \
  -f query='
    mutation($pr: ID!, $body: String) {
      addPullRequestReview(input: {pullRequestId: $pr, body: $body}) {
        pullRequestReview { id url }
      }
    }
  ' \
  --jq '.data.addPullRequestReview.pullRequestReview | {review_id: .id, url, created: true}'
