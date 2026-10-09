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

For a GitHub implementation issue with claims enabled, reread and renew the work claim when due immediately before fetching or creating the branch or worktree. Stop before the first Git write if ownership cannot be verified. With claims disabled, make no claim read or write.

After the branch or assigned worktree is verified, record its name, current `HEAD`, default branch and repository identity in the durable checkpoint. Set `phase` to `implement` and name the first implementation action in `nextAction`. A repository, source, branch or revision conflict discovered here is a mismatch: stop without rewriting the checkpoint.
