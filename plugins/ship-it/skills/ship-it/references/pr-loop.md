# ship-it PR loop: open, wait, fix, merge

From a reviewed and tested branch to a merged PR. Never end the turn while CI or Copilot is pending: keep polling (background waits are fine) until the PR is merged or a hard stop is reached.

## Before the first push

Do not rewrite history after review begins. If the unpublished branch still needs a version-bump squash or any other rewrite, return to implementation, rewrite it with hooks enabled, run repository gates, and repeat adversarial review and testing on the new `HEAD` before pushing or opening the PR.

## History rules after the first push

- Never force-push and never rebase.
- When the default branch moves or the PR conflicts, `git fetch origin` and `git merge origin/<default>` with a signed merge commit (`git merge -S`). In conflicts keep both sides' entries (changelogs, lists, version tables), then rerun the quality gates.

## Open the PR

Push the branch and create a PR against the default branch. Title: the conventional lead-commit title. Body: `## Motivation`, `## Implementation information`, a changelog line (`> Changelog: type(scope): desc` or `> Changelog: skip`), any unsettled review `question:` findings, plus the source link:

| Source | PR title or body must contain |
| :-- | :-- |
| GitHub issue | `Closes #<number>` (`Closes owner/repo#<number>` when the issue lives in another repository) |
| Jira ticket | The Jira key, as a link to the ticket, in the body (and in the title when the repository's convention puts it there). Never `Closes` |
| Task description | No issue reference |

Follow the repository's own PR template or conventions when it documents them. Capture the PR number.

Store the PR URL and its `headRefOid` in the durable checkpoint, set `phase` to `pr`, and keep `nextAction` aligned with the current wait, fix or merge action. Reconcile these fields with GitHub before every resumed PR loop.

## Request Copilot

```bash
gh pr edit <n> --add-reviewer copilot-pull-request-reviewer
```

If that fails, fall back to the REST API:

```bash
gh api -X POST repos/<owner>/<repo>/pulls/<n>/requested_reviewers \
  -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

A failure to request Copilot never fails PR creation; note it and keep waiting, since many repositories request Copilot automatically.

## Wait for CI and Copilot

Poll every 5–10 minutes; do not busy-loop. On each poll inspect:

- `gh pr checks <n>`.
- Reviews: `gh api repos/<owner>/<repo>/pulls/<n>/reviews` (Copilot's author login contains `copilot`).
- Unresolved, non-outdated review threads, via GraphQL `repository.pullRequest.reviewThreads` (`isResolved`, `isOutdated`, comments).

If CI fails, read the failed run logs (`gh run view <id> --log-failed`), fix, push, and keep waiting. If after roughly 30 minutes Copilot has neither reviewed nor has a pending review request, stop and ask whether to merge without it; never silently skip the Copilot wait.

## Address Copilot feedback

For every unresolved Copilot thread:

- Valid, actionable: fix it, commit (signed, conventional), push, reply with what changed, resolve the thread.
- Questionable: use the codebase to decide; ask only when necessary.
- Invalid: reply with a concise rationale and resolve the thread.

Reply and resolve with REST or `gh`; when REST is rate-limited, use GraphQL:

```bash
gh api graphql -f query='mutation($id:ID!,$body:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}){comment{id}}}' -f id=<thread-id> -f body='<reply>'
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -f id=<thread-id>
```

Then return to waiting. Stop for a human decision if the same thread loops more than three times.

## Merge

Merge only when all of these hold:

- The current PR head has `Review Verdict: CLEAN` and `Test Verdict: PASS`. Record its `headRefOid`; after every code-changing CI/Copilot fix or merge from the default branch, rerun both gates on the new committed tip. Check `headRefOid` again just before merge and restart the gates if it changed. The squash merge commit will have a different SHA; compare the PR head SHA.
- Every CI check succeeded.
- Copilot submitted at least one review (a no-comments review counts). Do not wait for Copilot to re-review fix commits.
- Every Copilot comment is fixed or answered, and its thread is resolved.

How to merge, in order:

1. The repository's documented convention (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`). If it merges through a bot comment, post exactly that comment instead of merging yourself. Example: smykla-skalski repositories merge when a PR comment with the exact body `squash` is posted (`gh pr comment <n> --body squash`); the smyklot bot then merges. If the bot bounces the merge because the default branch moved, merge `origin/<default>` (signed), push, wait for CI again, and post the comment again.
2. Otherwise `gh pr merge <n> --squash --delete-branch`.

Never force-merge or use admin overrides. If branch protection requires extra approvals or admin action, report the state and stop. Confirm the PR shows as merged before reporting. If the remote branch still exists after the merge, delete it with `git push origin --delete <branch>`.

After GitHub confirms the merge, record the PR head and merge commit but leave the checkpoint active until completion verifies the source issue and final repository state.
