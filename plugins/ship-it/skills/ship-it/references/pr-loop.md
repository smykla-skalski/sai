# ship-it PR loop: open, wait, fix, merge

From a revision with every selected PR-due gate passed to a merged PR. Never end the turn while a selected hosted gate is pending: keep polling until the PR is merged or a hard stop is reached.

For GitHub work, verify the issue claim before the first push and renew it at least every 10 minutes throughout the loop. Renew before each GitHub write when due. A conflicting, expired or unverifiable claim pauses pushes, PR changes, review replies and merge until reconciliation succeeds.

## Before the first push

Do not rewrite history after validation begins. If the unpublished branch still needs a version-bump squash or any other rewrite, return to implementation, rewrite it with hooks enabled, recompute risk, and repeat every selected gate on the new `HEAD` before pushing or opening the PR.

## History rules after the first push

- Never force-push and never rebase.
- When the default branch moves or the PR conflicts, `git fetch origin` and `git merge origin/<default>` with a signed merge commit (`git merge -S`). In conflicts keep both sides' entries (changelogs, lists, version tables), then rerun the quality gates.

## Open the PR

Before pushing, validate that every result with `requiredBy: pr` passed in the current revision's evidence record. Missing, pending, failed, blocked or stale due evidence stops PR creation. CI results remain pending with `requiredBy: merge` until the PR exists.

Push the branch and create a PR against the default branch. Title: the conventional lead-commit title. Body: `## Motivation`, `## Implementation information`, a changelog line (`> Changelog: type(scope): desc` or `> Changelog: skip`), any unsettled review `question:` findings, plus the source link:

| Source | PR title or body must contain |
| :-- | :-- |
| GitHub issue | `Closes #<number>` (`Closes owner/repo#<number>` when the issue lives in another repository) |
| Jira ticket | The Jira key, as a link to the ticket, in the body (and in the title when the repository's convention puts it there). Never `Closes` |
| Task description | No issue reference |

Follow the repository's own PR template or conventions when it documents them. Capture the PR number.

Store the PR URL and its `headRefOid` in the durable checkpoint, set `phase` to `pr`, and keep `nextAction` aligned with the current wait, fix or merge action. Reconcile these fields with GitHub before every resumed PR loop.

## Request Copilot

Run this section only when `copilot-review` is selected. Otherwise record no hosted-review evidence and continue to CI.

```bash
gh pr edit <n> --add-reviewer copilot-pull-request-reviewer
```

If that fails, fall back to the REST API:

```bash
gh api -X POST repos/<owner>/<repo>/pulls/<n>/requested_reviewers \
  -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

A failure to request Copilot never fails PR creation; note it and keep waiting, since many repositories request Copilot automatically.

## Wait for hosted gates

Poll every 5–10 minutes; do not busy-loop. On each poll inspect:

- `gh pr checks <n>` when `ci` is selected.
- Reviews when `copilot-review` is selected: `gh api repos/<owner>/<repo>/pulls/<n>/reviews` (Copilot's author login contains `copilot`).
- Required unresolved, non-outdated review threads via GraphQL `repository.pullRequest.reviewThreads` (`isResolved`, `isOutdated`, comments).

If selected CI fails, read the failed run logs (`gh run view <id> --log-failed`), fix, push, and keep waiting. If selected Copilot review has neither completed nor remained requested after roughly 30 minutes, stop and ask whether to authorize a policy override; never silently skip it.

Record every selected hosted gate against the current PR head in its evidence record, including provider, timestamp and job URL. A code-changing fix creates a new revision record with every selected result pending; recompute risk and rerun every selected gate before returning to the PR loop.

## Address Copilot feedback

When `copilot-review` is selected, handle every unresolved Copilot thread:

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

- The current evidence record is `complete`; every result with `requiredBy: merge` passed on its exact revision; and that revision equals both local `HEAD` and the PR `headRefOid`.
- The current PR head has passing evidence for every selected gate. Record its `headRefOid`; after every code-changing fix or default-branch merge, recompute risk and rerun all selected gates on the new committed tip. Check `headRefOid` again just before merge and restart the gates if it changed. The squash merge commit will have a different SHA; compare the PR head SHA.
- When `ci` is selected, every required CI check succeeded.
- When `copilot-review` is selected, Copilot submitted at least one review (a no-comments review counts). Do not wait for Copilot to re-review fix commits.
- When `copilot-review` is selected, every Copilot comment is fixed or answered, and its thread is resolved.

How to merge, in order:

1. The repository's documented convention (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`). If it merges through a bot comment, post exactly that comment instead of merging yourself. Example: smykla-skalski repositories merge when a PR comment with the exact body `squash` is posted (`gh pr comment <n> --body squash`); the smyklot bot then merges. If the bot bounces the merge because the default branch moved, merge `origin/<default>` (signed), push, wait for CI again, and post the comment again.
2. Otherwise `gh pr merge <n> --squash --delete-branch`.

Never force-merge or use admin overrides. If branch protection requires extra approvals or admin action, report the state and stop. Confirm the PR shows as merged before reporting. If the remote branch still exists after the merge, delete it with `git push origin --delete <branch>`.

After GitHub confirms the merge, record the PR head and merge commit but leave the checkpoint active until completion verifies the source issue and final repository state.
