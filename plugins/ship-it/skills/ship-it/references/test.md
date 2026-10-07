# Adversarial manual test gate

From the review-clean committed tip, run `adversarial-test:adversarial-test` with `--base origin/<default> --context <task-context-file>`. In the Sybra repository, invoke `sybra-test` instead. The reply must start with `Test Verdict: PASS`, `Test Verdict: FAIL` or `Test Verdict: BLOCKED`.

The tester derives acceptance criteria from the task, runs the real changed product surface in isolated state, attacks happy paths, boundaries, malformed input, repeated or concurrent use and adjacent flows, then reruns every reproduction. Automated tests, lint, build and source inspection are supporting evidence, not manual testing.

When the skill is unavailable outside Sail, give `adversarial-test:test-adversary`, or a fresh generic subagent, the repository path, `git diff origin/<default>...HEAD`, changed files and task context. Tell it to prove the change does not satisfy the task by exercising the real surface in isolated temporary state and to report self-contained reproductions. Rerun every reproduction yourself. The fallback verdict is `FAIL` when a reproduction survives, `BLOCKED` when testing needs a named human action, otherwise `PASS`. With no subagent capability outside Sail, run that mandate inline. In Sail mode, pause instead of testing inline.

On `FAIL`, rerun each reproduction before acting. Fix every surviving failure, add regression coverage, run quality gates, commit, then repeat both adversarial review and manual testing on the new tip. More than three failed fixes of one reproduction is a hard stop when the user is reachable.

After three combined failing review or test rounds, stop and ask when the user is reachable. Otherwise continue only while each round finds smaller concrete issues, and report the overrun.

`BLOCKED` is a hard stop: report the exact human action required. Open a PR only after `PASS` on the same revision that received `Review Verdict: CLEAN`.
