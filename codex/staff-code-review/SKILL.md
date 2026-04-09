---
name: staff-code-review
description: Review code changes with staff-level depth by reusing the source workflow under `claude/staff-code-review`. Use when the user wants a thorough review beyond line-level correctness.
metadata:
  short-description: Review changes at staff level
---

# Staff Code Review

Use this skill when the user wants a staff-level review of a PR, diff, or code change.

This is a thin Codex wrapper around `claude/staff-code-review/skills/staff-code-review/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a staff-level review of a PR, diff, or code change.

## Do Not Use This Skill

- Do not use this skill for a quick syntax check or lightweight lint feedback.

## Source Material

- Source skill: `claude/staff-code-review/skills/staff-code-review/SKILL.md`
- Source directory: `claude/staff-code-review/skills/staff-code-review/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/staff-code-review/skills/staff-code-review/SKILL.md` as the source workflow.
2. Read the needed source references from `claude/staff-code-review/skills/staff-code-review/references/` before escalating findings in those dimensions.
3. Ground the review in actual codebase context and report findings first, ordered by severity.
4. Where the source skill suggests agent fan-out, follow Codex delegation rules instead of copying Claude-specific agent usage blindly.

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
User: "Use Staff Code Review for this task."
Assistant: Opens `claude/staff-code-review/skills/staff-code-review/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Staff Code Review workflow here."
Assistant: Reuses the source material from `claude/staff-code-review/skills/staff-code-review/` instead of relying on duplicated Codex-side resources.
</example>
