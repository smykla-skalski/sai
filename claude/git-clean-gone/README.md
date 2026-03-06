# git-clean-gone

A Claude Code plugin to clean up local branches with deleted remote tracking and their worktrees.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install git-clean-gone@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/git-clean-gone/
```

## Skills

### git-clean-gone

Clean up local branches with deleted remote tracking and their worktrees. Detects gone branches, squash-merged PRs (via `gh`), and rebased branches (via `git cherry`).

```
/git-clean-gone
/git-clean-gone --dry-run
/git-clean-gone --no-worktrees
```

| Flag             | Purpose                              |
|:-----------------|:-------------------------------------|
| `--dry-run`      | Preview only, no changes             |
| `--no-worktrees` | Branches only, skip worktree removal |

## License

MIT
