---
name: review-claude-md
description: Audit and improve `CLAUDE.md` files using the bundled rubric, examples, and validators. Use when the user wants a `CLAUDE.md` contract reviewed or fixed.
metadata:
  short-description: Audit CLAUDE.md files quickly
---

# Review CLAUDE.md

Use this skill when the user wants a `CLAUDE.md` file reviewed or fixed against a structured checklist.

This is a Codex-oriented port of the Claude skill at `claude/review-claude-md/skills/review-claude-md`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants a `CLAUDE.md` file reviewed or fixed against a structured checklist.

## Do Not Use This Skill

- Do not use this skill for generic markdown cleanup or for reviewing Codex skills. It is specific to `CLAUDE.md` contracts.

## Workflow

1. Resolve the target repository or file path first. If none is provided, inspect the current repository for `CLAUDE.md`.
2. Read `references/rubric.md`, `references/output-format.md`, `references/examples.md`, and `references/sources.md` before writing the verdict.
3. Use `scripts/validate-claudemd.sh` and `scripts/validate-commands.sh` for repeatable checks instead of manually reproducing them.
4. Report findings before edits. Group them by severity and cite concrete file evidence.
5. Only patch the file when the user asked for fixes or approves remediation after the report.

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

- Keep the review focused on the repository instructions contract, not general prose polish.
- After edits, rerun the validators and summarize what changed and what still needs work.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Audit the `CLAUDE.md` in this repo."
Assistant: Runs the validators, reports the issues, and fixes them only if the user asked for remediation.
</example>

<example>
User: "Review and fix `docs/CLAUDE.md`."
Assistant: Applies the rubric, patches approved issues, and reruns the validators.
</example>
