# Worktree Creation Script Template

## Variables

| Variable | Description                | Example                                                |
|:---------|:---------------------------|:-------------------------------------------------------|
| `R`      | Remote name                | `upstream`                                             |
| `B`      | Branch name                | `feat/implement-retry-logic`                           |
| `S`      | Source path (current dir)  | `/Users/dev/projects/myapp`                            |
| `W`      | Worktree path              | `/Users/dev/projects/myapp-feat-implement-retry-logic` |
| `P`      | Pbcopy flag (`1` or empty) | `1`                                                    |
| `I`      | IDE name (or empty)        | `goland`                                               |

## Worktree Path Convention

`{source-dir}-{branch-prefix}-{slug}` — e.g., `/Users/dev/myapp-feat-retry-logic`

## Script

CRITICAL: Zero single quotes — scripts are wrapped in `bash -c '...'`.

```bash
set -euo pipefail; R="{remote}"; B="{prefix}/{slug}"; S="{source}"; W="{worktree}"; P="{1|}"; I="{ide|}"; git fetch "$R"; D=$(git remote show "$R" 2>/dev/null | grep "HEAD branch" | awk "{print \$NF}"); [ -z "$D" ] && D="main"; git worktree add -b "$B" "$W" "$R/$D"; git -C "$W" config extensions.worktreeConfig true; E=$(git -C "$W" rev-parse --git-path info/exclude); mkdir -p "$(dirname "$E")"; not_tracked() { [ -z "$(git ls-files "$1" 2>/dev/null)" ]; }; X=""; [ -e "$S/.claude" ] && not_tracked ".claude" && ln -sfn "$S/.claude" "$W/.claude" && X="$X .claude"; [ -e "$S/.klaudiush" ] && not_tracked ".klaudiush" && ln -sfn "$S/.klaudiush" "$W/.klaudiush" && X="$X .klaudiush"; [ -e "$S/tmp" ] && not_tracked "tmp" && ln -sfn "$S/tmp" "$W/tmp" && X="$X tmp"; [ -e "$S/.envrc" ] && not_tracked ".envrc" && ln -sf "$S/.envrc" "$W/.envrc" && X="$X .envrc"; [ -e "$S/CLAUDE.md" ] && not_tracked "CLAUDE.md" && ln -sf "$S/CLAUDE.md" "$W/CLAUDE.md" && X="$X CLAUDE.md"; [ -e "$S/AGENTS.md" ] && not_tracked "AGENTS.md" && ln -sf "$S/AGENTS.md" "$W/AGENTS.md" && X="$X AGENTS.md"; [ -e "$S/GEMINI.md" ] && not_tracked "GEMINI.md" && ln -sf "$S/GEMINI.md" "$W/GEMINI.md" && X="$X GEMINI.md"; for f in "$S"/.gemini*; do n=$(basename "$f"); [ -e "$f" ] && not_tracked "$n" && ln -sf "$f" "$W/$n" && X="$X $n"; done 2>/dev/null || true; for i in $X; do echo "$i"; done > "$E"; git -C "$W" config --worktree core.excludesFile "$E"; [ -n "$P" ] && { [ -n "$I" ] && printf "%s" "$I $W; cd $W && mise trust && direnv allow" || printf "%s" "cd $W && mise trust && direnv allow"; } | pbcopy; echo "=== RESULT ==="; echo "BRANCH=$B"; echo "PATH=$W"; echo "TRACKING=$R/$D"; echo "SYMLINKED=$X"; echo "PBCOPY=$P"; echo "IDE=$I"
```

## What the Script Does

1. Fetch latest from remote
2. Detect default branch from remote HEAD
3. Create worktree with new branch tracking remote/default
4. Enable worktree-specific config
5. Symlink untracked context files (`.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`)
6. Configure git excludes for symlinked files
7. Copy cd command to clipboard (with IDE prefix if detected)
8. Output structured result

## Symlink Rules

- Directories (`.claude/`, `.klaudiush/`, `tmp/`): use `ln -sfn` (no-dereference)
- Files (`.envrc`, `CLAUDE.md`, etc.): use `ln -sf`
- Only symlink untracked/ignored files — check `git ls-files` first
- Tracked files already exist in worktree from `git worktree add`

## Output Parsing

Script outputs `=== RESULT ===` followed by key=value lines:

- `BRANCH=feat/slug`
- `PATH=/absolute/worktree/path`
- `TRACKING=remote/main`
- `SYMLINKED=.claude .envrc CLAUDE.md`
- `PBCOPY=1` or `PBCOPY=`
- `IDE=goland` or `IDE=`
