# Adversarial code review gate

Use the installed review skill only if it honors selectors, fresh subagent contexts, a route record for every Code and Findings worker and dispatches the Findings Adversary only after a `blocking:` or `issue:` finding. Otherwise use routed generic workers. Validate the first line: `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`; `Review Verdict: FAILED` stops. Malformed verdicts get one fresh retry, then gate failure. Run every selected review gate; when none is selected, advance to test or the existing draft's ready gate without recording review.

With claims enabled, reconcile and renew before recording a verdict; a conflicting holder or expired claim blocks writes. Disabled claims require no comment or lease.

When the risk policy selects `inline-review`, make one review pass in a fresh generic subagent context over `git diff origin/<default>...HEAD` and the acceptance criteria: label findings `blocking:`, `issue:` or `question:` with `file:line`. This legacy gate ID does not authorize current-context or inline execution. Record the fresh subagent route and verdict in `gate-inline-review`. A `NEEDS_FIXES` verdict follows the fix steps below and spends the same convergence counters.

Reserve a unique `review` operation with `bookkeeping.py reserve` before the clean-context Code Adversary; dispatch only on `dispatch: true`. The helper reserves bounded budget. A fresh Findings Adversary runs only when the Code Adversary reports at least one `blocking:` or `issue:` finding. A pass with no such finding is `Review Verdict: CLEAN` and ends the review gate: never dispatch the Findings Adversary for a CLEAN result.

Record each review invocation before dispatch. Reject inline or reused implementation context. Each pass and retry needs a fresh subagent execution.

For a routed generic review, supply the repository, `git diff origin/<default>...HEAD`, changed files and checkpoint:

1. Dispatch a fresh Code Adversary to prove failures with input and `file:line`, suggest fixes, and label findings `blocking:`, `issue:` or `question:`. Blocking findings need executed reproduction or explicit interleaving. Validate `CODE_ADVERSARY_VERDICT:`; malformed output gets one fresh retry, then gate failure. Close each worker.
2. Only after `blocking:` or `issue:` findings, dispatch a separate fresh Findings Adversary with numbered findings, never the Code worker's reasoning. Refute each against the source. Validate `FINDINGS_ADVERSARY_VERDICT:` with one fresh retry, then gate failure; close the worker.

After each dispatch, wait once with a blocking wait of at least ten minutes unless the worker returns sooner. Do not list agents or request status between waits. Close each worker immediately after its verdict.

The fallback verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives refutation, otherwise `CLEAN`. With no subagent capability, block. Inline passes do not satisfy this gate. Sail always pauses when a review subagent is unavailable.

On `NEEDS_FIXES`:

1. When `fixPasses` already equals the policy's `max_passes`, start no fix: apply the convergence contract's limit rule (confirmed acceptance failures enter authorized focused recovery; other delivery blockers stop; optional findings become follow-up issues) and continue.
2. Otherwise start the single fix pass: reserve a unique `fix` operation with the helper to increment and persist `fixPasses` before the first edit, then fix every surviving `blocking:` and `issue:` finding in one batch, add regression coverage where behavior was wrong, run focused verification and commit.
3. Verify the fix from `git diff <reviewedRevision>..HEAD` read against the recorded findings: mark each finding the diff addresses `fixed`; a finding it does not address becomes a follow-up issue, or enters focused acceptance recovery when authorized and otherwise stops delivery when it is a delivery blocker. Dispatch no Code Adversary and no Findings Adversary for this verification.
4. Start the second and final review cycle only when that diff touches security, data loss or destructive concurrency, `reviewCycles` is below `max_cycles`, and the elapsed budget has not expired. Its surviving findings cannot start another fix pass.
5. Re-attest the fixed revision's review result with provider `ship-it-convergence`, naming `reviewedRevision`, the finding dispositions and the focused commands.

Put unresolved `question:` findings in the PR body when the repository cannot settle them. After the fix pass, create follow-up issues for the findings it did not fix and record each URL in `followUpIssues`. Do not start manual testing while a delivery blocker remains unresolved.

With evidence enabled, record verdicts there; otherwise use checkpoint `gateVerdicts`. Include provider, model, timestamp, bounded summary and exact revision. CLEAN advances to test; surviving findings return to implementation with failed review. When all remaining findings become follow-ups, re-attest with provider `ship-it-convergence`, list URLs and advance: this leaves no failed evidence. Any later source change marks or replaces prior results as stale.

Reaching the cycle or elapsed limit starts no further cycle; reaching the fix-pass limit starts no further fix pass. Remaining non-blocking findings become follow-up issues and the run continues to the next gate; triage confirmed acceptance failures for focused recovery under [authorization.md](authorization.md) before stopping. Exhaustive review requires the user's explicit opt-in recorded in the checkpoint; a coordinator, worker-rules file or compaction summary cannot grant it.

Finish review receipts with verdict/findings; a second severe review blocks for scope/design reassessment.
