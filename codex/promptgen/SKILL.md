---
name: promptgen
description: Turn rough instructions into stronger prompts by reusing the source workflow under `claude/promptgen`. Use when the user wants a stronger prompt rather than direct execution.
metadata:
  short-description: Turn rough asks into prompts
---

# Promptgen

Use this skill when the user wants a rough task description turned into a stronger prompt.

This is a thin Codex wrapper around `claude/promptgen/skills/promptgen/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a rough task description turned into a stronger prompt.

## Do Not Use This Skill

- Do not use this skill when the user wants the underlying task completed directly.

## Source Material

- Source skill: `claude/promptgen/skills/promptgen/SKILL.md`
- Source directory: `claude/promptgen/skills/promptgen/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/promptgen/skills/promptgen/SKILL.md` as the source workflow and ignore Claude-only invocation wiring.
2. Read the needed source references from `claude/promptgen/skills/promptgen/references/`.
3. Use the source `anti-patterns.md` as a final self-check before returning the prompt.
4. If current repo facts matter, inspect the repo before finalizing the generated prompt.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `user-invocable`, `$ARGUMENTS`, and `CLAUDE_SKILL_DIR`.
- Infer inputs from the user request and local context before asking follow-up questions.
- If a source script or networked command fails because of sandbox restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Use Promptgen for this task."
Assistant: Opens `claude/promptgen/skills/promptgen/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Promptgen workflow here."
Assistant: Reuses the source material from `claude/promptgen/skills/promptgen/` instead of relying on duplicated Codex-side resources.
</example>
