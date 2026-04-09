---
name: staff-resume
description: Coach and tailor staff-level engineering resumes using bundled patterns for scope, impact, archetypes, and ATS alignment. Use when the user wants a staff-oriented resume review or rewrite.
metadata:
  short-description: Coach and tailor staff resumes
---

# Staff Resume

Use this skill when the user wants a resume reviewed, rewritten, or tailored for staff-level engineering roles.

This is a Codex-oriented port of the Claude skill at `claude/staff-resume/skills/staff-resume`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a resume reviewed, rewritten, or tailored for staff-level engineering roles.

## Do Not Use This Skill

- Do not use this skill for general copyediting unrelated to resume positioning or job targeting.

## Workflow

1. Determine whether the user wants coaching, tailoring to a job, or both.
2. Read `references/staff-resume-patterns.md` before rewriting so the advice stays grounded in staff-level expectations.
3. Look for evidence of scope, decision-making authority, cross-team influence, technical depth, and measurable impact.
4. Rewrite bullets to make outcomes, ownership, and scale explicit without exaggeration.
5. If a job description is provided, map the resume to that role’s needs and call out remaining gaps.

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

- Do not inflate the candidate’s experience. Sharpen what is already true.
- If critical achievements or metrics are missing, ask focused questions instead of guessing.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Tailor my resume for this staff platform role."
Assistant: Reviews the resume against the job needs and proposes sharper bullets and positioning.
</example>

<example>
User: "Coach me on making this resume look more staff-level."
Assistant: Finds missing scope and impact signals, then suggests focused rewrites and follow-up questions.
</example>
