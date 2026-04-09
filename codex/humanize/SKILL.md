---
name: humanize
description: Rewrite text to sound less formulaic by reusing the source workflow under `claude/humanize`. Use when the user wants writing to sound more natural in Codex.
metadata:
  short-description: Rewrite text to sound natural
---

# Humanize

Use this skill when the user wants a draft rewritten to sound more natural and less AI-generated.

This is a thin Codex wrapper around `claude/humanize/skills/humanize/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a draft rewritten to sound more natural and less AI-generated.

## Do Not Use This Skill

- Do not use this skill for translation or for edits where wording must stay nearly exact.

## Source Material

- Source skill: `claude/humanize/skills/humanize/SKILL.md`
- Source directory: `claude/humanize/skills/humanize/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/humanize/skills/humanize/SKILL.md` as the source workflow.
2. Read the needed source references from `claude/humanize/skills/humanize/references/`.
3. Preserve meaning and factual claims while improving rhythm, specificity, and tone.
4. If the user only wants scoring, report patterns without rewriting the text.

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
User: "Use Humanize for this task."
Assistant: Opens `claude/humanize/skills/humanize/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Humanize workflow here."
Assistant: Reuses the source material from `claude/humanize/skills/humanize/` instead of relying on duplicated Codex-side resources.
</example>
