---
name: review-plan
description: Review implementation plans for completeness, quality, and executor-readiness against planning-agent template standards. Use when auditing plans before execution, after creating implementation specs, or when assessing whether an executor session can start immediately.
argument-hint: "<plan-file-path|@file> [--fix]"
allowed-tools: Read, Write, Edit, Grep, Glob, AskUserQuestion
user-invocable: true
---

# Review Plan

Audit implementation plans against the planning-agent template standards. Validates all 7 mandatory sections, workflow commands, git configuration, progress tracker, execution plan phases, and self-containment for executor handoff. Produces a verdict-based quality report with executor-readiness assessment.

## Arguments

Parse from `$ARGUMENTS`:

| Flag         | Default | Purpose                                             |
|:-------------|:--------|:----------------------------------------------------|
| (positional) | —       | Plan file path or inline content. Prompt if omitted |
| `--fix`      | off     | Apply auto-fixable corrections in-place             |

## Workflow

### Phase 1: Input resolution

1. Parse `$ARGUMENTS` for file path, inline content, and flags.
2. If no input provided, use AskUserQuestion to ask which plan file to review.
3. Determine input type:
   - Starts with `# Implementation Spec:` or `---` → treat as inline content
   - Contains `.md` or path separators → treat as file path, read with Read tool
4. If file path: read the file and verify success.
5. If file not found, report error immediately.
6. If content does not appear to be an implementation plan, use AskUserQuestion to confirm the file is intended as a plan.

### Phase 2: Read reference material

1. Read `references/checklist.md` for the full quality checklist.
2. Read `references/grading-rubric.md` for verdict criteria and output format.

### Phase 3: Mandatory sections check

Verify all 7 mandatory sections exist:

1. **Title**: `# Implementation Spec:` with action-oriented summary (5-10 words)
2. **Workflow Commands**: table with Lint, Fix/Format, Test — all verified, no placeholders
3. **Git Configuration**: table with Base Branch, Feature Branch, Push Remote — no placeholders
4. **Progress Tracker**: has `**NEXT**:` pointer, max 20 lines, checkbox format
5. **Technical Context**: problem/solution context, file paths, architectural decisions
6. **Execution Plan**: phases with steps, verification at end of each phase
7. **Files to Modify**: repo-relative paths with brief reasons

Flag missing sections as CRITICAL.

### Phase 4: Section quality validation

For each section that exists, check quality criteria from the checklist:

- **Workflow Commands**: all commands runnable (not TBD or placeholder)
- **Git Configuration**: remote and branch names specified (not "ask user")
- **Progress Tracker**: exactly one `**NEXT**:` item, blockers section present
- **Technical Context**: uses pseudocode not verbatim code, includes rationale
- **Execution Plan phases**: each phase has 3-7 steps, last step is verification
- **Execution Plan steps**: specific actions with file paths where applicable
- **Open Questions**: answerable, not blockers
- **Files to Modify**: paths are repo-relative, not absolute

### Phase 5: Anti-pattern scan

Scan for each anti-pattern from the checklist:

- Placeholder text (`{something}` patterns)
- Empty sections (header with no content or just "N/A")
- Vague steps ("Implement feature", "Make it work", "Fix bugs")
- Missing verification (phase without test step at end)
- Overloaded phases (>7 steps or >10 files)
- Absolute paths (full system paths instead of repo-relative)
- Multiple NEXT pointers (more than one `**NEXT**:` marker)
- Commands as questions ("What is the lint command?")
- Duplicated context (same info in Technical Context and Execution Plan)

Record line numbers for each finding.

### Phase 6: Self-containment assessment

Evaluate whether a fresh executor session can start immediately:

- No re-investigation needed (Technical Context has all context)
- Commands verified (executor can run lint/test without searching)
- Branch ready (git config complete, naming clear)
- First action clear (NEXT pointer is specific and actionable)
- No ambiguity (no "TBD", "ask user", or placeholder patterns)

### Phase 7: Synthesize verdict

Apply the verdict logic from `references/grading-rubric.md`:

1. List all Critical results — any FAIL?
2. Count Important FAILs — 3 or more?
3. Apply verdict logic:
   - Any Critical fails → FAIL
   - 3+ Important fails → NEEDS WORK
   - All Critical pass, ≤2 Important → PASS
   - Polish checks → informational only
4. Write a 2-3 sentence chain-of-thought explaining the reasoning
5. Determine executor-readiness (Yes/No)

### Phase 8: Report generation

Output the quality report using the format from `references/grading-rubric.md`:

1. Summary table (verdict, counts, executor-ready status)
2. Critical Issues with line numbers and execution impact
3. Warnings with line numbers and executor impact
4. Suggestions with line numbers and benefit
5. Tiered checklist results with `[PASS]`/`[FAIL]` per check (Critical, Important, Polish)
6. Chain of Thought section with reasoning
7. Verdict section with summary and executor-start assessment

### Phase 9: Auto-fix (if --fix)

If `--fix` flag is set:

1. Apply fixes for auto-fixable issues:
   - Convert absolute paths to repo-relative
   - Remove duplicate NEXT pointers (keep first)
   - Add missing verification steps to phases
2. Use Edit tool to apply changes.
3. Re-run validation on the fixed file.
4. Report what was fixed and what requires manual attention.

## Example

```bash
/review-plan tmp/tasks/add-retry-logic/implementation_plan.md
```

Output: verdict-based quality report with executor-readiness assessment, findings, and recommendations.

```bash
/review-plan tmp/tasks/add-retry-logic/implementation_plan.md --fix
```

Output: auto-fixes applied, then re-validated quality report.
