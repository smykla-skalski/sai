---
name: go-code-review
description: Review Go code for common correctness, concurrency, interface, performance, and testing mistakes. Use when the user wants a focused Go review grounded in known failure patterns.
metadata:
  short-description: Review Go code for common mistakes
---

# Go Code Review

Use this skill when reviewing Go code and the user wants a focused quality review grounded in common failure patterns.

This is a Codex-oriented port of the Claude skill at `claude/go-code-review/skills/go-code-review`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when reviewing Go code and the user wants a focused quality review grounded in common failure patterns.

## Do Not Use This Skill

- Do not use this skill for non-Go code review or for broad architectural reviews that are better handled by a higher-level review skill.

## Workflow

1. Read `knowledge-base.md` before reviewing so severity and terminology stay anchored to the curated mistake set.
2. Use `real-world-patterns.md` when you need concrete examples or counterexamples from existing projects. Use `evals/test-cases.md` only for calibration or follow-up validation.
3. Review findings in a code-review mindset: prioritize bugs, behavioural risks, performance cliffs, concurrency hazards, API misuse, and missing tests.
4. Re-check flagged lines before reporting to reduce false positives, especially around concurrency, error propagation, and interface design.
5. Report findings first, ordered by severity, with file evidence and the relevant mistake category.

## Bundled Resources

- `agents/openai.yaml`
- `evals/`
- `knowledge-base.md`
- `real-world-patterns.md`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Do not pad the output with generic praise. If there are no findings, say so explicitly and mention residual risks or test gaps.
- Keep the review grounded in the actual diff and surrounding context, not just checklist matching.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Review these Go changes for correctness and concurrency risks."
Assistant: Reads the diff, checks against the knowledge base, and returns findings ordered by severity.
</example>

<example>
User: "Audit `internal/cache/` for common Go mistakes."
Assistant: Reviews the targeted files and cites the relevant mistake classes with file evidence.
</example>
