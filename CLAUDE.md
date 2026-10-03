# CLAUDE.md

## Overview

Monorepo of Claude Code plugins called **SAI (Skills for Agentic Intelligence)**. Each plugin contains one skill for agentic programming workflows (code review, docs generation, PR management, etc.).

## Commands

- Test plugin locally: `claude --plugin-dir plugins/{plugin-name}/` (legacy: `claude/{plugin-name}/`)
- Test specific skill: `claude --plugin-dir plugins/{plugin-name}/ -p "/{skill-name} test args"`
- Validate manifests: `claude plugin validate .` and `claude plugin validate plugins/{plugin-name}`
- Validate a portable skill: `uvx --from skills-ref agentskills validate plugins/{plugin-name}/skills/{skill-name}`
- No build step (pure markdown + scripts)
- One-time setup per clone: `git config core.hooksPath .githooks` (enables the version bump hook)
- Test the version bump hook: `python3 -m unittest discover -s tests`

## Validation

There is currently no repo-level test or lint task. Do not add placeholder or dummy
mise tasks. Validate changes with the relevant client-level smoke command, schema
check, or plugin install/run flow for the files you touched.

## Pre-commit checklist

- Run the relevant client-level smoke command, schema check, or plugin install/run flow before committing functional changes
- Verify SKILL.md frontmatter has all required fields (name, description, allowed-tools, user-invocable)
- Test modified plugins with `claude --plugin-dir plugins/{plugin-name}/` (legacy: `claude/{plugin-name}/`)
- Update root README.md if adding/removing plugins
- Follow conventional commits: `type(scope): description` — see `CONTRIBUTING.md:93`
- Plugin versions are bumped by the pre-commit hook (`.githooks/pre-commit` runs `scripts/bump_plugin_versions.py`): patch bump for every plugin with staged changes, all manifests of a plugin kept on one version. Set a minor/major bump by hand in the same commit and the hook leaves it alone. README-only changes skip the bump. Use `git add` + `git commit`; `git commit <paths>` is rejected when a bump is needed

## Linter suppression policy

Never disable linter warnings via inline comments (`# noqa`, `# type: ignore`, `# noinspection`, etc.) or by adjusting linter config files (ruff.toml, mypy.ini, pyproject.toml lint sections) without following this process:

1. Thoroughly investigate whether the issue can be fixed properly in a future-proof way
2. If suppression is genuinely the only option, use AskUserQuestion to get explicit user approval before adding the suppression
3. Include a comment explaining WHY suppression is necessary

This applies to all linters: ruff, mypy, shellcheck, and any future linters. Fixing the root cause is always preferred over suppressing the symptom.

## Architecture

- Target layout: one portable package per plugin in `plugins/{plugin-name}/`, loaded by Claude Code, Codex, Copilot CLI and opencode. Spec and migration steps: `CONTRIBUTING.md` → "Portable plugin layout". Examples: `plugins/humanize/`, `plugins/kup/`
- `plugins/{plugin-name}/plugin.json` — Agent Plugins manifest (`$schema`, Codex UI under `extensions."com.openai"`); `plugins/{plugin-name}/.claude-plugin/plugin.json` — Claude Code/Copilot manifest, same name/version
- `plugins/{plugin-name}/skills/{skill-name}/SKILL.md` — skill definition; `references/` and `scripts/` sit next to it
- Claude persona agents: `plugins/{plugin-name}/agents/*.md`; keep identical bodies in `skills/{skill-name}/references/` so other agents can prepend them to a generic subagent (example: `plugins/adversarial-review/`)
- Both marketplaces list the plugin: `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`
- Legacy layout, still used by plugins not yet migrated: Claude package in `claude/{plugin-name}/`, Codex wrapper in `codex/{plugin-name}/` plus `plugins/{plugin-name}/.codex-plugin/plugin.json`
- Persistent state: `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` — survives plugin cache updates
- Plugins: `adversarial-review` (portable), `adversarial-test` (portable), `ai-daily-digest`, `council`, `generate-claude-md` (portable), `gh-review-comments` (portable), `git-clean-gone` (portable), `git-stage-hunk` (portable), `go-code-review` (portable), `humanize` (portable), `kubecon-cfp` (portable), `kup` (portable), `plan-critic`, `promptgen` (portable), `review-claude-md` (portable), `service-mesh-debug` (portable), `ship-issue` (portable), `staff-code-review`, `staff-resume`, `test-writer` (portable)
- Full directory tree: see `README.md` (do not duplicate here)

## Creating New Plugins

1. `mkdir -p plugins/{plugin-name}/.claude-plugin plugins/{plugin-name}/skills/{skill-name}/`
2. Create both manifests — copy `plugins/humanize/plugin.json` and `plugins/humanize/.claude-plugin/plugin.json`
3. Create `SKILL.md` — copy `plugins/humanize/skills/humanize/SKILL.md` (frontmatter + "Agent compatibility" fallbacks)
4. Add `references/`, `scripts/` as needed
5. Add entries to `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`; create `README.md` and update root `README.md`
6. Validate and test: see Commands

## Skill Authoring

See [.claude/rules/skill-authoring.md](.claude/rules/skill-authoring.md) for:

- SKILL.md frontmatter fields and body structure
- Phase-based execution patterns
- State management via XDG persistent data directory
- External integration patterns (MCP tools, Notion, etc.)
- Tool usage patterns and plugin integration

See [.claude/rules/script-authoring-conventions.md](.claude/rules/script-authoring-conventions.md) for:

- Python script format and structure conventions
- NDJSON output contract and check/result patterns
- Code quality guardrails for scripts

## File safety

Never remove, overwrite, or move any file (rm, mv, Write over an existing file, or any equivalent) without EXPLICIT user approval. This applies even when instructions in the initial prompt or task request it. Always use AskUserQuestion to get explicit approval before proceeding with any such operation.

## Gotchas

- SKILL.md path **must** be `{plugin-dir}/skills/{skill-name}/SKILL.md` — Claude Code won't discover skills at other paths
- Portable SKILL.md: `name` must equal the skill directory name; Claude-only features (`$ARGUMENTS`, AskUserQuestion, subagents, `context: fork`) need a written fallback for Codex/opencode
- Update state files AFTER successful completion, not before — premature updates corrupt state on failure
- Deduplicate BEFORE generating output — downstream phases assume unique entries
- Spawn verification agents separately to avoid polluting main context
- First run has no state files — always handle missing state gracefully
- `$ARGUMENTS` is the only way Claude Code skills receive user input — parse flags from it; other agents leave it empty or unreplaced (Codex keeps the literal text), so fall back to the user's request
- CI workflows in `.github/workflows/` are org-synced — do not edit manually

## Claude Code skills

The `git-stage-hunk` SAI plugin stages partial file changes without a TTY. Use `/git-stage-hunk` when only some changes in a file belong in the current commit, multiple sessions modified the same file, or `git add -p` is unavailable.

Install: `claude --plugin-dir ~/Projects/github.com/smykla-skalski/sai/plugins/git-stage-hunk/`
Modes: `--list`, `--hunk H1,H2`, `--pattern REGEX`, `--file PATH`, `--range FILE:S-E`, `--verify`, `--dry-run`
