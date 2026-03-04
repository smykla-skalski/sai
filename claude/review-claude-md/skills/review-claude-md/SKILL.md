---
name: review-claude-md
description: Audit and fix CLAUDE.md files using a tiered binary checklist based on official Anthropic best practices and community guidelines. Use when the user asks to "review CLAUDE.md", "audit CLAUDE.md", "score CLAUDE.md", "improve CLAUDE.md", or "fix CLAUDE.md".
argument-hint: "[path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]"
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Grep, Glob, Task
user-invocable: true
---

# Review CLAUDE.md

Evaluate any CLAUDE.md against a tiered binary checklist (Critical / Important / Polish), produce a categorical verdict (PASS / NEEDS WORK / FAIL), then fix all failing checks.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to repo root (default: current working directory)
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

1. Identify target repo root (from argument or cwd)
2. Find all CLAUDE.md files: root, `.claude/CLAUDE.md`, `CLAUDE.local.md`, subdirectories
3. Find `.claude/rules/*.md` files
4. Note git-tracked vs gitignored status

### Phase 2: Codebase Context

Read the codebase to understand what the CLAUDE.md SHOULD contain:

- **Build system**: Makefile, package.json, Cargo.toml, go.mod, pyproject.toml
- **Test config**: jest.config, pytest.ini, vitest.config, test directories
- **Lint/format**: .eslintrc, biome.json, .prettierrc, rustfmt.toml
- **CI/CD**: .github/workflows/, .gitlab-ci.yml
- **README.md**: Check for content that might be duplicated
- **Directory structure**: Top-level layout and component relationships
- **Git conventions**: `git log --oneline -20` for commit message patterns
- **Existing .claude/rules/**: Already modularized content

### Phase 3: Automated Checks

Run the deterministic validation scripts and collect their JSON output:

```bash
"$SKILL_DIR/scripts/validate-claudemd.sh" "$TARGET_DIR"
"$SKILL_DIR/scripts/validate-commands.sh" "$TARGET_DIR"
```

Where `$SKILL_DIR` is this skill's directory and `$TARGET_DIR` is the repo being reviewed. Parse each JSON line — `pass: false` results map to the corresponding checklist criterion.

### Phase 4: Manual Evaluation

Read `references/rubric.md` in full before starting this phase.

For each criterion not already covered by automated scripts, evaluate as binary pass/fail:

1. Read the check description and source reference
2. Examine the relevant section of the CLAUDE.md
3. Record the result with specific evidence (quote the line or describe the absence)
4. If `--thorough`, also evaluate Polish tier checks

Consult `references/sources.md` for authoritative source URLs when citing findings.

### Phase 5: Synthesize Verdict

Think step by step before declaring the verdict:

1. List all Critical results — any FAIL?
2. Count Important FAILs — 3 or more?
3. Apply the verdict logic above
4. Write a 2-3 sentence chain-of-thought explaining the reasoning

### Phase 6: Report

Output the verdict per the template in `references/output-format.md`.

### Phase 7: Fix

If `--score-only` was NOT passed:

1. Address every failing Critical and Important check
2. Apply these principles when rewriting:
   - Every line must pass "would removing this cause mistakes?"
   - Bullets over paragraphs
   - `file:line` references over embedded code
   - "Use Y instead of X" over "Never use X"
   - Only non-obvious info — skip what Claude infers from code
   - Commands are the highest-value items
   - No README content duplication
3. Create `.claude/rules/` files if root exceeds 150 lines
4. Target: under 150 lines (ideally 50-100 for root)

### Phase 8: Final Report

1. Re-run automated checks against the fixed CLAUDE.md
2. Re-evaluate manual checks
3. Output the post-fix report per `references/output-format.md`
4. If verdict is still not PASS, iterate: fix remaining issues and re-evaluate

## Good vs Bad Examples

Read `references/examples.md` for detailed comparison pairs. Key patterns:

**Commands** — Good: Specific commands with focused-test variant (`npm test -- --testPathPattern="auth"`). Bad: "Run tests" with no actual command.

**Architecture** — Good: Component relationships with file:line pointers (`src/services/` calls `src/db/`, never imports from `src/api/`). Bad: Plain file tree with no relationship explanations.

**Gotchas** — Good: "Payment service uses eventual consistency — check `transaction.status` before assuming completion (see `services/payment.ts:45`)." Bad: "Handle errors gracefully."

## Example Invocations

```bash
# Default audit
/review-claude-md

# Specific repo, verbose
/review-claude-md /path/to/repo --verbose

# Verdict only, no fixes
/review-claude-md --score-only

# Include Polish tier
/review-claude-md --thorough

# Combine flags
/review-claude-md /path/to/repo --verbose --thorough
```
