#!/usr/bin/env bash
# clean-gone.sh — Clean up local branches with deleted remote tracking and their worktrees.
#
# Usage:
#   ./clean-gone.sh [--dry-run] [--no-worktrees]
#
# Flags:
#   --dry-run       Preview only, no changes (WOULD_* prefixes)
#   --no-worktrees  Delete gone branches only, skip worktree removal and merge detection
#
# Output: One line per branch with structured prefixes:
#   DELETED:branch:reason          — Deleted branch (reason: gone, merged, squash-merged)
#   REMOVED_WT:worktree:branch     — Removed worktree
#   SKIPPED:branch:reason          — Skipped branch (e.g., current branch)
#   KEPT:branch:reason             — Kept branch with reason
#   KEPT_WT:worktree:branch:reason — Kept branch that has a worktree
#
# Dry-run output uses WOULD_DELETE, WOULD_REMOVE_WT, WOULD_SKIP, WOULD_KEEP, WOULD_KEEP_WT.
#
# Dependencies: git, gh (optional, for squash-merge detection)
set -uo pipefail

# ========================
# ARGUMENT PARSING
# ========================
DRY_RUN=false
NO_WORKTREES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --no-worktrees)
      NO_WORKTREES=true
      shift
      ;;
    *)
      echo "ERROR:unknown-flag:$1" >&2
      exit 1
      ;;
  esac
done

# ========================
# HELPERS
# ========================

# Emit a structured output line, mapping base action to correct tense.
# Usage: emit <action> <colon-separated-fields>
# Actions: DELETE, REMOVE_WT, SKIP, KEEP, KEEP_WT
emit() {
  local action="$1"
  shift
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "WOULD_${action}:$*"
  else
    # Map base form to past tense for actual output
    case "$action" in
      DELETE)    echo "DELETED:$*" ;;
      REMOVE_WT) echo "REMOVED_WT:$*" ;;
      SKIP)      echo "SKIPPED:$*" ;;
      KEEP)      echo "KEPT:$*" ;;
      KEEP_WT)   echo "KEPT_WT:$*" ;;
      *)         echo "${action}:$*" ;;
    esac
  fi
}

# ========================
# SETUP
# ========================

# Fetch and prune all remotes (suppress noisy output)
git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :

current=$(git branch --show-current)

# ========================
# NO-WORKTREES MODE (simplified: gone branches only)
# ========================
if [[ "$NO_WORKTREES" == "true" ]]; then
  git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads \
    | awk '/\[gone\]/ {print $1}' \
    | while read -r branch; do
        [[ "$branch" == "$current" ]] && emit "SKIP" "$branch:current branch" && continue
        if [[ "$DRY_RUN" == "true" ]]; then
          emit "DELETE" "$branch:gone"
        else
          git branch -D "$branch" >/dev/null 2>&1 && emit "DELETE" "$branch:gone"
        fi
      done
  exit 0
fi

# ========================
# FULL CLEANUP MODE
# ========================

# Detect remote from main branch's upstream
remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null)
[[ -z "$remote" ]] && remote=$(git remote | head -1)

# Detect default branch name
main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@")
[[ -z "$main" ]] && main="main"

tl=$(git rev-parse --show-toplevel)

# Detect squash-merged PRs via gh CLI (if available)
merged_prs=""
if command -v gh &>/dev/null; then
  merged_prs=$(gh pr list --state merged --limit 200 --json headRefName --jq ".[].headRefName" 2>/dev/null | tr "\n" "|")
fi

# Process each branch
git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do
  [[ "$branch" == "$main" ]] && continue
  [[ "$branch" == "$current" ]] && emit "SKIP" "$branch:current branch" && continue

  delete=false
  reason=""

  # Check if remote tracking is gone
  case "$track" in
    *"[gone]"*) delete=true; reason="gone" ;;
  esac

  # Check if fully merged via cherry-pick/rebase
  if [[ "$delete" == "false" ]]; then
    unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :)
    [[ "$unmerged" -eq 0 ]] 2>/dev/null && delete=true && reason="merged"
  fi

  # Check if squash-merged via PR
  if [[ "$delete" == "false" ]] && [[ -n "$merged_prs" ]] && echo "|${merged_prs}" | grep -q "|${branch}|"; then
    delete=true
    reason="squash-merged"
  fi

  if [[ "$delete" == "true" ]]; then
    # Handle associated worktree
    wt=$(git worktree list | awk -v b="[$branch]" 'index($0, b) {print $1}')
    if [[ -n "$wt" ]] && [[ "$wt" != "$tl" ]]; then
      if [[ "$DRY_RUN" == "true" ]]; then
        emit "REMOVE_WT" "$(basename "$wt"):$branch"
      else
        git worktree remove --force "$wt" 2>/dev/null && emit "REMOVE_WT" "$(basename "$wt"):$branch"
      fi
    fi
    # Delete branch
    if [[ "$DRY_RUN" == "true" ]]; then
      emit "DELETE" "$branch:$reason"
    else
      git branch -D "$branch" >/dev/null 2>&1 && emit "DELETE" "$branch:$reason"
    fi
  else
    wt=$(git worktree list | awk -v b="[$branch]" 'index($0, b) {print $1}')
    unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :)
    if [[ -n "$wt" ]] && [[ "$wt" != "$tl" ]]; then
      emit "KEEP_WT" "$(basename "$wt"):$branch:$unmerged unmerged"
    else
      emit "KEEP" "$branch:$unmerged unmerged"
    fi
  fi
done
