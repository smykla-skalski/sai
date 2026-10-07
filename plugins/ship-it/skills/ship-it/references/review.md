# Adversarial code review gate

When `adversarial-review` is selected, run `adversarial-review:adversarial-review` against the committed branch with `--base origin/<default> --context <checkpoint-file>`. Before relying on it under strict independence, verify that it launched fresh review workers; an installed skill that fell back inline is still an inline route and is rejected. The reply must start with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`. Run every other selected review gate according to its contract. If no review gate is selected, create no review evidence and atomically advance the checkpoint to `phase: test` with the selected test gate as `nextAction`, or to `phase: pr` with PR creation as `nextAction` when no test gate is selected.

For GitHub work, verify and renew the claim when due before writing review evidence. A review from another holder or after expiry does not satisfy the gate until ownership is reconciled.

The review uses two clean-context passes: a Code Adversary hunts concrete failures and unmet acceptance criteria, then a fresh Findings Adversary tries to refute every finding.

Resolve and record each review invocation before dispatch. Under strict independence, reject the implementation provider-and-model pair, unresolved aliases, implementation execution reuse and inline execution. A policy-authorized weaker route records degraded independence and its reasons; it never claims to be independent.

When the skill is unavailable outside Sail, give every subagent the repository path, `git diff origin/<default>...HEAD`, changed files and task context:

1. Spawn `adversarial-review:code-adversary`, or a generic subagent told to assume the change is broken, prove each finding with a failing input and `file:line`, and propose a fix. Label findings `blocking:`, `issue:` or `question:`.
2. After it returns, spawn a fresh `adversarial-review:findings-adversary`, or a fresh generic subagent told to refute each finding against the source. Give it the same inputs plus only the numbered findings, never the first agent's reasoning.

The fallback verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives refutation, otherwise `CLEAN`. With no subagent capability, block under strict independence. A repository policy with `independent_review: degraded` may authorize the two inline passes outside Sail only; record inline execution, degraded independence and its reasons. Sail always pauses instead of running either pass inline.

On `NEEDS_FIXES`:

1. Fix every surviving `blocking:` and `issue:` finding.
2. Add regression coverage where behavior was wrong.
3. Run the repository quality gates and commit the fix.
4. Review the new committed tip again.

Put unresolved `question:` findings in the PR body when the repository cannot settle them. Do not start manual testing until the verdict is `CLEAN`.

Record each verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A clean verdict advances the checkpoint to `phase: test`; a surviving finding marks the evidence failed and returns it to `phase: implement` with the finding as `nextAction`. Any later source change marks the entire record stale.

After three failing rounds, stop and ask when the user is reachable. Otherwise continue only while each round finds smaller concrete issues, and report the overrun.
