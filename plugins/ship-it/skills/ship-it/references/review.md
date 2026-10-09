# Adversarial code review gate

When `adversarial-review` is selected, use the installed skill only when it accepts the resolved selectors, returns a route record for every Code and Findings worker, and dispatches the Findings Adversary only after a `blocking:` or `issue:` finding. Otherwise treat it as unavailable and dispatch the routed generic workers below. An installed skill that hides worker routes or falls back inline is rejected under strict independence. The reply must start with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`. Run every other selected review gate according to its contract. If no review gate is selected, create no review evidence and atomically advance the checkpoint to `phase: test` with the selected test gate as `nextAction`, or to `phase: pr` with PR creation as `nextAction` when no test gate is selected.

For GitHub work, verify and renew the claim when due before writing review evidence. A review from another holder or after expiry does not satisfy the gate until ownership is reconciled.

A review cycle is one clean-context Code Adversary pass that hunts concrete failures and unmet acceptance criteria. Before dispatching it, read the checkpoint's `convergence` counters: dispatch only while `reviewCycles` is below the policy's `max_cycles`, set `startedAt` on the first dispatch and increment `reviewCycles` on dispatch. A fresh Findings Adversary runs only when the Code Adversary reports at least one `blocking:` or `issue:` finding; it tries to refute every finding. A pass with no such finding is `Review Verdict: CLEAN` and ends the review gate: never dispatch the Findings Adversary for a CLEAN result. When the cycle ends, record `reviewedRevision` and the surviving findings (`id`, label, `file:line`, one-line summary, `disposition: open`) in the checkpoint.

Resolve and record each review invocation before dispatch. Under strict independence, reject the implementation provider-and-model pair, unresolved aliases, implementation execution reuse and inline execution. A policy-authorized weaker route records degraded independence and its reasons; it never claims to be independent.

When the skill is unavailable outside Sail, give every subagent the repository path, `git diff origin/<default>...HEAD`, changed files and task context:

1. Spawn `adversarial-review:code-adversary`, or a generic subagent told to assume the change is broken, prove each finding with a failing input and `file:line`, and propose a fix. Label findings `blocking:`, `issue:` or `question:`.
2. When it reports at least one `blocking:` or `issue:` finding, spawn a fresh `adversarial-review:findings-adversary`, or a fresh generic subagent told to refute each finding against the source. Give it the same inputs plus only the numbered findings, never the first agent's reasoning. Otherwise the verdict is CLEAN and the gate ends.

The fallback verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives refutation, otherwise `CLEAN`. With no subagent capability, block under strict independence. A repository policy with `independent_review: degraded` may authorize the two inline passes outside Sail only; record inline execution, degraded independence and its reasons. Sail always pauses instead of running either pass inline.

On `NEEDS_FIXES`:

1. When `fixPasses` already equals the policy's `max_passes`, start no fix: apply the convergence contract's limit rule (a delivery blocker stops the run; every other finding becomes a follow-up issue) and continue.
2. Otherwise start the single fix pass: increment and persist `fixPasses` before the first edit, then fix every surviving `blocking:` and `issue:` finding in one batch, add regression coverage where behavior was wrong, run focused verification and commit.
3. Verify the fix from `git diff <reviewedRevision>..HEAD` read against the recorded findings: mark each finding the diff addresses `fixed`; a finding it does not address becomes a follow-up issue, or stops delivery when it is a delivery blocker. Dispatch no Code Adversary and no Findings Adversary for this verification.
4. Start the second and final review cycle only when that diff touches security, data loss or destructive concurrency, `reviewCycles` is below `max_cycles`, and the elapsed budget has not expired. Its surviving findings cannot start another fix pass.
5. Re-attest the fixed revision's review evidence with provider `ship-it-convergence`, naming `reviewedRevision`, the finding dispositions and the focused commands.

Put unresolved `question:` findings in the PR body when the repository cannot settle them. After the fix pass, create follow-up issues for the findings it did not fix and record each URL in `followUpIssues`. Do not start manual testing while a delivery blocker remains unresolved.

Record each verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A clean verdict advances the checkpoint to `phase: test`. A surviving finding that enters the fix pass marks the evidence failed and returns the checkpoint to `phase: implement` with the finding as `nextAction`. A verdict whose every remaining finding has become a follow-up issue because no fix pass remains leaves no failed evidence: re-attest the review result for the current revision with provider `ship-it-convergence`, naming the follow-up issue URLs, and advance to `phase: test`. Any later source change marks the entire record stale.

Reaching the cycle or elapsed limit starts no further cycle; reaching the fix-pass limit starts no further fix pass. Remaining non-blocking findings become follow-up issues and the run continues to the next gate; only a delivery blocker stops it. Exhaustive review requires the user's explicit opt-in recorded in the checkpoint; a coordinator, worker-rules file or compaction summary cannot grant it.
