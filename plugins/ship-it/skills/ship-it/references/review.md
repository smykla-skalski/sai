# Adversarial code review gate

When `adversarial-review` is selected, use the installed skill only when it accepts the resolved selectors and returns a route record for every Code and Findings worker. Otherwise treat it as unavailable and dispatch the routed generic workers below. An installed skill that hides worker routes or falls back inline is rejected under strict independence. The reply must start with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`. Run every other selected review gate according to its contract. If no review gate is selected, create no review evidence and atomically advance the checkpoint to `phase: test` with the selected test gate as `nextAction`, or to `phase: pr` with PR creation as `nextAction` when no test gate is selected.

For GitHub work, verify and renew the claim when due before writing review evidence. A review from another holder or after expiry does not satisfy the gate until ownership is reconciled.

The default review cycle uses exactly two clean-context passes: one Code Adversary hunts concrete failures and unmet acceptance criteria, then one fresh Findings Adversary tries to refute every finding. Follow the shared convergence policy's cycle, elapsed-time and fix-pass counters.

Resolve and record each review invocation before dispatch. Under strict independence, reject the implementation provider-and-model pair, unresolved aliases, implementation execution reuse and inline execution. A policy-authorized weaker route records degraded independence and its reasons; it never claims to be independent.

When the skill is unavailable outside Sail, give every subagent the repository path, `git diff origin/<default>...HEAD`, changed files and task context:

1. Spawn `adversarial-review:code-adversary`, or a generic subagent told to assume the change is broken, prove each finding with a failing input and `file:line`, and propose a fix. Label findings `blocking:`, `issue:` or `question:`.
2. After it returns, spawn a fresh `adversarial-review:findings-adversary`, or a fresh generic subagent told to refute each finding against the source. Give it the same inputs plus only the numbered findings, never the first agent's reasoning.

The fallback verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives refutation, otherwise `CLEAN`. With no subagent capability, block under strict independence. A repository policy with `independent_review: degraded` may authorize the two inline passes outside Sail only; record inline execution, degraded independence and its reasons. Sail always pauses instead of running either pass inline.

On `NEEDS_FIXES`:

1. Fix every surviving `blocking:` and `issue:` finding.
2. Add regression coverage where behavior was wrong.
3. Run focused verification and commit the fix.
4. Re-attest the new tip from the independent findings and focused verification; do not re-review routine fixes.
5. Run a second and final review cycle only for security, data loss, destructive concurrency or unresolved acceptance failures.

Put unresolved `question:` findings in the PR body when the repository cannot settle them. After the one fix pass, create follow-up issues for later non-blocking findings. Do not start manual testing while a required defect remains unresolved.

Record each verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A clean verdict advances the checkpoint to `phase: test`; a surviving finding marks the evidence failed and returns it to `phase: implement` with the finding as `nextAction`. Any later source change marks the entire record stale.

Stop when the second review cycle or 90-minute shared budget is exhausted. Exhaustive review requires explicit user opt-in recorded in the checkpoint.
