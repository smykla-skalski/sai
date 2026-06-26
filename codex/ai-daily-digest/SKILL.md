---
name: ai-daily-digest
description: Produce a daily AI news digest and reuse the source workflow under `claude/ai-daily-digest`. Use when the user wants a curated AI briefing or roundup in Codex.
metadata:
  short-description: Assemble a daily AI news digest
---

# AI Daily Digest

Use this skill when the user wants a current AI digest or roundup in Codex.

This is a thin Codex wrapper around `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a current AI digest or roundup in Codex.

## Do Not Use This Skill

- Do not use this skill for timeless explanations that do not need current-source verification.

## Source Material

- Source skill: `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md`
- Source directory: `claude/ai-daily-digest/skills/ai-daily-digest/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md` as the source workflow and adapt it to Codex conventions. Where it spawns a research subagent per phase, run those per the "Codex execution notes" below - inline by default.
2. When the source skill refers to bundled references, read them from `claude/ai-daily-digest/skills/ai-daily-digest/references/` as needed.
3. Because this task depends on current events, browse for up-to-date sources before drafting and use concrete dates in the result.
4. Keep publication to Notion or another sink as a separate step after the digest content is correct.

## Codex execution notes - subagent spawning

The source workflow spawns a Claude `Agent` research subagent per phase (or per batch of independent phases). Codex subagent fan-out is fragile - as of mid-2026 the default `agents.max_threads` is **6**, completed subagents do not free their slot unless explicitly closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)), and subagents can finish without returning their payload ([#16051](https://github.com/openai/codex/issues/16051)). Therefore:

- **Default: sequential / inline.** Run each research phase yourself in turn - browse and gather sources, hold the findings in context, move to the next phase - then synthesize the digest. This sidesteps the thread cap and the slot-leak and handoff bugs.
- **Optional parallel mode (only if the user asks and has raised `agents.max_threads`).** Fan out only independent phases, cap concurrency at **<= 5**, **`close_agent` each research agent as soon as it returns** (completion alone does not free the slot), and **verify each returned its sources** before synthesizing - re-run any missing one inline. Never assume all spawned agents reported.
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
User: "Use AI Daily Digest for this task."
Assistant: Opens `claude/ai-daily-digest/skills/ai-daily-digest/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the AI Daily Digest workflow here."
Assistant: Reuses the source material from `claude/ai-daily-digest/skills/ai-daily-digest/` instead of relying on duplicated Codex-side resources.
</example>
