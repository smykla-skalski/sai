# Copilot instructions

## Build, test, and lint commands

This repo has **no repo-level build, test, or lint entrypoint**. It is mostly Markdown plus small validation/automation scripts, so validate the client surface you changed instead of inventing a monorepo-wide task.

- Claude plugin smoke test: `claude --plugin-dir claude/{plugin-name}/`
- Single-skill smoke run: `claude --plugin-dir claude/{plugin-name}/ -p "/{skill-name} test args"`
- Copilot package smoke test: use `copilot --plugin-dir /absolute/path/to/sai/claude/{plugin-name}` for the self-contained plugin packages under `claude/`, or `copilot --plugin-dir /absolute/path/to/sai/plugins/council` for council's dedicated bundle, then run the relevant slash command in Copilot CLI
- For script-heavy skill changes, run the local checker/schema/smoke flow that belongs to that plugin rather than adding placeholder `mise`, `make`, or lint tasks

## Copilot plugin improvement loop

Use this full loop for behavior changes in `plugins/`, especially `plugins/council/`:

1. Read the current repo docs first: `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and any plugin-local docs you are touching.
2. If you are fixing runtime Copilot behavior, inspect real Copilot session artifacts under `~/.copilot/session-state/` and use unique `VALIDATE_*` tokens in smoke prompts so you can find the right session later.
3. Make the behavior change across the whole surface, not just one file: `copilot-skills/.../SKILL.md`, any bundled `agents/*.agent.md`, `plugin.json`, and `README.md` when user-facing behavior changed.
4. For any functional plugin change, bump that plugin’s `plugin.json` version in the same change.
5. Load the local Copilot package with `copilot --plugin-dir /absolute/path/to/sai/claude/{plugin}` for the self-contained plugin packages, or `copilot --plugin-dir /absolute/path/to/sai/plugins/{plugin}` when a dedicated bundle exists, before validating.
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

- The repo has three delivery surfaces:
  - `claude/` contains self-contained plugin packages for Claude Code and Copilot CLI marketplace installs
  - `plugins/` contains Codex-compatible packages and special multi-surface bundles such as `plugins/council/`
  - `codex/` contains Codex skills and shared native agent definitions
- Claude plugins are self-contained and use a strict discovery layout:
  - `claude/{plugin}/.claude-plugin/plugin.json`
  - `claude/{plugin}/skills/{skill}/SKILL.md`
  - `claude/{plugin}/skills/{skill}/references/`
  - `claude/{plugin}/skills/{skill}/scripts/`
- Copilot packages use a different shape. For example, `plugins/council/` keeps:
  - `plugin.json` for package metadata and versioning
  - `copilot-skills/` for slash-command entrypoints
  - `agents/` for bundled custom-agent definitions
  - `skills/` for Codex-facing skill parity
- Some capabilities span more than one surface. `council` is the clearest example: there is a Claude plugin under `claude/council/`, a Copilot package under `plugins/council/`, and Codex-facing material under `plugins/council/skills/` and `codex/`. Behavior changes often need coordinated doc or packaging updates across more than one tree.
- Persistent skill state must live outside plugin directories at `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` because plugin cache directories are replaced on update.

## Key conventions

- Exact skill discovery paths matter. Claude will only discover skills at `claude/{plugin}/skills/{skill}/SKILL.md`.
- Treat `SKILL.md` frontmatter as required in practice: `name`, `description`, `allowed-tools`, and `user-invocable`.
- Keep `SKILL.md` concise and move detailed material into linked `references/` files. Repo skill prompts are typically organized into explicit phases rather than long free-form instructions.
- Functional plugin changes must bump that plugin's `plugin.json` version in the same commit. Pure docs/comment/typo changes skip the bump.
- Validate via the surface you changed: Claude smoke commands for `claude/`, Copilot install/run flow for `plugins/`, and local checker/schema flows for script-based skills.
- Repo-specific authoring rules live in `.claude/rules/skill-authoring.md` and `.claude/rules/script-authoring-conventions.md`; follow those for new skills and Python-based checker scripts.
- Script defaults in this repo are Python with `#!/usr/bin/env python3`, `from __future__ import annotations`, `pathlib.Path`, deterministic NDJSON output, and explicit exit codes (`0` pass, `1` findings, `2` usage/input errors). Reuse shared helpers such as `_skill_check_common.py` when available.
- When a skill keeps state, update state files only after successful completion.
- Do not edit `.github/workflows/` manually; those workflows are org-synced.
- Do not add inline linter suppressions or relax lint config without explicit approval after exhausting real fixes.
