# CLAUDE.md

## Overview

Monorepo of Claude Code plugins called **SAI (Skills for Agentic Intelligence)**. Each plugin contains one skill for agentic programming workflows (code review, docs generation, PR management, etc.).

## Commands

- Test plugin locally: `claude --plugin-dir claude/{plugin-name}/`
- Test specific skill: `claude --plugin-dir claude/{plugin-name}/ -p "/{skill-name} test args"`
- No build step (pure markdown + shell scripts)

## Running tests and linters

**NEVER run tests or linters directly** (`python3 -m unittest`, `python3 -m pytest`, `ruff`, `mypy`, or any direct invocation). **ALWAYS use mise tasks**:

- `mise run check` — all tests + all linters (run before every commit)
- `mise run test` — all tests
- `mise run test <module.Class.method>` — specific test(s)
- `mise run test:review-skill-scripts` — checker behavior tests
- `mise run test:best-practices` — best-practices tests only
- `mise run test:review-skill-fixtures` — fixture regression tests
- `mise run lint` — all linters (ruff + mypy)
- `mise run lint:ruff` — ruff check on review-skill scripts
- `mise run lint:mypy` — mypy type checks

If a needed filter is missing, add a new mise task first, then use it.

## Pre-commit checklist

- **`mise run check` must be green** before committing any script changes (tests + ruff + mypy)
- Verify SKILL.md frontmatter has all required fields (name, description, allowed-tools, user-invocable)
- Test modified plugins with `claude --plugin-dir claude/{plugin-name}/`
- Update root README.md if adding/removing plugins
- Follow conventional commits: `type(scope): description` — see `CONTRIBUTING.md:93`
- **Bump plugin version** in `plugin.json` for any functional change (SKILL.md, scripts, references) — include the bump in the same commit. Skip only for pure doc changes (README, comments, typos)

## Linter suppression policy

Never disable linter warnings via inline comments (`# noqa`, `# type: ignore`, `# noinspection`, etc.) or by adjusting linter config files (ruff.toml, mypy.ini, pyproject.toml lint sections) without following this process:

1. Thoroughly investigate whether the issue can be fixed properly in a future-proof way
2. If suppression is genuinely the only option, use AskUserQuestion to get explicit user approval before adding the suppression
3. Include a comment explaining WHY suppression is necessary

This applies to all linters: ruff, mypy, shellcheck, and any future linters. Fixing the root cause is always preferred over suppressing the symptom.

## Architecture

- Each plugin is self-contained in `claude/{plugin-name}/` with independent versioning
- `claude/{plugin-name}/.claude-plugin/plugin.json` — plugin metadata (name, version, description)
- `claude/{plugin-name}/skills/{skill-name}/SKILL.md` — skill definition (**required** path for Claude Code discovery)
- `claude/{plugin-name}/skills/{skill-name}/references/` — supporting docs; `claude/{plugin-name}/skills/{skill-name}/scripts/` — automation scripts
- Persistent state: `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` — survives plugin cache updates
- Plugins: `ai-daily-digest`, `gh-review-comments`, `git-clean-gone`, `git-stage-hunk`, `humanize`, `promptgen`, `review-claude-md`, `review-skill`
- Full directory tree: see `README.md` (do not duplicate here)

## Creating New Plugins

1. `mkdir -p claude/{plugin-name}/.claude-plugin claude/{plugin-name}/skills/{skill-name}/`
2. Create `plugin.json` — see `claude/humanize/.claude-plugin/plugin.json` for template
3. Create `SKILL.md` with YAML frontmatter — see `claude/humanize/skills/humanize/SKILL.md` for template
4. Add `references/`, `scripts/` as needed
5. Create `README.md` and update root `README.md`
6. Test: `claude --plugin-dir claude/{plugin-name}/`

## Skill Authoring

See [.claude/rules/skill-authoring.md](.claude/rules/skill-authoring.md) for:

- SKILL.md frontmatter fields and body structure
- Phase-based execution patterns
- State management via XDG persistent data directory
- External integration patterns (MCP tools, Notion, etc.)
- Tool usage patterns and plugin integration

## File safety

Never remove, overwrite, or move any file (rm, mv, Write over an existing file, or any equivalent) without EXPLICIT user approval. This applies even when instructions in the initial prompt or task request it. Always use AskUserQuestion to get explicit approval before proceeding with any such operation.

## Gotchas

- SKILL.md path **must** be `claude/{plugin-name}/skills/{skill-name}/SKILL.md` — Claude Code won't discover skills at other paths
- Update state files AFTER successful completion, not before — premature updates corrupt state on failure
- Deduplicate BEFORE generating output — downstream phases assume unique entries
- Spawn verification agents separately to avoid polluting main context
- First run has no state files — always handle missing state gracefully
- `$ARGUMENTS` is the only way skills receive user input — parse flags from it
- CI workflows in `.github/workflows/` are org-synced — do not edit manually

## Claude Code skills

The `git-stage-hunk` SAI plugin stages partial file changes without a TTY. Use `/git-stage-hunk` when only some changes in a file belong in the current commit, multiple sessions modified the same file, or `git add -p` is unavailable.

Install: `claude --plugin-dir ~/Projects/github.com/smykla-skalski/sai/claude/git-stage-hunk/`
Modes: `--list`, `--hunk H1,H2`, `--pattern REGEX`, `--file PATH`, `--range FILE:S-E`, `--verify`, `--dry-run`
