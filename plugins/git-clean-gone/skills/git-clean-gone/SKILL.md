---
name: git-clean-gone
description: Clean up local branches with deleted remote tracking and their worktrees. Use after merging PRs to remove stale branches, detect squash-merged and rebased branches, and clean up associated worktrees.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs bash and git; the gh CLI is optional (squash-merge detection). Fetches from all remotes.
argument-hint: "[--dry-run] [--no-worktrees]"
allowed-tools: Bash
user-invocable: true
disable-model-invocation: true
metadata:
  short-description: Clean stale local branches safely
---

# Clean Gone

Delete local branches whose remote tracking is gone or merged, and remove their associated worktrees.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the flags from the user's request |
| Skill directory substitution | If the script path under Constraints is not an absolute path, run `bash <absolute skill directory>/scripts/clean-gone.sh` without changing directory. The script acts on the repository in the current working directory, so that must stay the user's repository, never the skill directory |
| Preprocessed context | If the values under Preprocessed context are unexpanded commands, ignore them: the script detects the remote, default branch and `gh` itself |
| `disable-model-invocation` | This skill deletes branches and worktrees and is meant to run only when the user invokes it by name. Codex enforces this through `agents/openai.yaml` (`allow_implicit_invocation: false`); where nothing enforces it (for example opencode), apply the confirmation gate below |
| AskUserQuestion, subagents, `context: fork` | Not used |

Confirmation gate on agents other than Claude Code: run the real cleanup directly only when the user invoked this skill by name (`/git-clean-gone` or `$git-clean-gone`) without `--dry-run` and without exclusions or conditions (such as "but keep feat/x"). In every other case, including plain requests such as "clean up stale branches", run with `--dry-run` first, show the preview, then end your turn and wait for the user's reply. Never run the real cleanup in the same turn as the preview; only an explicit yes in a later user message allows it. Approval is all-or-nothing: the script cannot skip individual branches, so if the user wants to keep any listed branch or worktree, stop and do not run the real cleanup. The real run fetches again, so after it, compare its `DELETED`/`REMOVED_WT` lines with the preview and call out every branch or worktree that was not in the preview. In Claude Code, invoking `/git-clean-gone` without `--dry-run` is that explicit request.

In Codex, `git fetch --prune` and `gh` need network access and the deletions write to `.git`, so run the script with escalation and a short reason from the start, for the `--dry-run` preview as well as the real run. A preview without network silently misses gone and squash-merged branches. If the output has a `fatal:` or `error:` line from `git fetch`, the fetch failed: report it and do not run the real cleanup.

## Arguments

Parse from `$ARGUMENTS`:

| Flag | Default | Purpose |
| :-- | :-- | :-- |
| (none) | — | Full cleanup: gone + merged branches + worktrees |
| `--dry-run` | off | Preview only, no changes |
| `--no-worktrees` | off | Branches only, skip worktree removal |

## Preprocessed context

- Default remote: !`git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null || git remote | head -1 2>/dev/null || echo "origin"`
- Default branch: !`basename "$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null || echo refs/remotes/origin/main)"`
- gh CLI: !`command -v gh >/dev/null 2>&1 && echo "available" || echo "unavailable"`

## Constraints

- First action MUST be Bash — preamble text wastes a turn and delays the actual cleanup
- Never delete the current branch — skip and report in summary
- Never remove the main worktree — only feature/task worktrees
- Execute `"${CLAUDE_SKILL_DIR}/scripts/clean-gone.sh"` as a single Bash invocation
- Output summary directly as text (NOT via bash/printf)
- Agents other than Claude Code: follow the confirmation gate in [Agent compatibility](#agent-compatibility); a `--dry-run` preview always ends the turn

## Workflow

### Phase 1: Execute Cleanup Script

Execute `"${CLAUDE_SKILL_DIR}/scripts/clean-gone.sh"` immediately, passing through any flags from `$ARGUMENTS`. On agents other than Claude Code, apply the confirmation gate from [Agent compatibility](#agent-compatibility) first.

- No flags → full cleanup (gone + merged branches + worktrees)
- `--dry-run` → preview only, no changes
- `--no-worktrees` → gone branches only, no worktree removal or merge detection
- Invalid flag → script exits with error, show valid options (`--dry-run`, `--no-worktrees`), stop

### Phase 2: Output Summary

Parse script output line prefixes and render formatted summary directly as text.

**Line prefixes** (from script output):

| Prefix | Meaning |
| :-- | :-- |
| `DELETED:branch:reason` | Deleted branch |
| `REMOVED_WT:worktree:branch` | Removed worktree |
| `SKIPPED:branch:reason` | Skipped branch |
| `KEPT:branch:reason` | Kept branch |
| `KEPT_WT:worktree:branch:reason` | Kept worktree |

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

- Uses pre-resolved remote name and default branch from preprocessed context
- Deletes branches marked `[gone]` (remote tracking deleted)
- Deletes branches fully merged via rebase/cherry-pick (`git cherry`)
- Deletes branches squash-merged via PR (`gh pr list --state merged`) when gh CLI is available
- Removes associated worktrees before branch deletion
- Skips main and current branch
- Falls back gracefully if gh CLI is unavailable (see preprocessed context)

## Edge Cases

- Invalid flags: report unknown flag, show valid options, stop
- No cleanable branches: report "Repository already clean"
- Current branch is gone/merged: skip deletion, warn in summary
- Uncommitted changes in worktree: force remove with `--force` flag
- No `gh` CLI (see preprocessed context): squash merges won't be detected, only `git cherry` used
- No remote configured: remote from preprocessed context used as fallback

## Example Invocations

<example>
Full cleanup:

```bash
/git-clean-gone
```
</example>

<example>
Preview what would be deleted:

```bash
/git-clean-gone --dry-run
```
</example>

<example>
Branches only, no worktree removal:

```bash
/git-clean-gone --no-worktrees
```
</example>
