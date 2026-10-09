# ship-it PR loop: open, wait, fix, merge

Resume the draft PR created in the publish step and take its current head to merge. Never poll in the foreground. Start one background waiter per PR that returns on a hosted-state change or the 30-minute deadline; read hosted status at most once per ten minutes.

Load the resolved release policy from the checkpoint and reconcile it with live GitHub policy before the first push and immediately before merge. A missing, stale, ambiguous or unsatisfied release policy blocks this loop with the exact required human action.

For GitHub work with claims enabled, verify the claim before a GitHub write and renew it only immediately before that write when due. Never renew on a timer. A conflicting, expired or unverifiable claim pauses remote writes until reconciliation succeeds.

## Before the first push

Do not rewrite history after validation begins. If the unpublished branch still needs a version-bump squash or any other rewrite, return to implementation, rewrite it with hooks enabled, recompute risk, and repeat every selected gate on the new `HEAD` before pushing or opening the PR.

## History rules after the first push

- Never force-push and never rebase.
- When the default branch moves or the PR conflicts, `git fetch origin` and `git merge origin/<default>` with a signed merge commit (`git merge -S`). In conflicts keep both sides' entries (changelogs, lists, version tables), then rerun the quality gates. A merge that leaves the reviewed files unchanged triggers no review; re-attest the merged revision under the convergence contract's default-branch-merge rule.

## Draft PR compatibility

The normal path already has a draft PR from [publish.md](publish.md). On resume from an older checkpoint without one, use that phase now: local checks are the only validation due before draft creation. Review and manual-test results are due before ready-for-review, and CI remains due before merge.

Create or update the PR body with `## Motivation`, `## Implementation information`, a changelog line (`> Changelog: type(scope): desc` or `> Changelog: skip`), gate verdicts for the current head, any unsettled review `question:` findings, each criterion recorded as `untested` by a `PASS (partial)` verdict under `## Untested criteria`, plus the source link:

