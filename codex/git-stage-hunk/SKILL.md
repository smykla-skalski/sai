---
name: git-stage-hunk
description: Stage selected git hunks non-interactively by reusing the source workflow under `claude/git-stage-hunk`. Use when only part of a file should be committed.
metadata:
  short-description: Stage selected diff hunks safely
---

# Git Stage Hunk

Use this skill when the user wants selective staging without an interactive TTY.

This is a thin Codex wrapper around `claude/git-stage-hunk/skills/git-stage-hunk/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants selective staging without an interactive TTY.

## Do Not Use This Skill

- Do not use this skill when ordinary `git add` already solves the task or when the user wants every change staged.

## Source Material

- Source skill: `claude/git-stage-hunk/skills/git-stage-hunk/SKILL.md`
- Source directory: `claude/git-stage-hunk/skills/git-stage-hunk/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/git-stage-hunk/skills/git-stage-hunk/SKILL.md` as the source workflow and map it to Codex interaction patterns.
2. Use the helper programs in `claude/git-stage-hunk/skills/git-stage-hunk/scripts/`.
3. Read the relevant source references from `claude/git-stage-hunk/skills/git-stage-hunk/references/` when the task needs split hunks, regex staging, or line-range staging.
4. Prefer listing or dry-run output first unless the user clearly requested staging.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `user-invocable`, `$ARGUMENTS`, and `CLAUDE_SKILL_DIR`.
- Infer inputs from the user request and local context before asking follow-up questions.
- If a source script or networked command fails because of sandbox restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- This skill runs in a single Codex agent loop - no subagent fan-out. If the source workflow spawns helper or persona subagents, do that work inline in the main loop.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Use Git Stage Hunk for this task."
Assistant: Opens `claude/git-stage-hunk/skills/git-stage-hunk/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Git Stage Hunk workflow here."
Assistant: Reuses the source material from `claude/git-stage-hunk/skills/git-stage-hunk/` instead of relying on duplicated Codex-side resources.
</example>
