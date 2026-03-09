---
name: review-skill
description: Audit Codex skill bundles before publishing. Use when reviewing or fixing a Codex skill's SKILL.md, references, scripts, or agents/openai.yaml for routing clarity, metadata quality, shell safety, and approval flow.
metadata:
  short-description: Audit Codex skills
---

# Review Skill

Use this skill to audit a Codex skill bundle, produce a verdict with evidence, and fix approved issues without importing Claude-only rules.

## Use this skill

- Review a skill under `codex/<name>/`, `.agents/skills/<name>/`, `$HOME/.agents/skills/<name>/`, `$CODEX_HOME/skills/<name>/`, or `~/.codex/skills/<name>/`
- Audit `SKILL.md`, bundled `references/`, bundled `scripts/`, and `agents/openai.yaml`
- Check whether a Claude-origin skill was ported cleanly to Codex

## Do not use this skill

- Do not use it for generic PR review, code review, or arbitrary markdown cleanup
- Do not apply Claude-only checks such as `allowed-tools`, `argument-hint`, `disable-model-invocation`, `$ARGUMENTS`, hooks, or `context: fork`
- Do not fail a skill only because it is authored under `codex/` instead of `.agents/skills`; classify the install surface first, then judge whether the contract is explicit and consistent

## Inputs to infer from the request

Infer the target skill directory from the user request and local context in this order:

1. An explicit path
2. A mentioned skill name that resolves to one local directory
3. The current directory if it already contains `SKILL.md`

If more than one target matches, ask one focused follow-up question before running any fixes.

## Required context

Before judging the skill, locate and read the applicable `AGENTS.md` files in scope for the target directory. Review against the real repo instructions, not against generic expectations.

Use this concrete skill path when calling bundled scripts:

```bash
SKILL_DIR="/Users/bart.smykla@konghq.com/Projects/github.com/smykla-skalski/sai/codex/review-skill"
```

Read [references/checklist.md](references/checklist.md) before manual review.
Read [references/rubric.md](references/rubric.md) before writing the verdict.
Read [references/codex-vs-claude-differences.md](references/codex-vs-claude-differences.md) when the target appears to be ported from Claude or mixes Claude-specific fields.
Read [references/examples.md](references/examples.md) when fixing weak routing, metadata, or approval wording.

## Automated pass

Run the validator first:

```bash
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR"
```

Optional focused modes:

```bash
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR" frontmatter
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR" structure
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR" shell
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR" metadata
"$SKILL_DIR/scripts/validate.py" "$TARGET_DIR" prompts
```

Parse every NDJSON line. Treat `pass: false` records as findings and use file/line evidence when present.

## Workflow

### 1. Discovery

1. Resolve the target directory.
2. Read the scoped `AGENTS.md` files.
3. Classify the install surface: repo source (`codex/<name>/`), public install (`.agents/skills/<name>/`), or user/global install (`$HOME/.agents/skills`, `$CODEX_HOME/skills`, `~/.codex/skills`).
4. Decide whether the user asked for audit only or audit plus fixes.

### 2. Automated validation

1. Run `validate.py`.
2. Group failures into frontmatter, structure, shell safety, metadata, and prompt quality.
3. Call out missing or malformed `agents/openai.yaml` explicitly.
4. Flag startup-cost smells, risky commands without approval language, and Claude-only surface area immediately.

### 3. Manual review

Inspect the target `SKILL.md`, linked references, scripts, and `agents/openai.yaml` against the checklist in `references/checklist.md`:

- routing clarity
- progressive disclosure
- examples
- approval and escalation flow
- AGENTS alignment
- helper-agent boundaries
- verification loop quality
- explicit install-surface contract

### 4. Verdict

Apply the rubric in `references/rubric.md` and report:

- `PASS`
- `NEEDS WORK`
- `FAIL`

Group findings by `Critical`, `Important`, and `Polish`. Every finding must cite concrete file evidence.

### 5. Fixes

Only patch files when the user asked for fixes or approves remediation after the report.

When fixing:

- preserve the target's chosen install surface
- keep `SKILL.md` compact and push detail into `references/`
- move brittle shell logic into `scripts/`
- keep `agents/openai.yaml` consistent with the actual workflow
- do not invent Claude-only metadata fields

### 6. Verification

After edits:

1. Re-run `validate.py`.
2. Manually re-check every finding you changed.
3. Summarize what passed, what still needs work, and any remaining risks.

## Reporting format

Use this shape unless the user asked for another format:

```text
## Codex Skill Review

Skill: <name>
Path: <path>
Surface: <repo source | public install | user/global install>
Verdict: <PASS | NEEDS WORK | FAIL>

### Critical
- [FAIL] <id>: <finding with file evidence>

### Important
- [PASS] <id>: <finding with file evidence>

### Polish
- [INFO] <id>: <optional improvement>

### Rationale
<2-3 sentences>
```

## Example requests

<example>
Context: The user says "audit codex/review-skill and tell me if it is publishable."
User: Audit `codex/review-skill` and report the verdict.
Assistant: Runs `validate.py`, reads the checklist and rubric, then returns an evidence-backed verdict without editing files.
</example>

<example>
Context: The user says "fix the Codex skill we just ported from Claude."
User: Review and fix `~/.codex/skills/my-skill`.
Assistant: Classifies the install surface, flags Claude-only fields, patches the skill, reruns validation, and summarizes the remaining risks.
</example>

<example>
Context: The user names a skill but not a path.
User: Review the `gh-review-comments` Codex skill in this repo.
Assistant: Resolves `codex/gh-review-comments`, audits `SKILL.md`, `references/`, scripts, and `agents/openai.yaml`, then reports the verdict with file evidence.
</example>
