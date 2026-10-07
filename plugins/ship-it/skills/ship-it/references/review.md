# Adversarial code review gate

Run `adversarial-review:adversarial-review` against the committed branch with `--base origin/<default> --context <checkpoint-file>`. The reply must start with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`.

The review uses two clean-context passes: a Code Adversary hunts concrete failures and unmet acceptance criteria, then a fresh Findings Adversary tries to refute every finding.

When the skill is unavailable outside Sail, give every subagent the repository path, `git diff origin/<default>...HEAD`, changed files and task context:

1. Spawn `adversarial-review:code-adversary`, or a generic subagent told to assume the change is broken, prove each finding with a failing input and `file:line`, and propose a fix. Label findings `blocking:`, `issue:` or `question:`.
2. After it returns, spawn a fresh `adversarial-review:findings-adversary`, or a fresh generic subagent told to refute each finding against the source. Give it the same inputs plus only the numbered findings, never the first agent's reasoning.

The fallback verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives refutation, otherwise `CLEAN`. With no subagent capability outside Sail, run the two passes inline in order and reread the source before refutation. In Sail mode, pause instead of running either pass inline.

On `NEEDS_FIXES`:

1. Fix every surviving `blocking:` and `issue:` finding.
2. Add regression coverage where behavior was wrong.
3. Run the repository quality gates and commit the fix.
4. Review the new committed tip again.

Put unresolved `question:` findings in the PR body when the repository cannot settle them. Do not start manual testing until the verdict is `CLEAN`.

Record each verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A clean verdict advances the checkpoint to `phase: test`; a surviving finding marks the evidence failed and returns it to `phase: implement` with the finding as `nextAction`. Any later source change marks the entire record stale.

After three failing rounds, stop and ask when the user is reachable. Otherwise continue only while each round finds smaller concrete issues, and report the overrun.
