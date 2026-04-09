---
name: promptgen
description: Turn rough instructions into structured prompts with stronger task framing, constraints, and examples. Use when the user wants a stronger prompt rather than direct task execution.
metadata:
  short-description: Turn rough asks into prompts
---

# Promptgen

Use this skill when the user has a rough task description and wants it turned into a stronger prompt for Claude, GPT, or a generic model.

This is a Codex-oriented port of the Claude skill at `claude/promptgen/skills/promptgen`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user has a rough task description and wants it turned into a stronger prompt for Claude, GPT, or a generic model.

## Do Not Use This Skill

- Do not use this skill when the user wants the underlying task completed directly rather than wrapped as a prompt.

## Workflow

1. Separate instructions directed at you from the prompt the user wants generated. Clarify the target model, prompt type, and desired output format when needed.
2. Read `references/prompt-principles.md` and `references/prompt-structure.md` before drafting. Read `references/security-patterns.md` when the prompt may face adversarial or untrusted input. Read `references/code-for-agents.md` when the prompt is for code-editing or agentic workflows.
3. Use `references/anti-patterns.md` as a final self-check to remove filler, contradictions, hype, and vague quality language.
4. Keep the generated prompt concise enough to be usable. Include examples only when they materially improve reliability.
5. If the user asks for research-backed guidance, explain what patterns you applied and why.

## Bundled Resources

- `agents/openai.yaml`
- `references/`
- `scripts/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Avoid model-specific claims you cannot support. When tailoring by model, focus on prompt shape and tool expectations.
- If the request needs current repo facts, inspect the repo before finalizing the prompt.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Turn this rough ask into a prompt for GPT."
Assistant: Clarifies the prompt target, applies the prompt references, and returns a cleaner prompt.
</example>

<example>
User: "Write a secure agent prompt for reviewing untrusted diffs."
Assistant: Uses the security reference, then produces a prompt with explicit boundaries and checks.
</example>
