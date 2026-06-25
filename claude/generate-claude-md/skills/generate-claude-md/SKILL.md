---
name: generate-claude-md
description: Generate a lean, high-signal CLAUDE.md for a repository from codebase analysis. Grounded in Anthropic best practices and empirical studies; built to pass review-claude-md (a bundled validator enforces the same critical checks). Use when the user asks to "generate CLAUDE.md", "create a CLAUDE.md", "write a CLAUDE.md", "init CLAUDE.md", "scaffold CLAUDE.md", or "bootstrap CLAUDE.md" for a project.
argument-hint: "[path/to/repo] [--output PATH] [--update] [--force] [--rules] [--dry-run]"
allowed-tools: Bash, Edit, Glob, Grep, Read, Task, Write
user-invocable: true
context: fork
agent: general-purpose
---

<!-- justify: writes a new CLAUDE.md; non-destructive by default, never overwrites an existing file without --force -->

# Generate CLAUDE.md

Build a project-specific CLAUDE.md that earns every line: exact commands, an
architecture map, real gotchas, and enforced boundaries — and nothing Claude
already knows. The goal is the inverse of naive `/init` output: short, specific,
and free of README duplication, directory trees, and generic filler.

This skill is the generator counterpart to the `review-claude-md` plugin. It
targets the same rubric the reviewer audits against. The bundled validator
(Phase 7) deterministically gates the mechanical checks — commands present,
length, no README duplication, no generic advice, no directory tree, bullets —
which are all of the reviewer's Critical checks, so a passing file cannot earn a
review FAIL verdict. The remaining quality (architecture as relationships, domain
mapping, real gotchas, style deltas) is your job during synthesis. Read
[references/principles.md](references/principles.md) in full before synthesizing —
it is the source of truth for every rule below.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: repo root (default: current working directory)
- `--output PATH` — write to PATH instead of `<repo>/CLAUDE.md`
- `--update` — merge into an existing CLAUDE.md, preserving sections this skill
  does not manage; regenerate the rest
- `--force` — overwrite an existing CLAUDE.md (explicit, destructive opt-in)
- `--rules` — split topic detail into `.claude/rules/*.md` even under the budget
- `--dry-run` — return the generated content without writing any file

## Write safety (read first)

Never silently overwrite. Decide the write target like this:

1. Resolve target: `--output PATH`, else `<repo>/CLAUDE.md`.
2. Target does **not** exist → write it directly.
3. Target exists and `--force` → overwrite it (the flag is the explicit approval).
4. Target exists and `--update` → merge (see Phase 6), then write the target.
5. Target exists, no flag → **do not touch it.** Write to
   `<dir>/CLAUDE.generated.md` and report that the user should diff it against the
   current file, then re-run with `--update` or `--force`.
6. `--dry-run` → write nothing; return the content in the report.

## Workflow

### Phase 1: Setup

1. Resolve repo root and the write target per Write safety above.
2. Detect existing context: `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*`,
   `AGENTS.md`, `.cursorrules`. Note whether `AGENTS.md` exists (drives bridging).
3. Confirm `README.md` presence (used to avoid duplication).

### Phase 2: Scan the codebase

Spawn one `Explore` agent. Pass it the repo root and the full contents of
[references/scan-spec.md](references/scan-spec.md) as its instructions. It reads
manifests, task runners, CI, lint/test config, entry points, and git history, and
returns the compact structured summary that file specifies. Do not re-read what
the agent already summarized.

### Phase 3: Verify commands

For each build/test/lint/run command in the summary, confirm it is real with a
non-destructive probe (`--help`, `--version`, `make -n <target>`, a script entry
in a manifest, or its presence in CI). Drop or mark `(unverified)` anything that
cannot be confirmed. Prefer the form CI uses over the README form.

### Phase 4: Synthesize

Read [references/principles.md](references/principles.md) and
[references/section-guide.md](references/section-guide.md) before writing. Then
build the file:

1. Work section by section in the priority order from the section guide. Include a
   section only if it has real, project-specific content.
2. Apply the deletion test to **every** line: "Would removing this cause Claude to
   make a mistake?" If no, cut it.
3. Use `file:line` pointers, never pasted code. Phrase rules positively ("use Y").
   Bullets, not paragraphs. Reserve emphasis for at most a couple of lines.
4. Do not duplicate README headings (from the summary). No directory tree. No
   standard language conventions. No generic advice.
5. If `AGENTS.md` exists, bridge instead of duplicating: make the first line
   `@AGENTS.md` and add only Claude-specific content. See
   [references/modularization.md](references/modularization.md).

See [references/example.md](references/example.md) for a full worked file and a
counter-example.

### Phase 5: Budget & modularization

1. Count lines. Keep the root **under 150 lines** — this is the limit
   `review-claude-md` enforces (its C2 check), so staying under it is what makes
   the output pass that audit. The official ceiling is 200, but 150 is the binding
   target here. Aim well below it.
2. If over budget, or if `--rules` was passed, move topic detail into
   `.claude/rules/*.md` per [references/modularization.md](references/modularization.md),
   using `paths:` frontmatter to scope rules to globs. Keep commands, the
   architecture map, top gotchas, and etiquette in the root, and link each rule
   file from the root with a one-line description.

### Phase 6: Write

- Default / `--force`: write the synthesized content to the target.
- `--update`: read the existing file, keep any heading this skill does not manage
  (preserve user-authored sections verbatim), replace the managed sections with
  the freshly synthesized ones, and write the merged result. Never drop a section
  you did not generate.
- Create any `.claude/rules/*.md` files from Phase 5.
- `--dry-run`: skip all writes.

### Phase 7: Validate & iterate

Run the validator on the written file (or, for `--dry-run`, on a temp copy):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/validate-claude-md.py" "<target-file>" --human
```

Parse the result. For any `[FAIL]` check, fix the file and re-run. Iterate up to
3 rounds. The validator enforces line count, README de-duplication, no generic
advice, no directory tree, no oversized code blocks, bullet ratio, and the presence
of build/test/lint commands plus a pre-commit gate — mirroring the same checks
`review-claude-md` runs (its command checks skip automatically for AGENTS.md bridge
files). A genuinely-absent command (e.g. a project with no linter) should be
reported honestly, not invented.

### Phase 8: Report

Return a summary:

- Target path written (or the `.generated.md` fallback / dry-run notice)
- Final line count and the validator verdict (PASS, or remaining advisories)
- Sections included and any `.claude/rules/*.md` created
- If a `.generated.md` fallback was used: the exact next step (diff, then `--update`
  or `--force`)
- One or two follow-ups the human should confirm (e.g. an unverified command, a
  gotcha that needs a real `file:line`)

## Error handling

- **No manifests / unknown stack**: infer commands from CI and scripts; if still
  unknown, omit the Commands section rather than guessing, and flag it in the report.
- **Empty or trivial repo**: generate only the sections with real content (often
  just Commands). Do not pad to look complete.
- **Existing CLAUDE.md and no flag**: never overwrite — use the `.generated.md`
  fallback and tell the user how to proceed.
- **Validator keeps failing after 3 rounds**: write the best version, report the
  remaining failing checks honestly, and suggest `/review-claude-md --fix`.

## Example invocations

<example>
Generate for the current repo:

```bash
/generate-claude-md
```
</example>

<example>
Specific repo, preview without writing:

```bash
/generate-claude-md /path/to/repo --dry-run
```
</example>

<example>
Refresh an existing file, preserving custom sections:

```bash
/generate-claude-md --update
```
</example>

<example>
Force a lean rewrite and split topics into rules:

```bash
/generate-claude-md --force --rules
```
</example>
