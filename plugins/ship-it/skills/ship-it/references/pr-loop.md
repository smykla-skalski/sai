# ship-it PR loop: open, wait, fix, merge

Apply [handoff.md](handoff.md) before first entry (`before-pr-loop`).

Resume open PRs at their reconciled head; merged PRs go to completion. Other states stop under checkpoint recovery. Apply [worker-events.md](worker-events.md) with one waiter keyed by PR and head SHA and a 30-minute deadline.

Reconcile the resolved release policy from the checkpoint with live GitHub policy before the first push and merge. Missing, stale, ambiguous or unsatisfied policy blocks the loop; name the required human action.

For GitHub work with claims enabled, verify the claim before a GitHub write and renew it only immediately before that write when due. Never renew on a timer. A conflicting, expired or unverifiable claim pauses remote writes until reconciliation succeeds.

## Before the first push

Do not rewrite history after validation begins. If the unpublished branch still needs a version-bump squash or any other rewrite, return to implementation, rewrite it with hooks enabled, recompute risk, and repeat every selected gate on the new `HEAD` before pushing or opening the PR.

## History rules after the first push

- Never force-push and never rebase.
- On a moved default branch or conflict, `git fetch origin` and `git merge origin/<default>` with a signed merge commit (`git merge -S`). Preserve both sides' entries. Assess local manifests under [validation-reuse.md](validation-reuse.md); carry verified results and verify affected criteria under the convergence contract.

## Draft PR compatibility

Legacy checkpoints without a PR use [publish.md](publish.md) after local checks; review/test remain due before ready and CI before merge.

Create or update the PR body with `## Motivation`, `## Implementation information`, a changelog line (`> Changelog: type(scope): desc` or `> Changelog: skip`), gate verdicts for the current head, any unsettled review `question:` findings, each criterion recorded as `untested` by a `PASS (partial)` verdict under `## Untested criteria`, plus the source link:

| Source | PR title or body must contain |
| :-- | :-- |
| GitHub issue | With `pull-request-keyword`, `Closes #<number>` (`Closes owner/repo#<number>` cross-repository). With `manual-after-merge` or `unchanged`, use non-closing `Refs #<number>` instead. |
| Jira ticket | The Jira key, as a link to the ticket, in the body (and in the title when the repository's convention puts it there). Never `Closes` |
| Task description | No issue reference |

Follow the repository's own PR template or conventions when it documents them.

Read the created PR body back from GitHub. For `PASS (partial)`, verify that `## Untested criteria` contains every criterion and environmental blocker from the verdict before treating PR creation as complete. A missing or altered entry returns to PR-body correction; it does not invalidate the already-valid revision result.

Store the PR URL and its `headRefOid` in the durable checkpoint, set `phase` to `pr`, and keep `nextAction` aligned with the current wait, fix or merge action. Reconcile these fields with GitHub before every resumed PR loop.

## Request hosted reviewers

When `hosted-review` is selected, read the [request procedure](release.md#request-hosted-reviewers) before requests. Check `scripts/copilot_quota.py status` before Copilot; refusal activates fallback or stops. Never retry a request after a service refusal: it immediately changes `hostedReviewDecision` to the configured fallback or blocked. A blocked decision stops delivery. Do not request Copilot unless policy names it.

## Wait for hosted gates

Before counting reviews, apply [Copilot quota rules](release.md#copilot-quota-refusals).

Run one blocking process per PR/head; it uses Python and `gh`, paginates checks/reviews/threads and emits one terminal JSON:

```bash
python3 <skill-dir>/scripts/hosted_wait.py <owner>/<repo> <n> --head <sha> --timeout 1800 --check '<policy-check>' --reviewer '<login>:review' --thread-author '<login>'
```

Use `--help` for flags. Repeat policy checks and required reviewers (`review|approval`); omit reviewers without hosted review. Omit thread authors to include all unresolved non-outdated threads. Platform gates always bind. Run under one background/event waiter if foreground limits are short; never poll or restart.

Only `satisfied` exits 0. Failures, head changes, closure, merge and deadline exit 1; API/input errors exit 2. Results name failed or pending requirements and observed transitions. Reconcile merged delivery or a changed head before continuing; resolve existing comments even when external review was waived.

If selected CI fails, read [ci-triage.md](ci-triage.md) before retrieving logs. Deduplicate the revision/workflow/job/attempt, bound and redact failing sections, classify the failure with evidence, then route only code failures back to implementation. A code failure is an unresolved acceptance failure under the shared convergence policy and consumes its remaining fix budget; after an internal limit, triage focused recovery under active scoped authorization. Never rerun CI without the repository policy or explicit approval required there.
If any selected reviewer or check remains unsatisfied for roughly 30 minutes, including a continuously requested reviewer or pending check, block with that exact requirement and the human action that satisfies it; never silently skip it.

## Ready gate

Mark the PR ready only when local checks, review, the single broad manual-test pass and required CI all pass for the same `headRefOid`. Every result with `requiredBy: ready` must pass. Update the body with those revision-bound verdicts first. A passing tester verdict is final: the coordinator never reruns or widens it. Keep the PR draft when any selected gate is missing, stale, failed or blocked.

Before diagnosing a failed hosted check, resolve and record a fresh CI-triage role. Its output identifies the matching route execution in the evidence record or checkpoint verdict.

Record selected hosted results in enabled evidence or checkpoint `gateVerdicts`, bound to PR head, provider, timestamp and job URL. Source changes require a helper validity decision for local results and live policy reconciliation for hosted results; recompute risk and revalidate affected inputs. Never reset shared counters.

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

Then return to waiting. After the single fix pass, turn later non-blocking suggestions into follow-up issues. Required feedback that survives an internal limit enters focused acceptance triage under [authorization.md](authorization.md). Existing scoped task authority covers necessary corrections; explicit user limits and mandatory controls still bind. Stop for an unresolved blocker, not to ask for the same permission again.

## Merge

Merge only when all of these hold:

- With evidence enabled, the current evidence record is `complete`, every result with `requiredBy: merge` passed on its exact revision, and that revision equals both local `HEAD` and the PR `headRefOid`. With evidence disabled, the checkpoint's gate verdicts must record the same selected gates as passed for that exact revision and PR head.
- The current PR head has a passing result for every selected gate. Record its `headRefOid`; after a code-changing fix or default-branch merge, recompute risk and validate the new tip under the shared convergence policy. Check `headRefOid` again just before merge. The squash merge commit will have a different SHA; compare the PR head SHA.
- When `ci` is selected, every required CI check succeeded.
- When `hosted-review` is selected, every resolved reviewer requirement is satisfied for the current policy. A `review` accepts a submitted no-comment review; an `approval` requires an effective approval.
- When `hosted-review` is selected, every required reviewer's blocking comment is fixed or answered, and its thread is resolved.

Merge only through the checkpoint's resolved mechanism. For `bot-comment`, post its exact inert comment and wait for the bot; do not fall back to `gh pr merge`. For `github`, pass the resolved `merge|squash|rebase` strategy to `gh pr merge` and request remote-branch deletion only when policy says `delete`. If either mechanism reports that the default branch moved, merge `origin/<default>` (signed), assess local input validity, push, satisfy the selected local gates and current-head hosted requirements, then retry the same mechanism.

Never force-merge or use admin overrides. If branch protection requires extra approvals or admin action, report the exact required action and stop. Confirm the PR shows as merged before reporting. Delete a still-present remote branch only when resolved cleanup policy is `delete`; preserve it when policy says `preserve`.

After GitHub confirms the merge, record the PR head and merge commit but leave the checkpoint active until completion verifies the source issue and final repository state.
