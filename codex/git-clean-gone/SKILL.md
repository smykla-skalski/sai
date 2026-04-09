---
name: git-clean-gone
description: Clean stale local branches and worktrees by reusing the source workflow under `claude/git-clean-gone`. Use when merged or abandoned work leaves gone branches behind.
metadata:
  short-description: Clean stale local branches safely
---

# Git Clean Gone

Use this skill when the user wants to prune stale local branches or related worktrees.

This is a thin Codex wrapper around `claude/git-clean-gone/skills/git-clean-gone/SKILL.md`. Reuse the source workflow, references, scripts, and eval material from the Claude skill directory instead of maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants to prune stale local branches or related worktrees.

## Do Not Use This Skill

- Do not use this skill for general branch management or arbitrary repository cleanup unrelated to gone branches.

## Source Material

- Source skill: `claude/git-clean-gone/skills/git-clean-gone/SKILL.md`
- Source directory: `claude/git-clean-gone/skills/git-clean-gone/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/git-clean-gone/skills/git-clean-gone/SKILL.md` as the source workflow and translate Claude-only mechanics into normal Codex steps.
2. Run the helper from `claude/git-clean-gone/skills/git-clean-gone/scripts/clean-gone.sh` instead of reimplementing cleanup logic.
3. Default to preview mode when intent is unclear, and treat deletions as destructive actions that need explicit user intent.
4. Summarize deletions, skips, preserved worktrees, and any partial failures.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `user-invocable`, `$ARGUMENTS`, and `CLAUDE_SKILL_DIR`.
- Infer inputs from the user request and local context before asking follow-up questions.
- If a source script or networked command fails because of sandbox restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "Use Git Clean Gone for this task."
Assistant: Opens `claude/git-clean-gone/skills/git-clean-gone/SKILL.md`, loads only the needed source references or scripts, adapts the workflow to Codex conventions, and completes the task.
</example>

<example>
User: "Apply the Git Clean Gone workflow here."
Assistant: Reuses the source material from `claude/git-clean-gone/skills/git-clean-gone/` instead of relying on duplicated Codex-side resources.
</example>
