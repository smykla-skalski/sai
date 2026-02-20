# CLAUDE.md

## Overview

Monorepo of Claude Code plugins called **SAI (Skills for Agentic Intelligence)**. Each plugin contains one skill for agentic programming workflows (code review, docs generation, PR management, etc.).

## Commands

- Test plugin locally: `claude --plugin-dir {plugin-name}/`
- Test specific skill: `claude --plugin-dir {plugin-name}/ -p "/{skill-name} test args"`
- No build step (pure markdown + shell scripts)
- No lint step (no linter configured)

## Pre-commit Checklist

- Verify SKILL.md frontmatter has all required fields (name, description, allowed-tools, user-invocable)
- Test modified plugins with `claude --plugin-dir {plugin-name}/`
- Update root README.md if adding/removing plugins
- Follow conventional commits: `type(scope): description` — see `CONTRIBUTING.md:93`
- **Bump plugin version** in `plugin.json` for any functional change (SKILL.md, scripts, references) — include the bump in the same commit. Skip only for pure doc changes (README, comments, typos)

## Architecture

- Each plugin is self-contained in `{plugin-name}/` with independent versioning
- `{plugin-name}/.claude-plugin/plugin.json` — plugin metadata (name, version, description)
- `{plugin-name}/skills/{skill-name}/SKILL.md` — skill definition (**required** path for Claude Code discovery)
- `{plugin-name}/skills/{skill-name}/references/` — supporting docs; `{plugin-name}/skills/{skill-name}/scripts/` — automation scripts
- Persistent state: `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` — survives plugin cache updates
- Plugins: `ai-daily-digest`, `gh-review-comments`, `git`, `humanize`, `review-claude-md`, `review-skill`
- Full directory tree: see `README.md` (do not duplicate here)

## Creating New Plugins

1. `mkdir -p {plugin-name}/.claude-plugin {plugin-name}/skills/{skill-name}/`
2. Create `plugin.json` — see `humanize/.claude-plugin/plugin.json` for template
3. Create `SKILL.md` with YAML frontmatter — see `humanize/skills/humanize/SKILL.md` for template
4. Add `references/`, `scripts/` as needed
5. Create `README.md` and update root `README.md`
6. Test: `claude --plugin-dir {plugin-name}/`

## Skill Authoring

See `.claude/rules/skill-authoring.md` for:

- SKILL.md frontmatter fields and body structure
- Phase-based execution patterns
- State management via XDG persistent data directory
- External integration patterns (MCP tools, Notion, etc.)
- Tool usage patterns and plugin integration

## Gotchas

- SKILL.md path **must** be `{plugin-name}/skills/{skill-name}/SKILL.md` — Claude Code won't discover skills at other paths
- Update state files AFTER successful completion, not before — premature updates corrupt state on failure
- Deduplicate BEFORE generating output — downstream phases assume unique entries
- Spawn verification agents separately to avoid polluting main context
- First run has no state files — always handle missing state gracefully
- `$ARGUMENTS` is the only way skills receive user input — parse flags from it
- CI workflows in `.github/workflows/` are org-synced — do not edit manually
