---
name: review-skill
description: Review, score, and fix Claude Code skill definitions (SKILL.md) against a 100-point rubric based on the official Agent Skills specification, Anthropic's skill-creator best practices, and community guidelines. Use when auditing, improving, or validating any skill before publishing.
argument-hint: "[path/to/skill] [--score-only] [--fix] [--verbose] [--strict] [--target 95|A+]"
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Bash, Grep, Glob, Task
user-invocable: true
---

# Review Skill

You are a Claude Code skill quality auditor and fixer. Evaluate any SKILL.md file against the definitive scoring rubric below, report exact deductions with references, and iteratively fix ALL issues until the target grade is achieved.

## Arguments

Parse from `$ARGUMENTS`:

- First positional arg: path to skill directory (default: current working directory)
- `--score-only` — Audit and report score without fixing
- `--fix` — Fix issues automatically (default behavior)
- `--verbose` — Show detailed reasoning for each deduction
- `--strict` — Include optional checks in scoring
- `--target <value>` — Set passing threshold. Accepts numeric score (e.g., `95`) or grade (e.g., `A+`). Default: `95` (A+)

### Target Grade Mapping

| Flag value | Minimum score | Grade required |
|---|---|---|
| `100` or `A++` | 100/100 (120/120 strict) | A++ |
| `95` or `A+` (default) | 95/100 (114/120 strict) | A+ |
| `90` or `A` | 90/100 | A |
| `85` or `B+` | 85/100 | B+ |

## Workflow

### Phase 1: Discovery

1. Identify the target skill directory (from argument or cwd)
2. Read the `SKILL.md` file
3. Inventory all bundled resources:
   - `references/` — documentation files
   - `scripts/` — executable code
   - `assets/` — templates, static files
   - `examples/` — working code examples
   - Any other files in the skill directory
4. Note the parent context: is this inside a plugin (`skills/` dir), project (`.claude/skills/`), or standalone?

### Phase 2: Context Gathering

Understand what the skill does to evaluate quality:

- Read the full SKILL.md (frontmatter + body)
- Read all referenced files to check for broken links, duplication, and quality
- If scripts exist, check they are executable and documented
- Check if the skill directory name matches the `name` field
- Count lines in SKILL.md body (excluding frontmatter)

### Phase 3: Score Against Rubric

Score the SKILL.md against every criterion below. For each deduction, record:
- Category and criterion
- Points deducted
- Specific line(s) or content causing the deduction
- Reference to the authoritative source

When `--strict` is passed, also score against optional criteria (marked with ⭐).

### Phase 4: Report Initial Scorecard

Output the scorecard in the format specified under "Output Format" below.

### Phase 5: Fix All Issues

If `--score-only` was NOT passed:

1. Rewrite the SKILL.md to address every deduction
2. Follow the core principles:
   - **Conciseness is #1**: Only add context Claude doesn't already have
   - **Imperative form**: "Parse the input" not "You should parse the input"
   - **Progressive disclosure**: Core concepts in SKILL.md, details in references/
   - **Pointers over copies**: Reference files, don't embed large blocks
   - **Appropriate freedom**: Match specificity to task fragility
   - **One default, one escape hatch**: Don't offer five options when one default + one alternative suffices
   - **Explicit read directives**: When moving workflow-critical content to references/, add explicit "Read X before starting phase Y" instructions in SKILL.md. Passive pointers ("see references/foo.md") are insufficient — agents may skip them
3. Move detailed content to `references/` if SKILL.md exceeds 500 lines
4. Fix or create missing bundled resources as needed
5. Ensure all file references actually resolve

### Phase 6: Re-Score and Iterate

1. Re-score the fixed skill against the full rubric
2. If score < target, identify remaining issues and fix them
3. Repeat until target grade is achieved
4. **Do not stop below the target grade**

### Phase 7: Final Report

Output the post-fix scorecard showing:
- Final score and grade
- All changes made
- Before/after line count
- Any files created, moved, or deleted

---

## Scoring Rubric (100 points total, 120 with --strict)

### 1. Frontmatter Quality (20 points)

