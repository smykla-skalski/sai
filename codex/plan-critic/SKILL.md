---
name: plan-critic
description: Critique implementation plans by reusing the source workflow under `claude/plan-critic`. Use when the user wants a plan stress-tested before implementation.
metadata:
  short-description: Critique implementation plans hard
---

# Plan Critic

Use this skill when the user presents an implementation plan and wants a serious critique.

This is a thin Codex wrapper around `claude/plan-critic/skills/plan-critic/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user presents an implementation plan and wants a serious critique.

## Do Not Use This Skill

- Do not use this skill to execute the plan itself.

## Source Material

- Source skill: `claude/plan-critic/skills/plan-critic/SKILL.md`
- Source directory: `claude/plan-critic/skills/plan-critic/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/plan-critic/skills/plan-critic/SKILL.md` as the source workflow and adapt any Claude-only delegation instructions to Codex rules.
2. Read `claude/plan-critic/skills/plan-critic/references/personas.md` before writing the critique.
3. Challenge hidden assumptions, missing rollback steps, and weak validation plans.
4. Separate blockers from improvements so the user can act on the critique.

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
User: "Use Plan Critic for this task."
Assistant: Opens `claude/plan-critic/skills/plan-critic/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Plan Critic workflow here."
Assistant: Reuses the source material from `claude/plan-critic/skills/plan-critic/` instead of relying on duplicated Codex-side resources.
</example>
