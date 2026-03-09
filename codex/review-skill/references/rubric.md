# Codex Skill Rubric

Use this rubric after the automated checks finish.

## Verdict logic

- Any `Critical` failure -> `FAIL`
- No `Critical` failures but one or more `Important` failures -> `NEEDS WORK`
- No `Critical` or `Important` failures -> `PASS`
- `Polish` findings are informational unless they support a broader `Important` problem

## Review sequence

1. Resolve the target surface.
   Repo source: `codex/<name>/`
   Public install: `.agents/skills/<name>/`
   User or global install: `$HOME/.agents/skills/<name>/`, `$CODEX_HOME/skills/<name>/`, or `~/.codex/skills/<name>/`
2. Read the scoped `AGENTS.md` files before making any judgment.
3. Run the automated validator.
4. Read the target `SKILL.md` in full.
5. Read only the linked references you need for the failing or ambiguous checks.
6. Inspect bundled scripts directly instead of trusting SKILL summaries.
7. Reconcile the skill contract with `agents/openai.yaml`.

## How to handle common edge cases

### Claude ports

If the bundle still carries Claude-only fields or language, fail the Codex review even if the prose is otherwise good. The platform contract is part of the quality bar.

### Missing metadata

If `agents/openai.yaml` is missing, decide whether the target is:

- a polished repo-native Codex bundle that should ship metadata
- a deliberately minimal external skill

Default toward `Important` failure unless the skill explicitly documents why metadata is absent.

### Side-effecting skills

If the skill can mutate repos, infrastructure, or remote systems:

- prefer `policy.allow_implicit_invocation: false`
- require explicit approval or escalation wording
- check whether the workflow defaults to inspect or plan before mutate

### Install-path drift

Do not hard-code a single discovery path into the verdict. Instead, ask:

- is the chosen source path explicit?
- is the install target explicit when needed?
- do the docs and metadata agree?

## Fix guidance

- Keep `SKILL.md` compact and operational.
- Put variants, long examples, and comparison tables into `references/`.
- Move fragile shell logic into executable scripts.
- Keep `agents/openai.yaml` aligned with the real workflow after every edit.
- Re-run validation after each fix batch, not only at the end.
