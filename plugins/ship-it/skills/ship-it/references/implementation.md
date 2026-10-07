# Implementing and committing the change

Follow repository patterns and implement the smallest complete behavior. Add or extend behavior-focused tests; avoid tests that only mirror implementation details.

Before every commit, run the relevant formatter, linter, type checker, build and tests discovered during exploration. Fix root causes. Never add a lint or type suppression, bypass hooks, or use `--no-verify`.

Keep commits focused and sign them. Commit titles use `<type>(<scope>): <description>`, require a scope, stay within 50 characters and contain no PR reference or AI attribution. Wrap body lines at 72 characters.

Add the source footer when applicable:

| Source | Footer |
| :-- | :-- |
| GitHub issue in this repository | `Refs #<number>` |
| GitHub issue in another repository | `Refs owner/repo#<number>` |
| Jira ticket | `Refs KEY-123` |
| Task description | no footer |

Comply with every commit hook. If a hook changes files, inspect and stage the intended result before committing again.

After every successful commit, atomically update the durable checkpoint with the new `HEAD`, current branch and next action. After implementation gates pass, set `phase` to `review` and `nextAction` to adversarial review. On a hard stop, preserve the last verified revision and record the blocker; never claim an uncommitted or failed revision as verified checkpoint state.

Before entering review, inspect version bumps across local commits. When the repository expects one bump, squash the unpublished branch now (`git reset --soft "$(git merge-base HEAD origin/<default>)"` then one signed commit with hooks enabled), run the quality gates, and record the rewritten `HEAD`. Review and test always start after the last history rewrite.
