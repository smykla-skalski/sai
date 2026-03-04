---
name: clean-gone
description: Clean up local branches with deleted remote tracking and their worktrees. Use after merging PRs to remove stale branches, detect squash-merged and rebased branches, and clean up associated worktrees.
argument-hint: "[--dry-run] [--no-worktrees]"
allowed-tools: Bash
user-invocable: true
---

# Clean Gone

Delete local branches whose remote tracking is gone or merged, and remove their associated worktrees.

## Arguments

Parse from `$ARGUMENTS`:

| Flag             | Default | Purpose                                          |
|:-----------------|:--------|:-------------------------------------------------|
| (none)           | —       | Full cleanup: gone + merged branches + worktrees |
| `--dry-run`      | off     | Preview only, no changes                         |
| `--no-worktrees` | off     | Branches only, skip worktree removal             |

## Constraints

- First action MUST be Bash — no text output before executing the script
- Never delete the current branch — skip and report in summary
- Never remove the main worktree — only feature/task worktrees
- Execute `"$SKILL_DIR/scripts/clean-gone.sh"` as a single Bash invocation
- Output summary directly as text (NOT via bash/printf)

## Workflow

### Phase 1: Execute Cleanup Script

Execute `"$SKILL_DIR/scripts/clean-gone.sh"` immediately, passing through any flags from `$ARGUMENTS`.

- No flags → full cleanup (gone + merged branches + worktrees)
- `--dry-run` → preview only, no changes
- `--no-worktrees` → gone branches only, no worktree removal or merge detection
- Invalid flag → script exits with error, show valid options (`--dry-run`, `--no-worktrees`), stop

### Phase 2: Output Summary

Parse script output line prefixes and render formatted summary directly as text.

**Line prefixes** (from script output):

| Prefix                           | Meaning          |
|:---------------------------------|:-----------------|
| `DELETED:branch:reason`          | Deleted branch   |
| `REMOVED_WT:worktree:branch`     | Removed worktree |
| `SKIPPED:branch:reason`          | Skipped branch   |
| `KEPT:branch:reason`             | Kept branch      |
| `KEPT_WT:worktree:branch:reason` | Kept worktree    |

Dry-run uses `WOULD_DELETE`, `WOULD_REMOVE_WT`, `WOULD_SKIP`, `WOULD_KEEP`, `WOULD_KEEP_WT`.

**Summary format:**

```
**Cleanup Summary**

Deleted:
  🗑️ fix/old-feature (gone)
  🗂️ fix-old-feature-wt (worktree)

Skipped:
  ⚠️ feat/current-work (current branch)

Kept:
  🗂️ wt-name (worktree) - branch (N unmerged)
  ℹ️ feat/in-progress (14 unmerged)
```

Only include sections with items. Empty state: `✅ Repository already clean — no branches to process`

Dry-run header: `**Dry Run Preview**` with "Would delete/remove" phrasing.

## Cleanup Logic

- Detects remote from main branch's upstream (works with origin, upstream, etc.)
- Deletes branches marked `[gone]` (remote tracking deleted)
- Deletes branches fully merged via rebase/cherry-pick (`git cherry`)
- Deletes branches squash-merged via PR (`gh pr list --state merged`)
- Removes associated worktrees before branch deletion
- Skips main and current branch
- Falls back gracefully if `gh` CLI unavailable

## Edge Cases

- Invalid flags: report unknown flag, show valid options, stop
- No cleanable branches: report "Repository already clean"
- Current branch is gone/merged: skip deletion, warn in summary
- Uncommitted changes in worktree: force remove with `--force` flag
- No `gh` CLI: squash merges won't be detected, only `git cherry` used
- No remote configured: falls back to first available remote

## Example Invocations

```bash
# Full cleanup
/clean-gone

# Preview what would be deleted
/clean-gone --dry-run

# Only delete gone branches, no worktree removal
/clean-gone --no-worktrees
```
