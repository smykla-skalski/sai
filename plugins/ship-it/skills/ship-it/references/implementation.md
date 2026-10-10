# Implementing and committing the change

Follow repository patterns and implement the smallest complete behavior. Add or extend behavior-focused tests; avoid tests that only mirror implementation details.

Resolve and record the implementation role before the first source edit. Its execution identity is the baseline for ensuring review and testing use fresh subagent contexts.

For GitHub work with claims enabled, verify the checkpoint's claim immediately before the first source edit. Renew it only immediately before a repository or GitHub write when due, never on a timer. A failed renewal stops that write and later edits until claim reconciliation succeeds.

Before an initial commit, run the focused formatter, checks and tests needed to keep the revision sound. During the convergence contract's single fix pass, run focused tests for changed behavior and reproduced failures. Run the complete repository quality gate once against the final candidate revision before delivery. Fix root causes. Never add a lint or type suppression, bypass hooks, or use `--no-verify`.

Keep commits focused and sign them. Commit titles use `<type>(<scope>): <description>`, require a scope, stay within 50 characters and contain no PR reference or AI attribution. Wrap body lines at 72 characters.

Add the source footer when applicable:

| Source | Footer |
| :-- | :-- |
| GitHub issue in this repository | `Refs #<number>` |
| GitHub issue in another repository | `Refs owner/repo#<number>` |
| Jira ticket | `Refs KEY-123` |
| Task description | no footer |

Comply with every commit hook. If a hook changes files, inspect and stage the intended result before committing again.

After every successful commit, create the new revision's evidence record when evidence is enabled, mark the previous record stale, then atomically update the durable checkpoint with the new `HEAD`, current branch, evidence pointer or checkpoint verdicts, and next action. Select and report risk before validation. Run local gates according to the shared convergence budget and record their result. After implementation gates pass, always advance to `phase: publish` with draft-PR creation as `nextAction`; publishing starts CI before any selected review or test gate. On a hard stop, preserve the last verified revision and record the blocker; never claim an uncommitted or failed revision as verified checkpoint state.

Before entering review, inspect version bumps across local commits. When the repository expects one bump, squash the unpublished branch now (`git reset --soft "$(git merge-base HEAD origin/<default>)"` then one signed commit with hooks enabled), create evidence for the rewritten `HEAD`, and rerun the quality gates. Review and test always start after the last history rewrite.
