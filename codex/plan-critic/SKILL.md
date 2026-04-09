---
name: plan-critic
description: Critique implementation plans before coding starts. Use when the user wants a plan stress-tested for correctness, sequencing, scope, and validation gaps.
metadata:
  short-description: Critique implementation plans hard
---

# Plan Critic

Use this skill when the user presents an implementation plan and wants a serious critique before execution begins.

This is a Codex-oriented port of the Claude skill at `claude/plan-critic/skills/plan-critic`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user presents an implementation plan and wants a serious critique before execution begins.

## Do Not Use This Skill

- Do not use this skill to execute the plan itself. Use it to critique and strengthen the plan before implementation.

## Workflow

1. Read the full plan first, then identify its goal, assumptions, dependencies, rollout sequence, and validation strategy.
2. Read `references/personas.md` before writing the critique so you cover skeptical, architectural, and verification perspectives even if you stay in a single-agent flow.
3. Challenge hidden assumptions, missing migration steps, rollback gaps, under-specified testing, and steps that are ordered incorrectly.
4. Distinguish between blockers, important weaknesses, and polish improvements so the user can act on the critique.
5. When you propose a revised plan, keep it concrete and execution-ready rather than abstract advice.

## Bundled Resources

- `agents/openai.yaml`
- `references/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Do not defer to the plan just because it is plausible. The job is to find the weak points.
- Prefer concrete failure modes over generic cautionary language.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Stress-test this rollout plan before we start coding."
Assistant: Finds sequencing gaps, missing rollback steps, and weak validation points.
</example>

<example>
User: "Critique this migration plan and propose a better one."
Assistant: Challenges assumptions, then rewrites the plan in a safer order.
</example>
