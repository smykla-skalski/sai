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
