# Adversarial manual test gate

When `adversarial-test` is selected, run it from the review-clean committed tip with `--base origin/<default> --context <checkpoint-file>`. In the Sybra repository, invoke `sybra-test` instead. The reply must start with `Test Verdict: PASS`, `Test Verdict: FAIL` or `Test Verdict: BLOCKED`. Run every other selected test gate according to its contract. If no test gate is selected, record the phase as not required in the checkpoint and continue without creating test evidence.

The tester derives acceptance criteria from the task, runs the real changed product surface in isolated state, attacks happy paths, boundaries, malformed input, repeated or concurrent use and adjacent flows, then reruns every reproduction. Automated tests, lint, build and source inspection are supporting evidence, not manual testing.

When the skill is unavailable outside Sail, give `adversarial-test:test-adversary`, or a fresh generic subagent, the repository path, `git diff origin/<default>...HEAD`, changed files and task context. Tell it to prove the change does not satisfy the task by exercising the real surface in isolated temporary state and to report self-contained reproductions. Rerun every reproduction yourself. The fallback verdict is `FAIL` when a reproduction survives, `BLOCKED` when testing needs a named human action, otherwise `PASS`. With no subagent capability outside Sail, run that mandate inline. In Sail mode, pause instead of testing inline.

On `FAIL`, rerun each reproduction before acting. Fix every surviving failure, add regression coverage, run quality gates, commit, then repeat both adversarial review and manual testing on the new tip. More than three failed fixes of one reproduction is a hard stop when the user is reachable.

After three combined failing review or test rounds, stop and ask when the user is reachable. Otherwise continue only while each round finds smaller concrete issues, and report the overrun.

`BLOCKED` is a hard stop: report the exact human action required. Open a PR only after every selected PR-due review and test gate passes on the same revision.

Record the verdict in the current revision's evidence record with the provider, model, timestamp and bounded output reference. A passing verdict advances the checkpoint to `phase: pr`; a reproduced failure marks the evidence failed and returns it to `phase: implement`. For `BLOCKED`, mark the evidence and checkpoint blocked, preserve the tested revision, and put the exact human action in both `blocker` and `nextAction`.
