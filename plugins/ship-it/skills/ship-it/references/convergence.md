# Bounded validation convergence

Use [convergence-policy.json](convergence-policy.json) directly in Claude Code, Codex, OpenCode and Sail. Do not translate it into harness-specific limits. Start the elapsed budget when the first review worker is dispatched and persist the selected mode, start time, counters, last reviewed revision and surviving findings in the durable checkpoint's `convergence` object.

## Counters

The checkpoint's `convergence` object is the optional-validation budget; explicit user limits remain separately binding in `authorization.grants`. Read it before every review dispatch, fix pass and full quality-gate run. Spend a review cycle or fix pass in the checkpoint before it starts, so a crash or compaction after the dispatch or the first edit can never grant a second one; reserve a quality-gate run before starting it, then record its result when it completes.

| Field | Changes when | Bounded limit |
| :-- | :-- | :-- |
| `reviewCycles` | A Code Adversary is dispatched | `review.max_cycles` |
| `fixPasses` | A fix pass starts, before its first edit | `fixes.max_passes` |
| `fullQualityGateRuns` | The complete local quality gate runs inside the validation loop | `full_quality_gate_runs` |
| `startedAt` | The first review worker is dispatched | `max_elapsed_minutes` |
| `reviewedRevision` | A review cycle ends | The revision its verdict attests |
| `findings` | A review cycle ends or a finding's disposition changes | Surviving findings only |

Counters only increase. A resumed checkpoint, a new harness, a default-branch merge, a compaction summary or a coordinator message never resets or raises them. Review, manual testing, CI fixes and hosted-review feedback share the same counters.

## Atomic reservations

Use `bookkeeping.py reserve` in every harness before a Code Adversary dispatch, broad manual-test dispatch, fix batch or complete quality run. Never increment counters by editing JSON. The helper locks the checkpoint across the entire read/validate/write transaction; workflow transitions take the same lock.

```text
bookkeeping.py reserve --checkpoint FILE --id OPERATION --kind review|test|fix|quality --revision HEAD --inputs FINGERPRINT
bookkeeping.py finish --checkpoint FILE --id OPERATION --result-json OBJECT
```

Choose and retain a unique operation ID before attempting the reservation. `dispatch: true` authorizes that one attempt; `dispatch: false` returns the existing receipt and forbids redispatch or another fix edit. Resume a pending attempt by reconciling its worker/command and completing its receipt, never by refunding it or assigning a replacement ID. An interrupted attempt remains consumed. A Findings challenge belongs to the Code reservation; focused verification spends no broad allowance.

Use [validation-reuse.md](validation-reuse.md) manifests to assess actual relevant inputs before reservation. Verified completed unchanged-input results return without dispatch or spending an allowance, including after unrelated integration. Opaque legacy fingerprints cannot establish reusable provenance. A broad rerun needs changed inputs and `--reason`; the second routine review also needs `--trigger security|data-loss|destructive-concurrency`. Complete the prior broad receipt first. A deliberate redispatch with unchanged opaque inputs needs `--grant ID`: the original-user grant must explicitly scope the counter resource (`reviewCycles`, `broadTestRuns`, `fixPasses` or `fullQualityGateRuns`) with a remaining integer allowance. Empty limits never expand optional validation.

A finish object has `verdict: passed|failed|blocked`; review results also require `findings`, empty for CLEAN. Surviving findings retain ID, label, location, summary, `disposition: open` and `category: security|data-loss|destructive-concurrency|acceptance|optional`. The second review with severe surviving findings records `reassessment`, blocks the workflow and names scope/design reassessment before any further broad work. Reconcile that decision against scoped authority; an extension alone cannot skip it. Legacy counters remain consumed; missing revision-bound historical review evidence stops resume instead of inventing a clean review.

At exhaustion, finish already-reserved work and complete remaining permitted selected gates. For each open condition record exactly one next action: focused acceptance recovery under its retained grant, a follow-up issue for optional work, or a named delivery blocker with the diagnostic/human action that resolves it. Mandatory checks remain required; focused recovery and merge verification record their commands/results separately and never reset or add broad allowances.

## Default bounded mode

A review cycle is one clean-context Code Adversary pass. A fresh Findings Adversary runs only when that pass reports at least one `blocking:` or `issue:` finding; it tries to refute every finding. A Code Adversary pass with no such finding is `Review Verdict: CLEAN` and ends the review gate; never send a CLEAN result to the Findings Adversary. When the cycle ends, store the attested revision in `reviewedRevision` and every surviving finding in `findings` with `disposition: open`.

