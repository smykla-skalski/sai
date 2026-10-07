# Preparing the implementation branch

Fetch origin and resolve the repository's default branch. Start from its latest revision, then create a conventional branch:

| Source | Branch |
| :-- | :-- |
| GitHub issue | `<type>/issue-<number>-<slug>` |
| Jira ticket | `<type>/<jira-key-lowercase>-<slug>` |
| Task description | `<type>/<slug>` |

Use a conventional type (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore` or `revert`) and a short kebab-case slug.

When the target is another repository, create a new worktree rather than editing its main checkout. A Sail worker stays in its assigned worktree and branch: verify both, then skip branch creation and the eventual return to the default branch.

Stop if unrelated local changes overlap the task or the branch cannot be based safely on the current default revision.
