---
name: generate-claude-md
description: Generate a lean, high-signal `CLAUDE.md` for a repository by reusing the source workflow under `claude/generate-claude-md`. Use when the user wants a CLAUDE.md created or refreshed in Codex.
metadata:
  short-description: Generate a lean CLAUDE.md for a repo
---

# Generate CLAUDE.md

Use this skill when the user wants a `CLAUDE.md` file created, scaffolded, or
refreshed for a repository from codebase analysis.

This is a thin Codex wrapper around
`claude/generate-claude-md/skills/generate-claude-md/SKILL.md`. Reuse the source
workflow, references, and validator from the Claude skill directory instead of
maintaining duplicated Codex copies.

## Use This Skill

- Use this skill when the user wants a `CLAUDE.md` generated or refreshed for a project.

## Do Not Use This Skill

- Do not use this skill to audit an existing CLAUDE.md against a checklist — that is `review-claude-md`.
- Do not use this skill for generic markdown authoring unrelated to CLAUDE.md.

## Source Material

- Source skill: `claude/generate-claude-md/skills/generate-claude-md/SKILL.md`
- Source directory: `claude/generate-claude-md/skills/generate-claude-md/`
- Codex metadata: `agents/openai.yaml`

Load only the source files needed for the current task. Do not recreate or copy the
Claude-side bundled resources into this Codex skill.

## Workflow

1. Treat `claude/generate-claude-md/skills/generate-claude-md/SKILL.md` as the source workflow.
2. Read the needed source references from `claude/generate-claude-md/skills/generate-claude-md/references/` (principles, section guide, scan spec, modularization, example).
3. Run the source validator `claude/generate-claude-md/skills/generate-claude-md/scripts/validate-claude-md.py` instead of duplicating it.
4. Apply the deletion test to every line; produce a short, project-specific file.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `context: fork`, `$ARGUMENTS`, and `CLAUDE_SKILL_DIR`.
- Infer the repo root and flags from the user request and local context before asking follow-up questions.
- Write safety: never overwrite an existing `CLAUDE.md` unless the user was explicit; otherwise write `CLAUDE.generated.md` and report.
- If a source script fails because of sandbox restrictions, rerun it with escalation and a short justification.

## Verification

After generating, run the source validator on the written file and report the verdict.

1. Run `validate-claude-md.py <target> --human` and read the result.
2. Fix any `[FAIL]` check and re-run, up to a few rounds.
3. Report what was verified, the final line count, and any residual risk.

## Examples

<example>
User: "Use Generate CLAUDE.md for this repo."
Assistant: Opens `claude/generate-claude-md/skills/generate-claude-md/SKILL.md`, scans the codebase, synthesizes a lean CLAUDE.md, validates it, and reports.
</example>

<example>
User: "Make a CLAUDE.md for this project."
Assistant: Reuses the source material from `claude/generate-claude-md/skills/generate-claude-md/`, writes a short project-specific file, and runs the validator before reporting.
</example>
