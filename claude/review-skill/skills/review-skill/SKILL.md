---
name: review-skill
description: Review and fix Claude Code skill definitions (SKILL.md) using a tiered binary checklist based on the Agent Skills specification, Anthropic best practices, and community guidelines. Use when auditing, improving, or validating any skill before publishing.
argument-hint: "[path/to/skill] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: Bash, Edit, Glob, Grep, Read, Task, Write
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

Read [references/skill-structure.md](references/skill-structure.md) to understand the canonical skill layout before evaluating.

1. Identify the target skill directory (from argument or cwd)
2. Read the SKILL.md file
3. Inventory all bundled resources (`references/`, `scripts/`, `assets/`, `examples/`)
4. Note parent context: plugin (`skills/` dir), project (`.claude/skills/`), or standalone

### Phase 2: Automated Checks

Run the validation script and collect its JSON output:

```bash
"${CLAUDE_SKILL_DIR}/scripts/validate.sh" "$TARGET_DIR"
```

`$TARGET_DIR` is the skill directory being reviewed. The script runs all checks by default. Subcommands `frontmatter` and `structure` run subsets. Parse each JSON line — `pass: false` results map to the corresponding checklist criterion. The final line is always a summary with total/passed/failed counts. The script also calls `${CLAUDE_SKILL_DIR}/scripts/check-fork-candidate.sh` internally for the P9 fork candidate analysis.

### Phase 3: Manual Evaluation

Spawn a `general-purpose` evaluation agent with these inputs:

- Target skill directory path
- Path to [references/checklist.md](references/checklist.md)
- The `--thorough` flag value (true/false)
- List of check IDs already covered by automated scripts (from Phase 2)

The agent reads the checklist, the target SKILL.md, and all bundled resources in the target skill directory. It evaluates each criterion not covered by automated checks as binary pass/fail with evidence.

The agent returns ONLY structured results - one entry per criterion:

```text
<id>: <PASS|FAIL> — <evidence quote or absence description>
```

Do not duplicate checklist evaluation in the main context. Use the agent's returned results directly in Phase 4.

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
   - Invoke scripts directly with the `${CLAUDE_SKILL_DIR}` prefix (never `./scripts/` or `bash` prefix)
3. Fix or create missing bundled resources as needed
4. Verify all file references resolve after changes

### Phase 7: Final Report

Spawn a `general-purpose` verification agent with these inputs:

- Target skill directory path (with fixes applied)
- Path to validate.sh script: `${CLAUDE_SKILL_DIR}/scripts/validate.sh`
- Path to [references/checklist.md](references/checklist.md)
- The `--thorough` flag value

The agent re-runs validate.sh AND re-evaluates all manual checks against the fixed skill. It returns ONLY the post-fix report:

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

Display the agent's returned report. If verdict is still not PASS, iterate: fix remaining issues in the main context and spawn a new verification agent.

## Good vs Bad Examples

Read [references/examples.md](references/examples.md) for detailed comparison pairs. Key patterns:

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
