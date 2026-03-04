---
name: worktree-review
description: Validate git worktree setup including symlinks, git excludes, and tracking configuration. Use after creating worktrees, when debugging worktree issues, or when auditing existing worktrees. Prevents broken symlinks and git tracking problems.
argument-hint: "[worktree-path]"
allowed-tools: Bash, Read, Glob
user-invocable: true
---

# Worktree Review

Validate worktree structure, symlink integrity, git excludes, and branch tracking.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to worktree (default: current working directory)

## Constraints

- Read-only analysis — never modify files
- Verify every check explicitly — never assume worktree state
- Check both symlink existence AND target — broken symlinks are critical failures
- Verify git excludes — symlinks must be excluded to prevent accidental commits
- Zero false positives — only flag genuine issues with specific evidence

## Workflow

### Phase 1: Identify Worktree

1. Determine worktree path from argument or current directory
2. Verify `.git` file exists (file, not directory) — confirms this is a worktree
3. If not a worktree: report error and stop

### Phase 2: Structure Checks

| Check               | Command             | Expected             |
|:--------------------|:--------------------|:---------------------|
| `.git` file exists  | `test -f "$W/.git"` | File (not directory) |
| Points to worktree  | `cat "$W/.git"`     | Contains `gitdir:`   |
| Worktree registered | `git worktree list` | Path listed          |

### Phase 3: Branch Configuration

| Check               | Command                                          | Expected      |
|:--------------------|:-------------------------------------------------|:--------------|
| Branch exists       | `git -C "$W" branch --show-current`              | Non-empty     |
| Tracking configured | `git -C "$W" rev-parse --abbrev-ref @{upstream}` | remote/branch |
| Remote exists       | `git -C "$W" remote -v`                          | At least one  |

### Phase 4: Symlink Validation

For each candidate file (`.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`):

1. Check if tracked in source worktree via `git ls-files "{name}"`
   - Tracked → should NOT be symlinked (regular file from checkout)
   - Untracked → should be symlinked if exists in source

2. For untracked files that should be symlinked:

| Check          | Command                | Expected         |
|:---------------|:-----------------------|:-----------------|
| Symlink exists | `test -L "$W/{name}"`  | True             |
| Target exists  | `test -e "$W/{name}"`  | True             |
| Target correct | `readlink "$W/{name}"` | Points to source |

3. For tracked files: verify NOT symlinked

### Phase 5: Git Excludes

| Check                   | Command                                           | Expected           |
|:------------------------|:--------------------------------------------------|:-------------------|
| worktreeConfig enabled  | `git -C "$W" config extensions.worktreeConfig`    | `true`             |
| excludesFile configured | `git -C "$W" config --worktree core.excludesFile` | Valid path         |
| excludesFile exists     | `test -f "$excludesFile"`                         | True               |
| Contains symlinks       | `cat "$excludesFile"`                             | Lists all symlinks |

### Phase 6: Git Status

| Check                 | Command                          | Expected           |
|:----------------------|:---------------------------------|:-------------------|
| No symlinks in status | `git -C "$W" status --porcelain` | No symlink entries |

### Phase 7: Report

Output findings in this format:

```
# Worktree Quality Review: {path}

## Summary

{PASS|WARN|FAIL}: {one-line summary}

## Worktree Info

| Property        | Value           |
|:----------------|:----------------|
| Path            | {path}          |
| Branch          | {branch}        |
| Tracking        | {remote/branch} |
| Source Worktree | {source-path}   |

## Findings

### Critical (Must Fix)
- **{check}**: {issue} — {evidence}

### Warnings (Should Fix)
- **{check}**: {issue} — {evidence}

### Info
- **{check}**: {observation}

## Checklist Results

### Structure
- [x] `.git` file exists
- [x] Points to valid worktree metadata
- [ ] Branch tracking configured

### Symlinks (untracked files only)
- [x] `.claude/` → symlink valid, target exists
- [x] `CLAUDE.md` → tracked file, correctly NOT symlinked
- [x] `AGENTS.md` → correctly absent (source doesn't exist)

### Git Excludes
- [x] worktreeConfig enabled
- [x] excludesFile configured
- [x] All symlinked files in excludes

### Git Status
- [x] No symlinks in status

## Recommendations
1. {Specific fix command}
```

## Verdict Criteria

| Status   | Criteria                |
|:---------|:------------------------|
| **PASS** | 0 critical, ≤2 warnings |
| **WARN** | 0 critical, 3+ warnings |
| **FAIL** | 1+ critical             |

## Edge Cases

- Path is not a worktree: critical error, `.git` should be file not directory
- Tracked files symlinked: critical — should be regular files from checkout
- Untracked files not symlinked: warning — context transfer incomplete
- Broken symlinks: critical — symlink exists but target missing
- Symlinks in git status: critical — excludes misconfigured

## Example Invocations

```bash
# Review worktree in current directory
/worktree-review

# Review specific worktree
/worktree-review /path/to/myapp-feat-auth
```
