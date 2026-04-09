---
name: git-clean-gone
description: Clean up local git branches whose upstreams are gone, including associated worktrees. Use when merged or abandoned work leaves stale local branches behind.
metadata:
  short-description: Clean stale local branches safely
---

# Git Clean Gone

Use this skill when the user wants to prune stale local branches or clean related worktrees after PRs have been merged or removed upstream.

This is a Codex-oriented port of the Claude skill at `claude/git-clean-gone/skills/git-clean-gone`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user wants to prune stale local branches or clean related worktrees after PRs have been merged or removed upstream.

## Do Not Use This Skill

- Do not use this skill for general branch management, rebases, or arbitrary repository cleanup unrelated to gone branches.

## Workflow

1. Infer whether the user wants a preview or an actual cleanup. Default to preview when intent is unclear.
2. Set `SKILL_DIR` to this skill directory and run `scripts/clean-gone.sh` rather than re-implementing the cleanup logic.
3. Treat deletion as destructive. If the request is not explicit, start with `--dry-run` and show what would be removed before doing irreversible cleanup.
4. Never delete the current branch or the primary worktree. Report skipped branches and the reason.
5. Summarize deletions, skipped branches, preserved worktrees, and any partial failures.

## Bundled Resources

- `agents/openai.yaml`
- `scripts/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- If git or gh operations fail because of sandboxing, rerun the exact command with escalation and a short justification.
- Do not silently broaden the cleanup scope beyond the user request.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Preview stale branches I can delete from this repo."
Assistant: Runs the cleanup script with `--dry-run`, shows what would be removed, and asks before destructive cleanup.
</example>

<example>
User: "Delete gone branches and their worktrees."
Assistant: Confirms the request is explicit, runs the script, and summarizes deletions and skips.
</example>
