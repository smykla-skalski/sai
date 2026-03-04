---
name: review-skill
description: Review and fix Claude Code skill definitions (SKILL.md) using a tiered binary checklist based on the Agent Skills specification, Anthropic best practices, and community guidelines. Use when auditing, improving, or validating any skill before publishing.
argument-hint: "[path/to/skill] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Grep, Glob, Task
user-invocable: true
---

# Review Skill

Evaluate any SKILL.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix all failing checks.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to skill directory (default: current working directory)
- `--score-only` — Report verdict without fixing
- `--fix` — Fix all failing checks (default behavior)
- `--verbose` — Show chain-of-thought reasoning for each check
- `--thorough` — Include Polish tier in the report

## Verdict Logic

```text
Any Critical fails              → FAIL
3+ Important fails              → NEEDS WORK
All Critical pass, ≤2 Important → PASS
Polish checks                   → informational (with --thorough)
```

## Workflow

### Phase 1: Discovery

Read `references/skill-structure.md` to understand the canonical skill layout before evaluating.

1. Identify the target skill directory (from argument or cwd)
2. Read the SKILL.md file
3. Inventory all bundled resources (`references/`, `scripts/`, `assets/`, `examples/`)
4. Note parent context: plugin (`skills/` dir), project (`.claude/skills/`), or standalone

### Phase 2: Automated Checks

Run the validation script and collect its JSON output:

```bash
"$SKILL_DIR/scripts/validate.sh" "$TARGET_DIR"
```

Where `$SKILL_DIR` is this skill's directory and `$TARGET_DIR` is the skill being reviewed. The script runs all checks by default. Subcommands `frontmatter` and `structure` run subsets. Parse each JSON line — `pass: false` results map to the corresponding checklist criterion. The final line is always a summary with total/passed/failed counts.

### Phase 3: Manual Evaluation

Read `references/checklist.md` in full before starting this phase.

For each criterion not already covered by the automated scripts, evaluate as binary pass/fail:

1. Read the check description and source
2. Examine the relevant section of the target SKILL.md
3. Record the result with specific evidence (quote the line or describe the absence)
4. If `--thorough`, also evaluate Polish tier checks

### Phase 4: Synthesize Verdict

Think step by step before declaring the verdict:

1. List all Critical results — any FAIL?
2. Count Important FAILs — 3 or more?
3. Apply the verdict logic above
4. Write a 2-3 sentence chain-of-thought explaining the reasoning

### Phase 5: Report

Output the verdict report:

```text
## Skill Review

**Skill**: <name>
**Path**: <path>
**Lines**: <count> (body, excluding frontmatter)
**Verdict**: PASS | NEEDS WORK | FAIL

### Critical
- [PASS] C1: Description includes what + when-to-use
- [FAIL] C2: Body 623 lines, exceeds 500 limit
...

### Important
- [PASS] I1: Imperative form throughout
- [FAIL] I3: No concrete examples found
...

### Polish (--thorough only)
- [INFO] P1: References have TOC
...

### Chain of Thought
<reasoning leading to verdict>

### Verdict: <VERDICT>
<summary>
```

### Phase 6: Fix

If `--score-only` was NOT passed:

1. Address every failing Critical and Important check
2. Apply these principles when rewriting:
   - Only add context Claude doesn't already have
   - Imperative form: "Parse the input" not "You should parse the input"
   - Move detail-heavy content to `references/` if SKILL.md exceeds 300 lines
   - Use explicit read directives: "Read X before starting phase Y"
   - Invoke scripts directly via `"$SKILL_DIR/scripts/..."` (never `./scripts/` or `bash "$SKILL_DIR/scripts/..."`)
3. Fix or create missing bundled resources as needed
4. Verify all file references resolve after changes

### Phase 7: Final Report

1. Re-run automated checks against the fixed skill
2. Re-evaluate manual checks
3. Output the post-fix report:

```text
## Post-Fix Review

**Skill**: <name>
**Path**: <path>
**Lines**: <count> (was: <old_count>)
**Verdict**: <verdict>

### Changes Made
- <change 1>
- <change 2>
...

### Files Created/Modified
- <file> — <purpose>
...
```

4. If verdict is still not PASS, iterate: fix remaining issues and re-evaluate

## Good vs Bad Examples

Read `references/examples.md` for detailed comparison pairs. Key patterns:

**Description** — Good: "Aggregate daily AI news from research papers and newsletters. Use when running a daily news roundup." Bad: "Helps with AI news."

**Progressive disclosure** — Good: 30-line workflow in SKILL.md, search patterns extracted to a reference file. Bad: 400-line SKILL.md with every search query inline.

**Read directives** — Good: "Read the search patterns file in full before starting Phase 3." Bad: "Search patterns are available in the search patterns file."

**Grading style** — Good: "Check each function for missing error handling. List issues with file path and fix." Bad: "Evaluate criteria with numeric scores and percentage weights, then derive a letter grade."

## Example Invocations

```bash
# Review a skill in the current directory
/review-skill

# Review a specific skill
/review-skill skills/ai-daily-digest

# Verdict only, no fixes
/review-skill --score-only

# Verbose with chain-of-thought per check
/review-skill --verbose

# Include Polish tier
/review-skill --thorough

# Combine flags
/review-skill skills/my-skill --verbose --thorough
```
