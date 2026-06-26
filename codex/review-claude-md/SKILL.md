---
name: review-claude-md
description: Audit `CLAUDE.md` files by reusing the source workflow under `claude/review-claude-md`. Use when the user wants a CLAUDE.md contract reviewed or fixed in Codex.
metadata:
  short-description: Audit CLAUDE.md files quickly
---

# Review CLAUDE.md

Use this skill when the user wants a `CLAUDE.md` file reviewed or fixed against a structured checklist.

This is a thin Codex wrapper around `claude/review-claude-md/skills/review-claude-md/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a `CLAUDE.md` file reviewed or fixed against a structured checklist.

## Do Not Use This Skill

- Do not use this skill for generic markdown cleanup or for reviewing Codex skills.

## Source Material

- Source skill: `claude/review-claude-md/skills/review-claude-md/SKILL.md`
- Source directory: `claude/review-claude-md/skills/review-claude-md/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/review-claude-md/skills/review-claude-md/SKILL.md` as the source workflow. It spawns helper subagents sequentially (repo scan, validation-script run, re-evaluation); run them per the "Codex execution notes" below - inline in the main loop.
2. Read the needed source references from `claude/review-claude-md/skills/review-claude-md/references/`.
3. Run the source helper scripts from `claude/review-claude-md/skills/review-claude-md/scripts/` instead of duplicating them.
4. Report findings before fixes unless the user explicitly asked for immediate remediation.

## Codex execution notes - subagent spawning

The source workflow spawns Claude `Agent` helpers sequentially - an Explore agent to scan the repo, a general-purpose agent to run the validation scripts, and another to re-evaluate the fixed file. None of these need to be subagents on Codex, and Codex fan-out is fragile anyway (default `agents.max_threads` is **6**; completed subagents do not free their slot unless explicitly closed - [openai/codex#22779](https://github.com/openai/codex/issues/22779); subagents can finish without returning their payload - [#16051](https://github.com/openai/codex/issues/16051)). Therefore:

- **Run every step inline in the main loop.** Do the repo scan with grep/read, run the validation scripts directly, apply fixes with the editor, then re-evaluate inline against the rubric. Do not spawn one subagent per step - the steps are sequential and share context, so inline is both simpler and more reliable.
- Use native agent tools only for agent state (`spawn_agent` / `wait_agent` / `close_agent`); do not run nested `codex exec`, and do not use shell (`ps`, `pgrep`) for agent orchestration.

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
User: "Use Review CLAUDE.md for this task."
Assistant: Opens `claude/review-claude-md/skills/review-claude-md/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Review CLAUDE.md workflow here."
Assistant: Reuses the source material from `claude/review-claude-md/skills/review-claude-md/` instead of relying on duplicated Codex-side resources.
</example>
