---
name: go-code-review
description: Review Go code using the source material under `claude/go-code-review`. Use when the user wants a focused Go review grounded in known failure patterns.
metadata:
  short-description: Review Go code for common mistakes
---

# Go Code Review

Use this skill when reviewing Go code and the user wants a focused quality review.

This is a thin Codex wrapper around `claude/go-code-review/skills/go-code-review/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when reviewing Go code and the user wants a focused quality review.

## Do Not Use This Skill

- Do not use this skill for non-Go review or for broad architectural review better handled elsewhere.

## Source Material

- Source skill: `claude/go-code-review/skills/go-code-review/SKILL.md`
- Source directory: `claude/go-code-review/skills/go-code-review/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/go-code-review/skills/go-code-review/SKILL.md` as the source workflow.
2. Read `claude/go-code-review/skills/go-code-review/knowledge-base.md` before reviewing.
3. Use `real-world-patterns.md` or `evals/test-cases.md` from the same source directory only when they materially improve the review.
4. Report findings first, ordered by severity, with concrete file evidence.

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
User: "Use Go Code Review for this task."
Assistant: Opens `claude/go-code-review/skills/go-code-review/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Go Code Review workflow here."
Assistant: Reuses the source material from `claude/go-code-review/skills/go-code-review/` instead of relying on duplicated Codex-side resources.
</example>
