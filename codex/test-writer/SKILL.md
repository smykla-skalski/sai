---
name: test-writer
description: Write or review tests that focus on behaviour, minimize mocking, and use language-appropriate patterns. Use when the user wants tests added or existing tests reviewed for quality.
metadata:
  short-description: Write behavior-first tests
---

# Test Writer

Use this skill when the user wants new tests added or existing tests reviewed for quality and maintainability.

This is a Codex-oriented port of the Claude skill at `claude/test-writer/skills/test-writer`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants new tests added or existing tests reviewed for quality and maintainability.

## Do Not Use This Skill

- Do not use this skill for production code changes that happen to mention tests but do not actually require test design or review.

## Workflow

1. Determine whether the task is to write tests, review tests, or both. Infer the language from the repo when possible.
2. Read `references/testing-principles.md` before drafting. Read `references/language-patterns.md` for the target language before writing or reviewing concrete tests.
3. Test behaviour rather than implementation details. Prefer table-driven or parameterized structures when multiple cases share the same assertion shape.
4. Use mocks only at true external boundaries and keep them minimal.
5. When reviewing tests, flag brittle assertions, over-mocking, missing edge cases, and gaps in behavioural coverage.

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

- Keep the tests aligned with existing repo conventions unless those conventions are clearly harmful.
- When adding tests, run the narrowest relevant verification available and report what was or was not executed.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Add tests for `pkg/parser.go`."
Assistant: Uses the language patterns and testing principles to write behaviour-first tests.
</example>

<example>
User: "Review these tests for brittleness."
Assistant: Flags over-mocking, missing edge cases, and implementation-coupled assertions.
</example>
