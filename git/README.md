# git

A Claude Code plugin for git workflow automation: worktree creation with context transfer, branch cleanup, and reset utilities.

## Installation

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/git/
```

## Skills

### worktree

Create git worktree with context transfer for feature branches. Handles conventional branch naming, IDE detection, symlinks for context files, and clipboard setup.

```
/worktree implement retry logic for API calls
/worktree --quick fix login bug
/worktree add caching --ide webstorm
```

| Flag           | Purpose                           |
|:---------------|:----------------------------------|
| `--quick`      | Skip questions, sensible defaults |
| `--no-pbcopy`  | Skip clipboard copy               |
| `--no-ide`     | Disable IDE detection             |
| `--ide <name>` | Override auto-detected IDE        |

### reset-main

Reset current branch to remote's default branch after PR merge.

```
/reset-main
/reset-main upstream
/reset-main --force
```

| Flag            | Purpose                       |
|:----------------|:------------------------------|
| `--force`, `-f` | Skip dirty state confirmation |

### clean-gone

Clean up local branches with deleted remote tracking and their worktrees.

```
/clean-gone
/clean-gone --dry-run
/clean-gone --no-worktrees
```

| Flag             | Purpose                              |
|:-----------------|:-------------------------------------|
| `--dry-run`      | Preview only, no changes             |
| `--no-worktrees` | Branches only, skip worktree removal |

### worktree-review

Validate git worktree setup including symlinks, excludes, and tracking.

```
/worktree-review
/worktree-review /path/to/worktree
```

## License

MIT
