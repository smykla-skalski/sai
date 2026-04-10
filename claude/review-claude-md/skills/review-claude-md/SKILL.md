---
name: review-claude-md
description: Audit and fix CLAUDE.md files using a tiered binary checklist based on official Anthropic best practices and community guidelines. Use when the user asks to "review CLAUDE.md", "audit CLAUDE.md", "score CLAUDE.md", "improve CLAUDE.md", or "fix CLAUDE.md".
argument-hint: "[path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: Bash, Edit, Glob, Read, Task, Write
user-invocable: true
context: fork
agent: general-purpose
---

<!-- justify: CF-side-effect Edit/Write fix detected issues in CLAUDE.md with user approval -->

# Review CLAUDE.md

Evaluate any CLAUDE.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix all failing checks.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to repo root (default: current working directory)
- `--score-only` — Report verdict without fixing
- `--fix` — Fix all failing checks (default behavior)
- `--verbose` — Show chain-of-thought reasoning for each check
- `--thorough` — Include Polish tier in the report

## Verdict logic

Read [references/rubric.md](references/rubric.md) for the full tiered checklist and verdict thresholds (Critical, Important, Polish tiers).

## Workflow

### Phase 1: Discovery

1. Identify target repo root (from argument or cwd)
2. Find all CLAUDE.md files: root, `.claude/CLAUDE.md`, `CLAUDE.local.md`, subdirectories
3. Find [.claude/rules/](.claude/rules/) `*.md` files
4. Note git-tracked vs gitignored status

### Phase 2: Codebase Context

Spawn an `Explore` agent to scan the target repository. Pass the agent: the repo root path.

Agent reads: Makefile, package.json, Cargo.toml, go.mod, pyproject.toml, CI configs (.github/workflows/, .gitlab-ci.yml), README.md, test configs (jest.config, pytest.ini, vitest.config), lint configs (.eslintrc, biome.json, .prettierrc, rustfmt.toml).
Also reads: top-level directory structure, `git log --oneline -20`, [.claude/rules/](.claude/rules/) contents.

Agent returns ONLY a structured summary with these fields:

- Build system and commands found
- Test framework and test commands
- Lint/format tool and commands
- CI provider and workflow names
- Existing [.claude/rules/](.claude/rules/) files and their topics
- Commit message convention observed
- README sections that overlap with CLAUDE.md content

Use this summary to inform Phase 3-4 checks. Do not re-read any files the agent already summarized.

### Phase 3: Automated Checks

Spawn a `general-purpose` agent to run validation scripts. Pass the agent: target CLAUDE.md path, `$TARGET_DIR`, and paths to both scripts:

```bash
"${CLAUDE_SKILL_DIR}/scripts/validate-claudemd.sh" "$TARGET_DIR"
"${CLAUDE_SKILL_DIR}/scripts/validate-commands.sh" "$TARGET_DIR"
```

Run both scripts, parse the JSON output, and return ONLY an array of `{check, pass, detail}` results. Each `pass: false` result maps to the corresponding checklist criterion.

Use these results directly in Phase 5 (Synthesize Verdict). Do not re-run the scripts in the main context.

### Phase 4: Manual Evaluation

Re-read [references/rubric.md](references/rubric.md) in full before starting this phase to prevent drift from the checklist criteria.

For each criterion not already covered by automated scripts, evaluate as binary pass/fail:

1. Read the check description and source reference
2. Examine the relevant section of the CLAUDE.md
3. Record the result with specific evidence (quote the line or describe the absence)
4. If `--verbose`, show chain-of-thought reasoning for each check
5. If `--thorough`, also evaluate Polish tier checks

Read [references/sources.md](references/sources.md) for authoritative source URLs when citing findings.

### Phase 5: Synthesize Verdict

Think step by step before declaring the verdict:

1. List all Critical results — any FAIL?
2. Count Important FAILs — 3 or more?
3. Apply the verdict logic above
4. Write a 2-3 sentence chain-of-thought explaining the reasoning

### Phase 6: Report

Read [references/output-format.md](references/output-format.md) for the verdict template. Output the verdict per this template.

### Phase 7: Fix

If `--score-only` was NOT passed (`--fix` mode, the default):

1. Address every failing Critical and Important check
2. Re-read [references/sources.md](references/sources.md) for rewriting principles before editing because fixes that violate source guidelines create new failures
3. Create [.claude/rules/](.claude/rules/) files if root exceeds 150 lines
4. Target: under 150 lines (ideally 50-100 for root)

### Phase 8: Final Report

Spawn a `general-purpose` agent to re-evaluate the fixed CLAUDE.md. Pass the agent: paths to the fixed CLAUDE.md, both validation scripts, `$TARGET_DIR`, the Phase 2 codebase summary, and a link to [references/rubric.md](references/rubric.md).

Agent instructions:

1. Re-run both automated check scripts and parse JSON output
2. Re-evaluate manual checks from [references/rubric.md](references/rubric.md)
3. Apply the verdict logic and produce a post-fix report per [references/output-format.md](references/output-format.md)
4. Return ONLY the post-fix verdict report

If the verdict is still not PASS, iterate in the main context: fix remaining issues using Edit, then spawn a new evaluation agent.

## Good vs Bad Examples

Read [references/examples.md](references/examples.md) for good vs bad comparison pairs covering commands, architecture, gotchas, and format sections.

## Example Invocations

<example>
Default audit (current directory):

```bash
/review-claude-md
```
</example>

<example>
Specific repo with verbose output:

```bash
/review-claude-md /path/to/repo --verbose
```
</example>

<example>
Score-only and thorough modes:

```bash
/review-claude-md --score-only
/review-claude-md --thorough
/review-claude-md /path/to/repo --verbose --thorough
```
</example>
