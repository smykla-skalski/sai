---
name: review-agent
description: Review Claude Code subagent definitions for quality compliance against template standards. Use when auditing agents before committing, after creating or modifying agents, or when checking existing agent quality. Also for validating frontmatter, section order, constraints, and anti-patterns.
argument-hint: "<agent-file-path|@file> [--fix]"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
user-invocable: true
---

# Review Agent

Audit Claude Code subagent definitions against the subagent template standards. Validates frontmatter schema, system prompt structure, section ordering, anti-patterns, and completeness. Produces a verdict-based quality report with severity-ranked findings.

## Arguments

Parse from `$ARGUMENTS`:

| Flag         | Default | Purpose                                              |
|:-------------|:--------|:-----------------------------------------------------|
| (positional) | —       | Agent file path or inline content. Prompt if omitted |
| `--fix`      | off     | Apply auto-fixable corrections in-place              |

## Workflow

### Phase 1: Input resolution

1. Parse `$ARGUMENTS` for file path, inline content, and flags.
2. If no input provided, use AskUserQuestion to ask which agent file to review.
3. Determine input type:
   - Starts with `---` (frontmatter) → treat as inline agent content
   - Contains `.md` or `.claude/` → treat as file path, read with Read tool
4. If file path: read the file and verify it was read successfully.
5. If file not found, report error immediately.

### Phase 2: Read reference material

1. Read `references/checklist.md` for the full quality checklist.
2. Read `references/grading-rubric.md` for verdict criteria and output format.

### Phase 3: Frontmatter validation

1. Parse YAML frontmatter between `---` markers.
2. If no frontmatter found, flag as CRITICAL (not a valid agent definition).
3. Check each frontmatter field against the checklist:
   - `name`: lowercase, kebab-case, descriptive
   - `description`: has trigger keyword, lists 2-3 scenarios, states value
   - `tools`: does NOT include AskUserQuestion, minimal set
   - `model`: appropriate for complexity

### Phase 4: System prompt validation

1. Verify all mandatory sections exist in order:
   - Role statement → Expertise → Constraints → Workflow → Edge Cases → Output Format → Examples → Done When
2. Check section contents against checklist requirements:
   - Constraints: uses bold+em-dash format, has NEVER/ALWAYS/ZERO keywords, includes uncertainty handling
   - Workflow: 3-7 numbered steps, includes verification
   - Edge Cases: covers empty input, partial completion, multiple items, uncertainty
   - Output Format: concrete structure with placeholders (not prose)
   - Examples: good example with `<example type="good">`, bad with `<why_bad>` and `<correct>`
   - Done When: 4-6 measurable criteria with checkboxes
3. Check optional sections are present when applicable (Modes of Operation, Decision Tree, Density Rules).

### Phase 5: Anti-pattern scan

Scan for each anti-pattern from the checklist:

- Vague role ("helpful assistant", "AI that helps")
- Missing or empty constraints
- Implicit assumptions (instructions assuming unprovided context)
- Placeholder text (`{something}` patterns)
- Negative-only framing ("don't X" without "do Y")
- AskUserQuestion in tools list
- Single-scenario description
- Value-less description
- Prose output format
- Unmeasurable Done When criteria

Record line numbers for each finding.

### Phase 6: Synthesize verdict

Apply the verdict logic from `references/grading-rubric.md`:

- Evaluate each checklist item as PASS or FAIL
- Apply verdict criteria: any Critical fail = FAIL, 3+ Important fails = NEEDS WORK, otherwise PASS
- Write chain-of-thought reasoning leading to the verdict

### Phase 7: Report generation

Output the quality report using the format from `references/grading-rubric.md`:

1. Summary table (verdict, path)
2. Tiered checklist results — [PASS]/[FAIL] per check for Critical, Important, and [INFO] for Polish
3. Chain of thought (2-3 sentence reasoning)
4. Overall verdict with one-line summary

### Phase 8: Auto-fix (if --fix)

If `--fix` flag is set:

1. Apply fixes for auto-fixable issues only:
   - Reorder sections to match template
   - Add missing uncertainty handling to Constraints
   - Fix description to include trigger keyword
2. Use Edit tool to apply changes.
3. Re-run validation on the fixed file.
4. Report what was fixed and what requires manual attention.

## Example

```bash
/review-agent .claude/agents/session-manager.md
```

Output: verdict-based quality report with tiered checklist, chain of thought, and overall verdict.

```bash
/review-agent .claude/agents/session-manager.md --fix
```

Output: auto-fixes applied, then re-validated verdict-based quality report.
