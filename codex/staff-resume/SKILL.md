---
name: staff-resume
description: Coach and tailor staff-level resumes by reusing the source workflow under `claude/staff-resume`. Use when the user wants a staff-oriented resume review or rewrite in Codex.
metadata:
  short-description: Coach and tailor staff resumes
---

# Staff Resume

Use this skill when the user wants a resume reviewed, rewritten, or tailored for staff-level engineering roles.

This is a thin Codex wrapper around `claude/staff-resume/skills/staff-resume/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a resume reviewed, rewritten, or tailored for staff-level engineering roles.

## Do Not Use This Skill

- Do not use this skill for generic copyediting unrelated to resume positioning or job targeting.

## Source Material

- Source skill: `claude/staff-resume/skills/staff-resume/SKILL.md`
- Source directory: `claude/staff-resume/skills/staff-resume/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/staff-resume/skills/staff-resume/SKILL.md` as the source workflow.
2. Read `claude/staff-resume/skills/staff-resume/references/staff-resume-patterns.md` before rewriting.
3. Sharpen ownership, scope, and measurable impact without exaggerating the candidate’s experience.
4. Ask focused follow-up questions when critical achievements or metrics are missing.

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
User: "Use Staff Resume for this task."
Assistant: Opens `claude/staff-resume/skills/staff-resume/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Staff Resume workflow here."
Assistant: Reuses the source material from `claude/staff-resume/skills/staff-resume/` instead of relying on duplicated Codex-side resources.
</example>
