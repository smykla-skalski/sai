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

1. Treat `claude/plan-critic/skills/plan-critic/SKILL.md` as the source workflow. It spawns a grounding Explore agent and three parallel persona subagents (Skeptic, Architect, Verifier); run them per the "Codex execution notes" below - inline by default - instead of copying Claude's `Agent` / `subagent_type` calls.
2. Read `claude/plan-critic/skills/plan-critic/references/personas.md` before writing the critique.
3. Challenge hidden assumptions, missing rollback steps, and weak validation plans.
4. Separate blockers from improvements so the user can act on the critique.

## Codex execution notes - subagent spawning

The source workflow uses Claude's `Agent` tool: a Phase 2 Explore agent for the Grounding Brief and three parallel persona subagents (Skeptic, Architect, Verifier) in Phase 3. Codex subagent fan-out is fragile - as of mid-2026 the default `agents.max_threads` is **6**, completed subagents do not free their slot unless explicitly closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)), and subagents can finish without returning their payload ([#16051](https://github.com/openai/codex/issues/16051)). Therefore:

- **Default: sequential / inline.** Build the Grounding Brief yourself (grep/read), then adopt the Skeptic, Architect, and Verifier lenses in turn from `references/personas.md`, then synthesize the Approve/Reject/Refine verdict. This is the reliable Codex path and keeps all three personas grounded in the same brief.
- **Optional parallel mode (only if the user asks and has raised `agents.max_threads`).** Three personas fit under a raised cap; still **`close_agent` each as soon as it returns** (completion alone does not free the slot) and **verify each returned a payload** before synthesizing - re-run any missing one inline. Never assume all spawned personas reported.
- Use native agent tools only for agent state (`spawn_agent` / `wait_agent` / `close_agent`); do not run nested `codex exec`, and do not use shell for agent orchestration.

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
