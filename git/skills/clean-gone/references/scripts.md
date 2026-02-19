# Cleanup Scripts

CRITICAL: All scripts use `bash -c '...'` format for atomic execution.

## Default (Full Cleanup)

Deletes branches that are gone OR merged (via squash/rebase), removes associated worktrees.

```bash
bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); merged_prs=""; command -v gh &>/dev/null && merged_prs=$(gh pr list --state merged --limit 200 --json headRefName --jq ".[].headRefName" 2>/dev/null | tr "\n" "|"); git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "false" ] && [ -n "$merged_prs" ] && echo "|${merged_prs}" | grep -q "|${branch}|"; then delete=true; reason="squash-merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && git worktree remove --force "$wt" 2>/dev/null && echo "REMOVED_WT:$(basename "$wt"):$branch"; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "KEPT_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "KEPT:$branch:$unmerged unmerged"; fi; done'
```

## Dry Run (Preview Only)

Same logic as default but uses `WOULD_*` prefixes and makes no changes.

```bash
bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; remote=$(git for-each-ref --format="%(upstream:remotename)" refs/heads/main 2>/dev/null); [ -z "$remote" ] && remote=$(git remote | head -1); main=$(git symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | sed "s@^refs/remotes/$remote/@@"); [ -z "$main" ] && main="main"; tl=$(git rev-parse --show-toplevel); current=$(git branch --show-current); merged_prs=""; command -v gh &>/dev/null && merged_prs=$(gh pr list --state merged --limit 200 --json headRefName --jq ".[].headRefName" 2>/dev/null | tr "\n" "|"); git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | while read -r branch track; do [ "$branch" = "$main" ] && continue; [ "$branch" = "$current" ] && echo "WOULD_SKIP:$branch:current branch" && continue; delete=false; reason=""; case "$track" in *"[gone]"*) delete=true; reason="gone";; esac; if [ "$delete" = "false" ]; then unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ "$unmerged" -eq 0 ] 2>/dev/null && delete=true && reason="merged"; fi; if [ "$delete" = "false" ] && [ -n "$merged_prs" ] && echo "|${merged_prs}" | grep -q "|${branch}|"; then delete=true; reason="squash-merged"; fi; if [ "$delete" = "true" ]; then wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_REMOVE_WT:$(basename "$wt"):$branch"; echo "WOULD_DELETE:$branch:$reason"; else wt=$(git worktree list | awk -v b="[$branch]" "index(\$0, b) {print \$1}"); unmerged=$(git cherry "$remote/$main" "$branch" 2>/dev/null | grep -c "^+" || :); [ -n "$wt" ] && [ "$wt" != "$tl" ] && echo "WOULD_KEEP_WT:$(basename "$wt"):$branch:$unmerged unmerged" || echo "WOULD_KEEP:$branch:$unmerged unmerged"; fi; done'
```

## No Worktrees (Gone Branches Only)

Only deletes branches with `[gone]` tracking, no worktree removal, no merge detection.

```bash
bash -c 'git fetch --prune --all 2>&1 | grep -v "^From\|^   \|^ \*\|^ +\|^ -" || :; git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads | awk "/\[gone\]/ {print \$1}" | while read -r branch; do current=$(git branch --show-current); [ "$branch" = "$current" ] && echo "SKIPPED:$branch:current branch" && continue; git branch -D "$branch" >/dev/null 2>&1 && echo "DELETED:$branch:gone"; done'
```
