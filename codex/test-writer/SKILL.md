---
name: test-writer
description: Write or review behavior-first tests by reusing the source workflow under `claude/test-writer`. Use when the user wants tests added or existing tests reviewed in Codex.
metadata:
  short-description: Write behavior-first tests
---

# Test Writer

Use this skill when the user wants new tests added or existing tests reviewed for quality and maintainability.

This is a thin Codex wrapper around `claude/test-writer/skills/test-writer/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants new tests added or existing tests reviewed for quality and maintainability.

## Do Not Use This Skill

- Do not use this skill for production code changes that do not actually require test design or review.

## Source Material

- Source skill: `claude/test-writer/skills/test-writer/SKILL.md`
- Source directory: `claude/test-writer/skills/test-writer/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/test-writer/skills/test-writer/SKILL.md` as the source workflow.
2. Read the needed source references from `claude/test-writer/skills/test-writer/references/` before writing or reviewing tests.
3. Focus on behaviour, edge cases, and minimal mocking rather than implementation-coupled tests.
4. Run the narrowest relevant verification available after adding or changing tests.

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
User: "Use Test Writer for this task."
Assistant: Opens `claude/test-writer/skills/test-writer/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Test Writer workflow here."
Assistant: Reuses the source material from `claude/test-writer/skills/test-writer/` instead of relying on duplicated Codex-side resources.
</example>
