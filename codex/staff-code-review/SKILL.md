---
name: staff-code-review
description: Review code changes like a staff engineer, with emphasis on architecture, system fit, failure modes, compatibility, and operational risk. Use when the user wants a thorough review beyond line-level correctness.
metadata:
  short-description: Review changes at staff level
---

# Staff Code Review

Use this skill when the user wants a thorough review of a PR, diff, or code change that goes beyond line-level correctness.

This is a Codex-oriented port of the Claude skill at `claude/staff-code-review/skills/staff-code-review`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a thorough review of a PR, diff, or code change that goes beyond line-level correctness.

## Do Not Use This Skill

- Do not use this skill for a quick syntax check or trivial lint feedback where a lighter review is enough.

## Workflow

1. Start with triage: necessity, problem fit, failure tolerance, comprehensibility, architectural fit, and cross-team impact.
2. Read `references/review-dimensions.md` before the deep review. Read `references/backward-compatibility.md`, `references/convention-conformance.md`, `references/dead-code.md`, and `references/performance-scalability.md` when those dimensions matter to the change under review.
3. Ground the review in the actual codebase: inspect callers, existing patterns, tests, git history, and any design context before escalating findings.
4. Report findings first, ordered by severity, with concrete file evidence and an explanation of blast radius or long-term risk.
5. If the evidence only supports uncertainty, downgrade to a question instead of presenting a blocking claim as fact.

## Bundled Resources

- `agents/openai.yaml`
- `references/`
- `scripts/`

Read the specific review references named in the workflow before escalating findings in those areas.

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Do not use subagents unless the user explicitly asks for delegation. Cover the review dimensions in a single coherent pass instead.
- A good staff review is selective. Focus on the highest-leverage risks, not exhaustive nitpicking.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Do a staff-level review of this PR."
Assistant: Triage the change, grounds the review in codebase context, and reports high-leverage findings first.
</example>

<example>
User: "Review these changes for architectural and operational risk."
Assistant: Uses the review dimensions and cites concrete evidence for each finding.
</example>
