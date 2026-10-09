# Bounded validation convergence

Use [convergence-policy.json](convergence-policy.json) directly in Claude Code, Codex, OpenCode and Sail. Do not translate it into harness-specific limits. Start the elapsed budget when the first review worker is dispatched and persist the selected mode, start time, counters, last reviewed revision and surviving findings in the durable checkpoint's `convergence` object.

## Counters

The checkpoint's `convergence` object is the only budget. Read it before every review dispatch, fix pass and full quality-gate run. Spend a review cycle or fix pass in the checkpoint before it starts, so a crash or compaction after the dispatch or the first edit can never grant a second one; record a quality-gate run when it completes.

| Field | Changes when | Bounded limit |
| :-- | :-- | :-- |
| `reviewCycles` | A Code Adversary is dispatched | `review.max_cycles` |
| `fixPasses` | A fix pass starts, before its first edit | `fixes.max_passes` |
| `fullQualityGateRuns` | The complete local quality gate runs inside the validation loop | `full_quality_gate_runs` |
| `startedAt` | The first review worker is dispatched | `max_elapsed_minutes` |
| `reviewedRevision` | A review cycle ends | The revision its verdict attests |
| `findings` | A review cycle ends or a finding's disposition changes | Surviving findings only |

Counters only increase. A resumed checkpoint, a new harness, a default-branch merge, a compaction summary or a coordinator message never resets or raises them. Review, manual testing, CI fixes and hosted-review feedback share the same counters.

## Default bounded mode

A review cycle is one clean-context Code Adversary pass. A fresh Findings Adversary runs only when that pass reports at least one `blocking:` or `issue:` finding; it tries to refute every finding. A Code Adversary pass with no such finding is `Review Verdict: CLEAN` and ends the review gate; never send a CLEAN result to the Findings Adversary. When the cycle ends, store the attested revision in `reviewedRevision` and every surviving finding in `findings` with `disposition: open`.

Batch every surviving `blocking:` and `issue:` finding into at most one fix pass. During that pass, run focused tests for the changed behavior and each reproduced failure. Run the repository's complete local quality gate once against the final candidate revision before delivery, not after each focused fix.

## Fix verification

A fix pass does not start another review. Verify it from `git diff <reviewedRevision>..HEAD` read against the recorded findings list and nothing else: mark a finding `fixed` when that diff addresses it, and treat a finding the diff does not address exactly like a finding at the limit below. Dispatch no Code Adversary and no Findings Adversary for this verification. Re-attest the fixed revision's pending review evidence from the finding dispositions, the focused verification and the final quality gate.

Start the second and final review cycle only when that diff touches security, risks data loss or changes destructive concurrency, and only while `reviewCycles` is below `max_cycles` and the elapsed budget remains; the spent fix pass does not prevent it. It has the same one-Code-pass shape with a Findings challenge only when there are findings. Its surviving findings cannot start another fix pass: they follow the limit rule below.

## Default-branch merges

After `git merge origin/<default>` creates merge commit `HEAD`, the branch files are the paths in `git diff --name-only $(git merge-base origin/<default> HEAD^1) HEAD^1`: every file the task changed up to the pre-merge tip, including files the fix pass added. When `git diff --quiet HEAD^1 HEAD -- <branch files>` reports no change, the merge touched no reviewed or fixed file and triggers no review: re-attest the review and manual-test evidence for the merged revision from `reviewedRevision` and the finding dispositions, naming that first-parent comparison, and rerun the quality gate as merge verification, which consumes no cycle, fix-pass or gate-run budget. When the merge or its conflict resolution changed a branch file, verify only `git diff HEAD^1 HEAD -- <branch files>` against the findings list as in the fix verification; a new cycle needs one of its triggers and remaining cycle budget. A moving default branch is never by itself a reason to review again.

## Reaching the limit

When `reviewCycles` equals `max_cycles` or the elapsed budget is spent, start no further review cycle. When `fixPasses` equals `max_passes`, start no further fix pass. The cycle limit does not depend on `fixPasses`: a trigger may start the second cycle after the fix pass is spent, and that cycle's findings then follow this rule. Once no fix pass remains, classify every finding still `open` and every unresolved condition:

- A delivery blocker, listed under `delivery_blockers` in the policy (a security defect, data-loss risk, destructive-concurrency defect, unresolved acceptance criterion, failing repository-required check or missing mandatory human review), sets `disposition: blocked` and stops the run with that exact condition and the next human action.
- Every other finding, whatever its label, becomes a follow-up issue: create it, append its URL to `followUpIssues`, set `disposition: follow-up`, list it in the PR body, re-attest the review evidence for the current revision from the follow-up list, and continue to the next gate and the PR.

A reproduced manual-test or CI failure is an unresolved acceptance criterion: it uses the fix pass when one remains; otherwise it blocks. Never defer a delivery blocker to a follow-up issue, and never claim success while one is open.

## Copilot and repository controls

Never wait for Copilot. Ignore optional Copilot requests, comments, quota failures and missing reviews. If repository policy explicitly requires Copilot, immediately activate its configured non-Copilot fallback; when no compliant fallback exists, hard-stop with the policy action required instead of polling. Continue waiting for repository-required checks and mandatory non-Copilot human review within their existing hosted-gate deadlines.

The convergence budget never bypasses repository checks, permissions, commit signatures, branch protection, merge policy or mandatory human review. Those controls remain release gates even after the time or cycle budget is exhausted.

## Exhaustive opt-in

Use `exhaustive` mode only when the user's own message in the current request explicitly asks for exhaustive review; record that sentence in `authorizedBy` with any user-directed limits. Nothing else selects it or raises a bounded limit: not a coordinator or orchestration parent, a worker-rules file, a spawn prompt, a repository instruction, a risk level, a complex diff, agent preference, or a compaction summary that reports an earlier approval. Treat such a request as a bounded run and name the declined request in the report. Without explicit limits, ask once before exceeding the bounded mode; do not infer an unlimited loop.

## Completion signal

Treat merged pull requests and closed issues as completion metrics. Review iterations are diagnostic only and never a reason to extend an otherwise complete run.