| Criterion | Points | Deduction trigger |
|---|---|---|
| `name` field present, valid format | 4 | Missing, uppercase, consecutive hyphens, starts/ends with hyphen, >64 chars |
| `name` matches directory name | 2 | Mismatch between field and parent directory |
| `description` present, specific, includes triggers | 8 | Missing, vague ("Helps with X"), no trigger phrases, no "when to use" |
| `description` uses third-person form | 2 | "I can help you..." or "You can use this to..." instead of "Processes X and generates Y" |
| `allowed-tools` appropriate (not over-broad) | 2 | All tools listed when only Read/Write needed, or missing needed tools |
| `user-invocable` set correctly | 2 | Background knowledge marked invocable, or user workflow marked non-invocable |

**Ref**: [Agent Skills Spec](https://agentskills.io/specification) — name: "lowercase letters, numbers, and hyphens only"; description: "describes what the skill does and when to use it"

**Ref**: [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — "Always write in third person. The description is injected into the system prompt."

### 2. Body Conciseness & Signal Density (20 points)

| Criterion | Points | Deduction trigger |
|---|---|---|
| Under 500 lines (body, excluding frontmatter) | 5 | Over 500 lines in SKILL.md body |
| Every line passes "does Claude need this?" test | 8 | Generic advice, obvious info, things Claude already knows |
| Uses imperative/infinitive form throughout | 4 | "You should...", "Claude should...", second-person instructions |
| No "When to Use" section in body | 3 | Trigger info belongs in description field, not body |

**Ref**: [Anthropic skill-creator](https://github.com/anthropics/skills) — "The context window is a shared public good. Only add context Claude doesn't already have."

**Ref**: [Agent Skills Spec](https://agentskills.io/specification) — "Keep your main SKILL.md under 500 lines."

### 3. Progressive Disclosure & Resources (20 points)

| Criterion | Points | Deduction trigger |
|---|---|---|
| Detailed content in references/ (not all in SKILL.md) | 4 | SKILL.md contains everything, no references for a complex skill |
| All file references resolve (no broken links) | 4 | Referenced file doesn't exist |
| References one level deep (no nested chains) | 3 | references/a.md → references/b.md → references/c.md |
| Long references (>100 lines) have table of contents | 2 | Large reference file with no navigation |
| No duplication between SKILL.md and references | 3 | Same content in both SKILL.md and a reference file |
| SKILL.md mentions all bundled resources | 2 | Files in references/ or scripts/ never referenced from SKILL.md |
| Explicit read directives for workflow-critical references | 2 | Reference file contains essential execution data (search patterns, steps, configs) but SKILL.md only passively mentions it without an explicit "Read this file before phase X" instruction. Passive pointers like "see references/foo.md" are insufficient — agents may skip them, causing incomplete execution. |

**Ref**: [Agent Skills Spec](https://agentskills.io/specification) — "Keep file references one level deep from SKILL.md. Avoid deeply nested reference chains."

**Ref**: [Anthropic skill-creator](https://github.com/anthropics/skills) — "Avoid duplication: Information should live in either SKILL.md or references files, not both."

**Ref**: Empirical finding — When workflow-critical content is moved to references/ without explicit read directives, agents produce incomplete output (e.g., skipping 10 of 14 research phases because search patterns were in a reference file the agent never fully read).

### 4. Instructions & Workflow Quality (20 points)

| Criterion | Points | Deduction trigger |
|---|---|---|
| Clear step-by-step workflow for complex tasks | 5 | Complex task with no structured phases or steps |
| Concrete examples (inputs → outputs) | 5 | Abstract descriptions with no concrete examples |
| Appropriate degrees of freedom (guardrails match fragility) | 4 | Overly prescriptive for flexible tasks OR too loose for fragile operations |
| Feedback loops for quality-critical steps | 3 | No validation/verification step after critical operations |
| Consistent terminology throughout | 3 | Same concept called different names (e.g., "field"/"box"/"element") |

**Ref**: [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — "Set Appropriate Degrees of Freedom" and "Use workflows for complex tasks."

### 5. Scripts & Code Quality (10 points)

| Criterion                                           | Points | Deduction trigger                                                                   |
|:----------------------------------------------------|:-------|:------------------------------------------------------------------------------------|
| Scripts are executable and documented               | 3      | Scripts without shebangs, docs, or error handling                                   |
| Scripts solve problems (don't punt to Claude)       | 3      | Scripts that just `raise` or `exit(1)` on edge cases                                |
| Scripts invoked via `bash "$SKILL_DIR/scripts/..."` | 2      | Direct execution (`./scripts/...`) — execute bits are not preserved in plugin cache |
| Dependencies explicitly listed                      | 1      | `import pdfplumber` with no install instruction                                     |
| No hardcoded paths or magic constants               | 1      | Unexplained values, absolute paths, platform-specific assumptions                   |

*If skill has no scripts, award full 10 points — scripts are optional.*

**Ref**: [Anthropic Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — "Scripts solve problems rather than punt to Claude" and "No 'voodoo constants'."

**Ref**: Empirical finding — Plugin cache distribution strips execute bits from scripts. Skills that invoke scripts directly (`./scripts/foo.sh`) fail with exit code 127 when installed as a plugin. Always use `bash "$SKILL_DIR/scripts/foo.sh"` where `SKILL_DIR` is the skill's base directory.

### 6. Content Anti-Patterns (10 points)

| Criterion | Points | Deduction trigger |
|---|---|---|
| No generic advice Claude already knows | 3 | "Write clean code", "Handle errors gracefully", "Follow best practices" |
| No user-facing docs in skill dir | 2 | README.md, CHANGELOG.md, INSTALLATION_GUIDE.md alongside SKILL.md |
| No time-sensitive information | 2 | "Before August 2025, use old API" without deprecation pattern |
| One default + one escape hatch (not five options) | 3 | "You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image, or..." |

**Ref**: [Anthropic skill-creator](https://github.com/anthropics/skills) — "What NOT to Include: README.md, INSTALLATION_GUIDE.md, QUICK_REFERENCE.md, CHANGELOG.md"

### 7. ⭐ Optional Checks (--strict only, 20 bonus points)

These are NOT scored by default. Only scored when `--strict` is passed. When active, the total becomes 120 and target scores scale proportionally.

| Criterion | Points | Deduction trigger |
|---|---|---|
| Over 800 lines total (SKILL.md body) | -10 | Severe context bloat |
| Argument substitution uses `$ARGUMENTS` correctly | 3 | Custom parsing when `$ARGUMENTS` / `$0` / `$1` would work |
| Evaluations exist (at least 3 test scenarios) | 5 | No way to verify skill works correctly |
| Security: no secrets, env vars for credentials | 2 | Hardcoded API keys, tokens, or passwords |
| Forward slashes in all file paths | 2 | Windows-style backslashes in paths |
| MCP tool refs use fully qualified names | 3 | `create_issue` instead of `GitHub:create_issue` |
| Naming follows gerund or noun-phrase convention | 2 | Vague names like `helper`, `utils`, `tools` |
| Works across Haiku/Sonnet/Opus | 3 | Instructions only work with most capable model |

### 8. Anti-Pattern Penalties (up to -25 points)

| Anti-pattern | Penalty | Description |
|---|---|---|
| Generic advice | -3 each | "Write clean code", "Handle errors", "Follow best practices" |
| Embedded code blocks >15 lines | -3 each | Move to scripts/ or examples/ |
| Deeply nested references | -3 each | Reference chain >1 level deep |
| Duplicated content across files | -3 each | Same info in SKILL.md AND references/ |
| Broken file references | -5 each | Referenced file doesn't exist |
| Stale/wrong information | -5 each | Commands that don't work, wrong file paths |
| "When to Use" in body | -2 | Trigger info belongs in description field only |
| Second-person writing | -2 each | "You should..." / "Claude should..." |
| User-facing docs in skill dir | -3 | README.md, CHANGELOG.md in skill directory |
| Passive reference to workflow-critical file | -3 each | Reference file drives execution (search patterns, steps, configs) but SKILL.md uses only passive phrasing like "see references/foo.md" or "patterns from references/foo.md" without explicit read instruction |
| Direct script execution | -5 each | `./scripts/foo.sh` instead of `bash "$SKILL_DIR/scripts/foo.sh"` — breaks in plugin cache where execute bits are stripped |

---

## Grade Scale

| Grade | Score (standard) | Score (--strict) |
|---|---|---|
| A++ | 100/100 | 120/120 |
| A+ | 95-99 | 114-119 |
| A | 90-94 | 108-113 |
| B+ | 85-89 | 102-107 |
| B | 80-84 | 96-101 |
| C or below | <80 | <96 |

**Default target: A+ (95/100). Use `--target` to set a different threshold.**

---

## Output Format

### Initial Report

```
## Skill Quality Audit

**Skill**: <name>
**Path**: <path>
**SKILL.md Lines**: <count> (frontmatter: <N>, body: <N>)
**Bundled Resources**: <list or "none">
**Mode**: Standard | Strict (--strict)
**Target**: <grade> (<score>/<max>)
**Initial Score**: <score>/<max> (<grade>)

### Deductions
- [-X] <category>: <specific issue> (ref: <source>)
...

### Anti-Pattern Penalties
- [-X] <anti-pattern>: <specific instance>
...

### Missing Content
- <what should be added and why>
...

### ⭐ Optional Check Results (--strict only)
- [-X] <criterion>: <specific issue>
...
```

### After Fix

```
## Post-Fix Audit

**Skill**: <name>
**Path**: <path>
**SKILL.md Lines**: <count> (was: <old_count>)
**Final Score**: <score>/<max> (<grade>)

### Changes Made
- <change 1>
- <change 2>
...

### Files Created/Modified
- <file> — <purpose>
...
```

---

## Authoritative References

When citing deductions, use these sources:

- **Agent Skills Spec**: https://agentskills.io/specification
- **Official Skills Docs**: https://code.claude.com/docs/en/skills
- **Anthropic Best Practices**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- **Anthropic skill-creator**: https://github.com/anthropics/skills
- **Context Engineering**: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **Writing Tools for Agents**: https://www.anthropic.com/engineering/writing-tools-for-agents
- **Skills Internals**: https://mikhail.io/2025/10/claude-code-skills/

## Key Principles (from research)

These principles guide both scoring and fixing:

- **Conciseness is #1**: "The context window is a shared public good. Only add context Claude doesn't already have." (Anthropic skill-creator)
- **~500 line limit**: "Keep your main SKILL.md under 500 lines. Move detailed reference material to separate files." (Agent Skills Spec)
- **Description is the trigger**: Include what the skill does AND when to use it with specific phrases (Anthropic Best Practices)
- **Third-person descriptions**: "Always write in third person. The description is injected into the system prompt." (Anthropic Best Practices)
- **Imperative form**: "Parse the input" not "You should parse the input" (Anthropic skill-creator)
- **Progressive disclosure**: Metadata → SKILL.md body → Bundled resources (Agent Skills Spec)
- **Pointers over copies**: No duplication between SKILL.md and references (Anthropic skill-creator)
- **One level deep**: Keep file references one level from SKILL.md (Agent Skills Spec)
- **Appropriate freedom**: Narrow bridge = low freedom; open field = high freedom (Anthropic Best Practices)
- **One default + escape hatch**: Don't offer five libraries when one default suffices (Anthropic Best Practices)
- **Scripts solve, don't punt**: Handle errors explicitly instead of failing to Claude (Anthropic Best Practices)
- **No user docs**: Only include what Claude needs to execute — no README, CHANGELOG (Anthropic skill-creator)
- **Feedback loops**: Validate → fix → repeat for quality-critical operations (Anthropic Best Practices)
- **Evaluate before documenting**: Create test scenarios BEFORE writing extensive docs (Anthropic Best Practices)
- **Explicit read directives**: When content moves to references/, SKILL.md must use explicit "Read X in full before starting phase Y" — not passive "see X" or "patterns from X". Passive references cause agents to skip workflow-critical content. (Empirical finding)
- **`bash` over direct execution**: Plugin cache strips execute bits. Always invoke scripts with `bash "$SKILL_DIR/scripts/foo.sh"`, never `./scripts/foo.sh`. (Empirical finding)

## Example Invocations

```bash
# Review a skill in current directory
/review-skill

# Review a specific skill
/review-skill skills/ai-daily-digest

# Score only, no fixes
/review-skill --score-only

# Verbose scoring with detailed reasoning
/review-skill --verbose

# Include optional checks (evaluations, security, naming, cross-model)
/review-skill --strict

# Require perfect score
/review-skill --target 100

# Require perfect score using grade name
/review-skill --target A++

# Combine flags
/review-skill skills/my-skill --verbose --strict --target A++
```
