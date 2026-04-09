---
name: slug
description: Generate a semantic session slug by reusing the source workflow under `claude/slug`. Use when the user wants a branch-style name or `/rename` command in Codex.
metadata:
  short-description: Generate a concise session slug
---

# Session Slug

Use this skill when the user wants a concise branch-style name for the work in the session.

This is a thin Codex wrapper around `claude/slug/skills/slug/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a concise branch-style name for the work in the session.

## Do Not Use This Skill

- Do not use this skill when there was no meaningful work or when the user wants a product name.

## Source Material

- Source skill: `claude/slug/skills/slug/SKILL.md`
- Source directory: `claude/slug/skills/slug/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/slug/skills/slug/SKILL.md` as the source workflow.
2. Review the full session context, not just the last message, before proposing a slug.
3. Return a directly usable rename command, and only use clipboard automation if the user wants it.
4. If the session had no meaningful implementation work, say so instead of inventing a weak slug.

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
User: "Use Session Slug for this task."
Assistant: Opens `claude/slug/skills/slug/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Session Slug workflow here."
Assistant: Reuses the source material from `claude/slug/skills/slug/` instead of relying on duplicated Codex-side resources.
</example>
