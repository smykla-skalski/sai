---
name: promptgen
description: Turn rough instructions into stronger prompts using the source workflow at `claude/promptgen`. Use when the user wants a task prompt, system prompt, coding-agent prompt, tool description, eval grader, subagent briefing, or prompt-improvement pass rather than direct execution.
metadata:
  short-description: Turn rough asks into prompts
  version: "3.0.0"
---

# Promptgen

Use this skill when the user wants a rough task description turned into a stronger prompt instead of asking Codex to perform the underlying task.

This is a thin Codex wrapper around `claude/promptgen/skills/promptgen/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- The user wants a rough task description turned into a stronger prompt.
- Targets: task prompts, system prompts, coding-agent prompts, tool descriptions, eval graders, subagent briefings, three-agent harness instructions, prompt-improvement requests.

## Do Not Use This Skill

- Do not use this skill when the user wants the underlying task completed directly.

## Source Material

- Source skill: `claude/promptgen/skills/promptgen/SKILL.md`
- Source directory: `claude/promptgen/skills/promptgen/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/promptgen/skills/promptgen/SKILL.md` as the source workflow and ignore Claude-only invocation wiring.
2. Read the needed source references from `claude/promptgen/skills/promptgen/references/`. The references cover prompt principles, mechanics, structure templates, security patterns, code-for-agents rules, and anti-patterns.
3. Before generation, read `prompt-mechanics.md` for the prompt brief and specificity dial; read `prompt-structure.md` to pick the target template (Claude / GPT / Codex / generic) and any prompt-type insert (subagent briefing, three-agent harness, eval grader).
4. Use `prompt-principles.md` for evidence-backed defaults, model-generation gotchas, and reasoning-effort / verbosity calibration.
5. Use `security-patterns.md` only when the prompt's target agent will face untrusted input, MCP tools, RAG, or the lethal trifecta. Apply Meta's Rule of Two when state-changing actions are in scope.
6. Run the `anti-patterns.md` self-check before returning the prompt; audit explicitly for contradictions.
7. If current repo facts matter (file paths, naming conventions, build / test commands, framework versions), inspect the repo before finalizing the generated prompt.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as tool allowlists, invocation metadata, Claude argument variables, and Claude skill-directory environment variables.
- Infer inputs from the user request and local context before asking follow-up questions. Bias to action over clarification - persist end-to-end within a single turn whenever feasible.
- Apply scope discipline when generating Codex-targeted prompts: implement EXACTLY and ONLY what the user requests; do not invent extra features or UX embellishments.
- Prefer `--for codex` mechanics when the target prompt is for Codex, repo edits, code review, CI repair, or long-running coding-agent work.
- For Codex-targeted prompts, allow short preambles every 1-3 logical steps; hard floor every 6 steps or 10 tool calls. Do not require routine progress preambles for non-interactive rollouts.
- Recommend `reasoning_effort` (`none | minimal | low | medium | high | xhigh`) and `verbosity` tuning at the API level instead of writing prose that approximates them. Default `none` on GPT-5.2; calibrate up only for genuinely complex multi-step work.
- Prefer dedicated tools over shell. Always parallelize independent reads. Do not hard-code tool-call order unless the harness contract requires it.
- For long-running rollouts beyond a single context window, instruct the agent to write a structured progress file (JSON, less prone to model corruption than Markdown) at the end of each session and read it at the start of the next.
- For repo-wide durable norms, recommend documenting them in `AGENTS.md` at the repo root (or nested per directory). Codex / Cursor / Copilot / Amp / Jules / Factory / Windsurf / Aider all read this file. Cap is 32 KiB (`project_doc_max_bytes`).
- Do not copy to clipboard unless the user explicitly asks for that side effect in the Codex session.
- If a source script or networked command fails because of sandbox restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit. Default Codex behavior: pause only for actions that risk data loss, security boundaries, or external impact.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before / after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Use Promptgen for this task."
Assistant: Opens `claude/promptgen/skills/promptgen/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Promptgen workflow here."
Assistant: Reuses the source material from `claude/promptgen/skills/promptgen/` instead of relying on duplicated Codex-side resources.
</example>

<example>
User: "Turn this into a Codex coding-agent prompt: 'fix the flaky checkout tests and verify the failure mode'."
Assistant: Builds a Codex variant from `prompt-structure.md` with explicit outcome contract, done-when criteria, narrow verification command, scope discipline, and a single-turn persistence rule. Skips routine final reminders.
</example>