Batch every surviving `blocking:` and `issue:` finding into at most one fix pass. During that pass, run focused tests for the changed behavior and each reproduced failure. Run the repository's complete local quality gate once against the final candidate revision before delivery, not after each focused fix.

## Fix verification

A fix pass does not start another review. Verify it from `git diff <reviewedRevision>..HEAD` read against the recorded findings list and nothing else: mark a finding `fixed` when that diff addresses it, and treat a finding the diff does not address exactly like a finding at the limit below. Dispatch no Code Adversary and no Findings Adversary for this verification. Re-attest the fixed revision's pending review evidence from the finding dispositions, the focused verification and the final quality gate.

Start the second and final review cycle only when that diff touches security, risks data loss or changes destructive concurrency, and only while `reviewCycles` is below `max_cycles` and the elapsed budget remains; the spent fix pass does not prevent it. It has the same one-Code-pass shape with a Findings challenge only when there are findings. Its surviving findings cannot start another fix pass: they follow the limit rule below.

## Default-branch merges

After `git merge origin/<default>` creates merge commit `HEAD`, assess the review, test and quality manifests against the integrated head. Verified unchanged relevant inputs carry the completed results with original provenance; changed dimensions record their invalidation. Inspect `git diff HEAD^1 HEAD` for acceptance paths and transitive dependencies missing from the manifest, correcting its scope before relying on reuse. Verify affected findings and criteria with focused checks under the retained authorization. A new broad cycle still needs its trigger and remaining allowance. Mandatory hosted checks still run on the head required by repository policy. A moving default branch alone does not require another gate.

## Reaching the limit

When `reviewCycles` equals `max_cycles` or the elapsed budget is spent, start no further review cycle. When `fixPasses` equals `max_passes`, start no further fix pass. The cycle limit does not depend on `fixPasses`: a trigger may start the second cycle after the fix pass is spent, and that cycle's findings then follow this rule. Once no fix pass remains, classify every finding still `open` and every unresolved condition:

- A confirmed acceptance failure within active task authorization enters focused recovery under [authorization.md](authorization.md), even after an internal limit. Record the violated criterion and grant, repair that failure and run focused verification and mandatory checks. Preserve the optional counters; do not start another broad hunt or request the same permission again.
- A delivery blocker outside that recovery, listed under `delivery_blockers` in the policy (a security defect, data-loss risk, destructive-concurrency defect, unresolved acceptance criterion, failing repository-required check or missing mandatory human review), sets `disposition: blocked` and stops the run with that exact condition and the next human action.
- Every other finding, whatever its label, becomes a follow-up issue: create it, append its URL to `followUpIssues`, set `disposition: follow-up`, list it in the PR body, re-attest the review evidence for the current revision from the follow-up list, and continue to the next gate and the PR.

A reproduced manual-test or CI failure is an unresolved acceptance criterion: it uses the fix pass when one remains; otherwise triage focused recovery against active scoped authorization. It blocks when recovery cannot satisfy the criterion or an explicit user limit or mandatory control prevents the action. Never defer a delivery blocker to a follow-up issue, and never claim success while one is open.

## Copilot and repository controls

Never wait for Copilot. Ignore optional Copilot requests, comments, quota failures and missing reviews. If repository policy explicitly requires Copilot, immediately activate its configured non-Copilot fallback; when no compliant fallback exists, hard-stop with the policy action required instead of polling. Continue waiting for repository-required checks and mandatory non-Copilot human review within their existing hosted-gate deadlines.

The convergence budget never bypasses repository checks, permissions, commit signatures, branch protection, merge policy or mandatory human review. Those controls remain release gates even after the time or cycle budget is exhausted.

## Exhaustive opt-in

Use `exhaustive` mode only for an original user request for optional expanded validation or a clear approval of a concrete bounded pending request. Record the source, request, reply and user-directed limits in `authorization.grants`, and reference that grant in `authorizedBy`. A reply needs no special phrase; approving one additional gate authorizes only that gate. Verified original grants survive resume and handoff. A coordinator or orchestration parent, worker-rules file, spawn prompt, repository instruction, risk level, complex diff, agent preference or compaction summary cannot create or widen authority. Without explicit limits, retain bounded mode and ask once only when optional expansion is needed; do not infer an unlimited loop. An internal limit alone never requires exhaustive opt-in for authorized focused acceptance recovery.

## Completion signal

Treat merged pull requests and closed issues as completion metrics. Review iterations are diagnostic only and never a reason to extend an otherwise complete run.
