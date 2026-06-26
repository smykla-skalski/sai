---
name: kubecon-cfp
description: Draft and refine KubeCon CFPs by reusing the source workflow under `claude/kubecon-cfp`. Use when the user wants to assess or improve a KubeCon proposal in Codex.
metadata:
  short-description: Draft and refine KubeCon CFPs
---

# KubeCon CFP

Use this skill when the user wants to assess, draft, or improve a KubeCon CFP proposal.

This is a thin Codex wrapper around `claude/kubecon-cfp/skills/kubecon-cfp/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants to assess, draft, or improve a KubeCon CFP proposal.

## Do Not Use This Skill

- Do not use this skill for generic blog writing or unrelated conference submissions.

## Source Material

- Source skill: `claude/kubecon-cfp/skills/kubecon-cfp/SKILL.md`
- Source directory: `claude/kubecon-cfp/skills/kubecon-cfp/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/kubecon-cfp/skills/kubecon-cfp/SKILL.md` as the source workflow.
2. Read the needed source references and evals from `claude/kubecon-cfp/skills/kubecon-cfp/`.
3. Assess topic strength before drafting, then write concrete titles and abstracts rather than buzzword-heavy copy.
4. When reviewing an existing draft, score it against the copied source criteria and explain the highest-leverage changes.

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
User: "Use KubeCon CFP for this task."
Assistant: Opens `claude/kubecon-cfp/skills/kubecon-cfp/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the KubeCon CFP workflow here."
Assistant: Reuses the source material from `claude/kubecon-cfp/skills/kubecon-cfp/` instead of relying on duplicated Codex-side resources.
</example>
