---
name: worktree
description: Create git worktree with context transfer. Use ONLY when the user explicitly asks for a worktree - never infer this from generic branch or PR requests. Handles conventional branch naming, IDE detection, symlinks for context files, and clipboard setup.
argument-hint: "<task-description> [--quick] [--no-pbcopy] [--no-ide] [--ide <name>]"
allowed-tools: Bash, AskUserQuestion
user-invocable: true
---

# Worktree

Create a git worktree with context transfer — symlinks for config files, git excludes, IDE detection, and clipboard integration.

## Arguments

Parse from `$ARGUMENTS`:

| Flag           | Default     | Purpose                                        |
|:---------------|:------------|:-----------------------------------------------|
| (positional)   | —           | Task description for branch naming             |
| `--quick`      | off         | Skip questions, use sensible defaults          |
| `--no-pbcopy`  | off         | Skip clipboard copy                            |
| `--no-ide`     | off         | Disable IDE detection                          |
| `--ide <name>` | auto-detect | Override IDE (goland, pycharm, webstorm, etc.) |

## Constraints

- **CRITICAL: ALWAYS use `bash -c '...'`** — NEVER execute scripts directly
- NEVER create worktree without confirming branch name (unless `--quick`)
- NEVER assume remote or default branch — detect explicitly
- Check for uncommitted changes before creating worktree (unless `--quick`)
- ZERO single quotes inside scripts — scripts wrapped in `bash -c '...'`
- ZERO tolerance for data loss — handle uncommitted changes explicitly

## Workflow

### Phase 1: Gather Context

Run these bash commands to collect state:

```bash
pwd
git status --porcelain
git remote -v
git branch --show-current
ls go.mod Cargo.toml pyproject.toml setup.py pom.xml build.gradle build.gradle.kts Gemfile composer.json CMakeLists.txt tsconfig.json package.json requirements.txt 2>/dev/null | tr '\n' ' '
```

### Phase 2: Select Mode

**Quick mode** (no questions) when:

- `--quick` flag present, OR
- Task description has 4+ words AND no ambiguous phrases

**Full mode** (may ask questions) when:

- Task is short (< 4 words)
- Contains ambiguous phrases: "work on", "make changes", "do something", "changes to", "update something"
- No task description provided

### Phase 3: Determine Parameters

**Remote:** prefer `upstream`, fall back to `origin`.

**Branch type** — detect from task description:

| Keywords                    | Prefix                          |
|:----------------------------|:--------------------------------|
| add, implement, new, create | `feat/`                         |
| fix, resolve, patch, bug    | `fix/`                          |
| update, upgrade, deps, bump | `chore/`                        |
| document, readme, guide     | `docs/`                         |
| test, spec, coverage        | `test/`                         |
| refactor, reorganize, clean | `refactor/`                     |
| ci, pipeline, workflow      | `ci/`                           |
| build, tooling, compile     | `build/`                        |
| unclear                     | Quick: `chore/`. Full: ask user |

**Branch slug:** lowercase, hyphens, max 50 chars from task description.

**IDE detection:** Read `references/ide-detection.md` in full before evaluating.

- `--no-ide` → skip
- `--ide <name>` → use specified IDE
- Otherwise → auto-detect from project config files

### Phase 4: Validate Pre-conditions (Full Mode Only)

Skip all validation if `--quick`.

1. If git status shows uncommitted changes → AskUserQuestion: commit, stash, or abort
2. If branch type unclear → AskUserQuestion with conventional commit options
3. If multiple Tier 1 IDE config files → AskUserQuestion for IDE selection

### Phase 5: Generate and Execute Script

Read `references/script-template.md` in full before generating the script.

Fill in the template variables:

- `R` — Remote name
- `B` — Branch name (prefix/slug)
- `S` — Source path (current directory)
- `W` — Worktree path (`{source}-{prefix}-{slug}`)
- `P` — `1` for pbcopy or empty for no pbcopy
- `I` — IDE name or empty for no IDE

Execute with `bash -c '{filled-script}'`.

If execution fails: diagnose error, attempt fix, retry once.

### Phase 6: Report Results

Output worktree creation summary:

- Branch name and path
- Tracking remote/branch
- Symlinked files
- Clipboard status and IDE

## Notes

- Only untracked/ignored files are symlinked: `.claude/`, `.klaudiush/`, `tmp/`, `.envrc`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.gemini*`
- Tracked files already exist in worktree after `git worktree add`
- Script checks `git ls-files` before each symlink
- Worktree-specific git excludes configured automatically
- If branch name exists, append `-2`, `-3`, etc.
- Clipboard contains `<ide> <path>; cd <path> && mise trust && direnv allow` (or without IDE prefix)

## Example Invocations

```bash
# Create worktree for a feature
/worktree implement retry logic for API calls

# Quick mode - no questions, sensible defaults
/worktree --quick fix login validation bug

# Without clipboard
/worktree add caching layer --no-pbcopy

# Specific IDE override
/worktree refactor auth module --ide webstorm

# No IDE detection
/worktree update dependencies --no-ide
```