| Source | PR title or body must contain |
| :-- | :-- |
| GitHub issue | With `pull-request-keyword`, `Closes #<number>` (`Closes owner/repo#<number>` cross-repository). With `manual-after-merge` or `unchanged`, use non-closing `Refs #<number>` instead. |
| Jira ticket | The Jira key, as a link to the ticket, in the body (and in the title when the repository's convention puts it there). Never `Closes` |
| Task description | No issue reference |

Follow the repository's own PR template or conventions when it documents them. Capture the PR number.

Read the created PR body back from GitHub. For `PASS (partial)`, verify that `## Untested criteria` contains every criterion and environmental blocker from the verdict before treating PR creation as complete. A missing or altered entry returns to PR-body correction; it does not invalidate the already-valid revision result.

Store the PR URL and its `headRefOid` in the durable checkpoint, set `phase` to `pr`, and keep `nextAction` aligned with the current wait, fix or merge action. Reconcile these fields with GitHub before every resumed PR loop.

## Request hosted reviewers

Run this section only when `hosted-review` is selected and the checkpoint's `hostedReviewDecision` is `serviceable`. Request every resolved reviewer whose request mode is `reviewer` or `team-reviewer`; reviewers with `automatic` are requested by repository policy. `not-required` satisfies the gate without a request. `fallback` uses the recorded fallback immediately. `blocked` is a hard stop. Never retry a request after quota, permission or unavailable-service made that reviewer unserviceable.

```bash
gh pr edit <n> --add-reviewer <request-target>
```

If the request mechanism itself fails, use the matching GitHub REST reviewer or team-reviewer field once. A quota, permission or unavailable-service response immediately changes `hostedReviewDecision` to the configured `fallback`; activate it without another request. When no fallback exists, record `blocked` with the named policy action and stop. Never leave an unserviceable reviewer pending or retry it. Do not request Copilot unless the resolved policy names it, and do not substitute an actor outside the configured fallback.

## Wait for hosted gates

Use one blocking background waiter that returns when checks, reviews, threads or the deadline change. Do not list agents between waits, and do not issue a status read more than once per ten minutes. In Sail, consume worker events instead of reading terminal panes. On each returned change inspect:

- `gh pr checks <n>` when `ci` is selected.
- Reviews and outstanding requests when `hosted-review` is selected: `gh api repos/<owner>/<repo>/pulls/<n>/reviews` plus the PR's requested reviewers and teams.
- Required unresolved, non-outdated review threads via GraphQL `repository.pullRequest.reviewThreads` (`isResolved`, `isOutdated`, comments), filtered by the resolved release policy.
- Every named policy or platform-required check on the exact PR head when `ci` is selected.

If selected CI fails, read [ci-triage.md](ci-triage.md) before retrieving logs. Deduplicate the revision/workflow/job/attempt, bound and redact failing sections, classify the failure with evidence, then route only code failures back to implementation. A code failure is an unresolved acceptance failure under the shared convergence policy and consumes its remaining fix/cycle budget. Never rerun CI without the repository policy or explicit approval required there.
If any selected reviewer or check remains unsatisfied for roughly 30 minutes, including a continuously requested reviewer or pending check, block with that exact requirement and the human action that satisfies it; never silently skip it.

## Ready gate

Mark the PR ready only when local checks, review, the single broad manual-test pass and required CI all pass for the same `headRefOid`. Every result with `requiredBy: ready` must pass. Update the body with those revision-bound verdicts first. A passing tester verdict is final: the coordinator never reruns or widens it. Keep the PR draft when any selected gate is missing, stale, failed or blocked.

Before diagnosing a failed hosted check, resolve and record a fresh CI-triage role. Its output identifies the matching route execution in the evidence record or checkpoint verdict.

Record every selected hosted gate against the current PR head in its evidence record when evidence is enabled, otherwise in checkpoint `gateVerdicts`, including provider, timestamp and job URL. A code-changing fix creates results pending for the new revision; recompute risk and validate it according to the shared convergence policy before returning to the PR loop. Never reset its counters for CI or hosted feedback.

## Address required reviewer feedback

When `hosted-review` is selected, handle every unresolved thread from a required reviewer:

- Valid, actionable: fix it, commit (signed, conventional), push, reply with what changed, resolve the thread.
- Questionable: use the codebase to decide; ask only when necessary.
- Invalid: reply with a concise rationale and resolve the thread.

Reply and resolve with REST or `gh`; when REST is rate-limited, use GraphQL:

```bash
gh api graphql -f query='mutation($id:ID!,$body:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}){comment{id}}}' -f id=<thread-id> -f body='<reply>'
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -f id=<thread-id>
```

Then return to waiting. After the single fix pass, turn later non-blocking suggestions into follow-up issues. Required feedback that cannot be resolved inside the remaining cycle or time budget is a hard stop.

## Merge

Merge only when all of these hold:

- With evidence enabled, the current evidence record is `complete`, every result with `requiredBy: merge` passed on its exact revision, and that revision equals both local `HEAD` and the PR `headRefOid`. With evidence disabled, the checkpoint's gate verdicts must record the same selected gates as passed for that exact revision and PR head.
- The current PR head has a passing result for every selected gate. Record its `headRefOid`; after a code-changing fix or default-branch merge, recompute risk and validate the new tip under the shared convergence policy. Check `headRefOid` again just before merge. The squash merge commit will have a different SHA; compare the PR head SHA.
- When `ci` is selected, every required CI check succeeded.
- When `hosted-review` is selected, every resolved reviewer requirement is satisfied for the current policy. A `review` accepts a submitted no-comment review; an `approval` requires an effective approval.
- When `hosted-review` is selected, every required reviewer's blocking comment is fixed or answered, and its thread is resolved.

Merge only through the checkpoint's resolved mechanism. For `bot-comment`, post its exact inert comment and wait for the bot; do not fall back to `gh pr merge`. For `github`, pass the resolved `merge|squash|rebase` strategy to `gh pr merge` and request remote-branch deletion only when policy says `delete`. If either mechanism reports that the default branch moved, merge `origin/<default>` (signed), push, rerun every selected gate and retry the same mechanism.

Never force-merge or use admin overrides. If branch protection requires extra approvals or admin action, report the exact required action and stop. Confirm the PR shows as merged before reporting. Delete a still-present remote branch only when resolved cleanup policy is `delete`; preserve it when policy says `preserve`.

After GitHub confirms the merge, record the PR head and merge commit but leave the checkpoint active until completion verifies the source issue and final repository state.
