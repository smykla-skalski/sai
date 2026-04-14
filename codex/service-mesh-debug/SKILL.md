---
name: service-mesh-debug
description: Diagnose flaky service-mesh tests and connectivity issues by reusing the source workflow under `claude/service-mesh-debug`. Use when the user is debugging mesh flakiness, xDS issues, or mTLS failures.
metadata:
  short-description: Debug flaky mesh tests and traffic
---

# Service Mesh Debug

Use this skill when the user is debugging flaky e2e tests or service-mesh traffic problems.

This is a thin Codex wrapper around `claude/service-mesh-debug/skills/service-mesh-debug/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user is debugging flaky e2e tests or service-mesh traffic problems.

## Do Not Use This Skill

- Do not use this skill for unit tests, pure application bugs, or non-mesh networking issues.

## Source Material

- Source skill: `claude/service-mesh-debug/skills/service-mesh-debug/SKILL.md`
- Source directory: `claude/service-mesh-debug/skills/service-mesh-debug/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/service-mesh-debug/skills/service-mesh-debug/SKILL.md` as the source workflow.
2. Read the needed source references and helper scripts from `claude/service-mesh-debug/skills/service-mesh-debug/`.
3. Prefer the smallest fix that matches the diagnosed root cause.
4. State clearly whether the diagnosis is confirmed or inferred from partial evidence.

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
User: "Use Service Mesh Debug for this task."
Assistant: Opens `claude/service-mesh-debug/skills/service-mesh-debug/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Service Mesh Debug workflow here."
Assistant: Reuses the source material from `claude/service-mesh-debug/skills/service-mesh-debug/` instead of relying on duplicated Codex-side resources.
</example>
