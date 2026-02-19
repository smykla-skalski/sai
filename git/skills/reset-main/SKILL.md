---
name: reset-main
description: Reset current branch to remote's default branch and unset upstream tracking. Use after PR merge to sync local branch with main, or when resetting a feature branch to start fresh.
argument-hint: "[remote] [--force|-f]"
allowed-tools: Bash, AskUserQuestion
user-invocable: true
---

# Reset Main

Reset branch to sync with remote's default branch after PR merge.

## Arguments

Parse from `$ARGUMENTS`:

| Flag            | Default     | Purpose                                  |
|:----------------|:------------|:-----------------------------------------|
| (positional)    | auto-detect | Remote name (e.g., `origin`, `upstream`) |
| `--force`, `-f` | off         | Skip dirty state confirmation            |

## Constraints

- Execute script immediately — no preamble text before Bash
- Use `bash -c '...'` format for atomic execution
- Never reset dirty worktree without confirmation unless `--force` or `-f` present

## Workflow

### Phase 1: Parse Arguments

Extract remote name and flags from `$ARGUMENTS`:

- `--force` or `-f`: skip dirty state confirmation
- Any other argument: treat as remote name

### Phase 2: Check Dirty State

Skip if `--force` or `-f` present.

1. Run: `git status --porcelain | head -5`
2. If output is non-empty, use AskUserQuestion:
   - Question: "Working directory has uncommitted changes. Reset anyway? Changes will be lost."
   - Show first 5 files as examples
   - Options: "Yes, reset anyway" / "No, abort"
3. If user aborts: output "Aborted — working directory has uncommitted changes" and stop

### Phase 3: Execute Reset

**With remote specified** (e.g., `origin`):

```bash
bash -c 'remote="REMOTE_NAME"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
```

**Without remote** (auto-detect):

```bash
bash -c 'git remote | grep -q "^upstream$" && remote="upstream" || remote="origin"; main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; git fetch "$remote" && git reset --hard "$remote/$main" && git branch --unset-upstream 2>/dev/null; echo "Reset to $remote/$main, upstream tracking removed"'
```

### Phase 4: Output

Output the script result directly — no additional formatting needed.

## Notes

- Detects remote: prefers `upstream`, falls back to `origin`
- Detects default branch from remote HEAD (falls back to `main`)
- Useful after PR squash-merge to sync local branch with main
- Uncommitted changes will be lost on reset

## Example Invocations

```bash
# Auto-detect remote, reset to default branch
/reset-main

# Reset to specific remote
/reset-main upstream

# Skip dirty state check
/reset-main --force

# Combine remote and force
/reset-main origin -f
```
