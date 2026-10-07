# Adversarial manual test gate

When `adversarial-test` is selected, use the installed skill only when it accepts the resolved selectors and returns a route record for every tester execution and retry. Otherwise treat it as unavailable and dispatch the routed generic tester below. In the Sybra repository, invoke `sybra-test` only when it meets the same route contract. The reply must start with `Test Verdict: PASS`, `Test Verdict: FAIL` or `Test Verdict: BLOCKED`. Run every other selected test gate according to its contract. If no test gate is selected, create no test evidence and atomically advance the checkpoint to `phase: pr` with PR-due evidence validation and PR creation as `nextAction`.

For GitHub work, verify and renew the claim when due before writing manual-test evidence. A verdict from another holder or after expiry does not satisfy the gate until ownership is reconciled.

The tester derives acceptance criteria from the task, runs the real changed product surface in isolated state, attacks happy paths, boundaries, malformed input, repeated or concurrent use and adjacent flows, then reruns every reproduction. Automated tests, lint, build and source inspection are supporting evidence, not manual testing.

Resolve and record a fresh testing role before each adversarial-test dispatch.

When the skill is unavailable outside Sail, give `adversarial-test:test-adversary`, or a fresh generic subagent, the repository path, `git diff origin/<default>...HEAD`, changed files and task context. Tell it to prove the change does not satisfy the task by exercising the real surface in isolated temporary state and to report self-contained reproductions. Rerun every reproduction yourself. The fallback verdict is `FAIL` when a reproduction survives, `BLOCKED` when testing needs a named human action, otherwise `PASS`. With no subagent capability, block by default. A repository policy with `independent_review: degraded` may authorize inline testing outside Sail only; record inline execution, degraded independence and its reasons. Sail always pauses instead of testing inline.

On `FAIL`, rerun each reproduction before acting. Fix every surviving failure, add regression coverage, run quality gates, commit, then repeat both adversarial review and manual testing on the new tip. More than three failed fixes of one reproduction is a hard stop when the user is reachable.

After three combined failing review or test rounds, stop and ask when the user is reachable. Otherwise continue only while each round finds smaller concrete issues, and report the overrun.

`BLOCKED` is a hard stop: report the exact human action required. Open a PR only after every selected PR-due review and test gate passes on the same revision.

Record the verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A passing verdict advances the checkpoint to `phase: pr`; a reproduced failure marks the evidence failed and returns it to `phase: implement`. For `BLOCKED`, mark the evidence and checkpoint blocked, preserve the tested revision, and put the exact human action in both `blocker` and `nextAction`.
