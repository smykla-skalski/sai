---
name: git-stage-hunk
description: Stage selected git diff hunks non-interactively. Use when only part of a file should be committed or when `git add -p` is unavailable.
metadata:
  short-description: Stage selected diff hunks safely
---

# Git Stage Hunk

Use this skill when the user wants selective staging without an interactive TTY, including hunk IDs, regex matching, file filters, or line ranges.

This is a Codex-oriented port of the Claude skill at `claude/git-stage-hunk/skills/git-stage-hunk`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants selective staging without an interactive TTY, including hunk IDs, regex matching, file filters, or line ranges.

## Do Not Use This Skill

- Do not use this skill when the user wants to stage every change in full files or when ordinary `git add` already solves the task.

## Workflow

1. Start by determining whether the user wants to list hunks, split a hunk, stage a selection, or verify the staged result.
2. Read `references/output-format.md` before presenting hunk listings. Read `references/split-hunk-guide.md` and `references/patchutils-guide.md` when the request needs sub-hunks, regex staging, or line-range staging.
3. Set `SKILL_DIR` to this skill directory and use `scripts/git-stage-hunk.py` and `scripts/split_hunk.py` instead of rebuilding patch logic manually.
4. Prefer a dry run or listing first unless the user clearly requested staging.
5. After staging, run the verification mode and summarize what is now staged versus still unstaged.

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

- If `patchutils`-dependent modes are unavailable, explain the limitation and fall back to supported modes.
- Keep the user’s existing index state intact except for the requested hunks.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "List the unstaged hunks in `src/auth.ts`."
Assistant: Uses the listing mode first, then presents hunk IDs and previews in the documented format.
</example>

<example>
User: "Stage only the validation changes from `src/auth.ts`."
Assistant: Identifies the relevant hunks, stages only that subset, and verifies the staged result.
</example>
