# Copilot instructions

## Build, test, and lint commands

This repo has **no repo-level build, test, or lint entrypoint**. It is mostly Markdown plus small validation/automation scripts, so validate the client surface you changed instead of inventing a monorepo-wide task.

- Claude plugin smoke test: `claude --plugin-dir plugins/{plugin-name}/`
- Single-skill smoke run: `claude --plugin-dir plugins/{plugin-name}/ -p "/{skill-name} test args"`
- Copilot package smoke test: `copilot --plugin-dir /absolute/path/to/sai/plugins/{plugin-name}`, then run the relevant slash command in Copilot CLI
- For script-heavy skill changes, run the local checker/schema/smoke flow that belongs to that plugin rather than adding placeholder `mise`, `make`, or lint tasks

## Copilot plugin improvement loop

Use this full loop for behavior changes in `plugins/`, especially `plugins/council/`:

1. Read the current repo docs first: `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and any plugin-local docs you are touching.
2. If you are fixing runtime Copilot behavior, inspect real Copilot session artifacts under `~/.copilot/session-state/` and use unique `VALIDATE_*` tokens in smoke prompts so you can find the right session later.
3. Make the behavior change across the whole surface, not just one file: `skills/.../SKILL.md`, any bundled `agents/*.md` plus their `references/` mandate copies, `plugin.json`, and `README.md` when user-facing behavior changed. Council keeps its Copilot rules in the "Copilot CLI" section of `plugins/council/skills/council/SKILL.md`.
4. The pre-commit hook (`git config core.hooksPath .githooks`) bumps the patch version of every plugin with staged changes; set a minor/major bump by hand in the same commit.
5. Load the local Copilot package with `copilot --plugin-dir /absolute/path/to/sai/plugins/{plugin}` before validating.
6. Use the cheapest practical model for repeated validation and smoke loops (typically `gpt-5-mini`). Only escalate to a stronger model when the issue is genuinely diagnosis-heavy or the cheaper model is failing to make progress.
7. Run long Copilot validations in the background and actively observe them rather than blocking on one giant wrapper. If one case hangs, split validations into separate commands per case.
8. Run Copilot smoke validations from the **real target repository/cwd**, not from `sai`, when behavior depends on surrounding repo context.
9. For council changes, validate the full loop explicitly:
   - normal `/council ...`
   - `/council:council ...` alias behavior
   - broad `/council all ...` approval-stop behavior
   - direct `--agent council:council` failure if that agent is meant to be absent
   - resumed follow-up challenge behavior
10. Use `-s` when you want only the user-visible assistant response in the smoke output. Without it, Copilot CLI includes tool-step narration in stdout.
11. For a real follow-up validation, resume the actual prior session with `copilot --resume=<session-id> -p "..."`. Reusing `--name` alone is not enough to prove follow-up behavior.
12. Inspect `~/.copilot/session-state/<session-id>/events.jsonl` to confirm what actually happened:
    - whether bundled reviewer agents started
    - whether the parent stayed alive after background fan-out
    - whether `read_agent` / `write_agent` supervision happened
    - whether raw reviewer blocks leaked into user-visible assistant output
13. If a validation run stalls, stop only the specific shell session or PID you started; do not use broad kill commands.
14. After validation, commit with a conventional commit, push, and confirm the pushed repo state and the installed plugin version match.

## High-level architecture

- Every plugin is a portable package (`plugins/{plugin}/` with a root Agent Plugins `plugin.json`, `.claude-plugin/plugin.json` and `skills/{skill}/SKILL.md`, for example `plugins/humanize/` and `plugins/kup/`) that serves Claude Code, Codex, Copilot CLI and opencode from one directory; see "Portable plugin layout" in `CONTRIBUTING.md`.
- Plugins with persona agents (for example `plugins/council/`) keep them in `agents/*.md` with identical bodies under `skills/{skill}/references/`, and their root `plugin.json` omits `$schema` so Copilot CLI keeps registering `agents/`.
- Persistent skill state must live outside plugin directories at `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` because plugin cache directories are replaced on update.

## Key conventions

- Exact skill discovery paths matter. Claude will only discover skills at `{plugin-dir}/skills/{skill}/SKILL.md` (`plugins/{plugin}/`).
- Treat `SKILL.md` frontmatter as required in practice: `name`, `description`, `allowed-tools`, and `user-invocable`.
- Keep `SKILL.md` concise and move detailed material into linked `references/` files. Repo skill prompts are typically organized into explicit phases rather than long free-form instructions.
- Plugin versions are bumped by the pre-commit hook in `.githooks/pre-commit` (patch bump, all manifests of a plugin kept in sync). Enable it once with `git config core.hooksPath .githooks`. README-only changes skip the bump.
- Validate via the surface you changed: Claude smoke commands for `claude/`, Copilot install/run flow for `plugins/`, and local checker/schema flows for script-based skills.
- Repo-specific authoring rules live in `.claude/rules/skill-authoring.md` and `.claude/rules/script-authoring-conventions.md`; follow those for new skills and Python-based checker scripts.
- Script defaults in this repo are Python with `#!/usr/bin/env python3`, `from __future__ import annotations`, `pathlib.Path`, deterministic NDJSON output, and explicit exit codes (`0` pass, `1` findings, `2` usage/input errors). Reuse shared helpers such as `_skill_check_common.py` when available.
- When a skill keeps state, update state files only after successful completion.
- Do not edit `.github/workflows/` manually; those workflows are org-synced.
- Do not add inline linter suppressions or relax lint config without explicit approval after exhausting real fixes.
