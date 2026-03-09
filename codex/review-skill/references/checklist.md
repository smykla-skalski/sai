# Codex Skill Checklist

Binary checklist for reviewing a Codex skill bundle. Judge the real bundle: `SKILL.md`, linked references, bundled scripts, `agents/openai.yaml`, and the scoped `AGENTS.md` instructions.

## Table of contents

- [Critical](#critical)
- [Important](#important)
- [Polish](#polish)

## Critical

Any failure here should produce a `FAIL`.

| ID | Check |
| :-- | :-- |
| C1 | `SKILL.md` has valid minimal frontmatter with `name` and `description`. |
| C2 | The description states what the skill does and when to use it. |
| C3 | Linked files resolve correctly from `SKILL.md`. |
| C4 | The bundle does not expose secrets, credentials, or obviously unsafe script patterns such as `shell=True` or `os.system(`. |
| C5 | Risky actions have a safe execution path: approval language, escalation guidance, or an explicit read-only default. |
| C6 | The skill does not contradict scoped `AGENTS.md` instructions. |
| C7 | The skill is task-specific rather than generic filler. |
| C8 | A Codex skill does not carry Claude-only runtime surface such as `allowed-tools`, `argument-hint`, `$ARGUMENTS`, hooks, or `context: fork`. |

## Important

Failures here should usually produce `NEEDS WORK`.

| ID | Check |
| :-- | :-- |
| I1 | The body has clear routing boundaries: use when and do not use when. |
| I2 | The skill uses progressive disclosure and keeps detail in `references/` instead of bloating `SKILL.md`. |
| I3 | Complex or judgment-heavy behavior includes concrete examples. |
| I4 | Linked references have explicit read directives at the point where they are needed. |
| I5 | `agents/openai.yaml` exists when the skill is intended to ship as a polished Codex bundle. |
| I6 | `agents/openai.yaml` UI copy matches the actual workflow and `default_prompt` names `$skill-name`. |
| I7 | Script entrypoints are executable, deterministic, and use bounded shell patterns. |
| I8 | Risky shell commands mention approval or escalation before the action is taken. |
| I9 | Startup-cost discipline is preserved: no "enumerate all skills on startup" or similar first-turn tax. |
| I10 | Helper-agent boundaries are explicit and scoped to concrete subtasks. |
| I11 | The skill explains its install or discovery surface when that contract matters. |
| I12 | Fix workflows include a verification loop: rerun checks, re-read changed findings, summarize residual risk. |

## Polish

These do not change the verdict alone, but they matter for publishable quality.

| ID | Check |
| :-- | :-- |
| P1 | Long reference files include a table of contents. |
| P2 | Naming is consistent across `SKILL.md`, script names, and `agents/openai.yaml`. |
| P3 | `short_description` is crisp and user-facing instead of internal jargon. |
| P4 | Examples cover both the common path and at least one edge case. |
| P5 | Shell snippets are quiet, scoped, and avoid noisy repo-wide scans when narrower commands are possible. |

## Review notes

- Do not fail a skill only because it is authored under `codex/` instead of `.agents/skills`. Fail the hidden or contradictory contract, not the directory name alone.
- If the target explicitly chooses a dual-surface workflow, verify that the authoring source and install target are both described clearly.
- When `agents/openai.yaml` is absent in an external skill, note whether that is a deliberate portability choice or a quality gap.
