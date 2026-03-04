# Implementation Plan Quality Checklist

Binary checklist for evaluating implementation plans. Each check is pass/fail.

## Table of Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)
- [Anti-Patterns](#anti-patterns)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements for executor-readiness.

| ID  | Check                                                            |
|:----|:-----------------------------------------------------------------|
| C1  | Title has `# Implementation Spec:` with action-oriented summary  |
| C2  | Workflow Commands table with verified commands (no placeholders) |
| C3  | Git Configuration table complete (no placeholders)               |
| C4  | Progress Tracker has exactly one `**NEXT**:` pointer             |
| C5  | Technical Context has problem/solution context with rationale    |
| C6  | Execution Plan has phases with verification steps                |
| C7  | Files to Modify has repo-relative paths                          |

### How to evaluate

Verify the plan begins with `# Implementation Spec:` followed by a 5-10 word action-oriented summary. Check the Workflow Commands table for Lint, Fix/Format, and Test rows — each must contain a runnable command, not TBD or placeholder text. Confirm the Git Configuration table has Base Branch, Feature Branch, and Push Remote with concrete values. Search for `**NEXT**:` markers and confirm exactly one exists. Read the Technical Context section for problem statement, solution approach, and architectural rationale. Verify each Execution Plan phase ends with a verification step. Confirm all paths in Files to Modify are repo-relative.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect plan quality.

| ID  | Check                                                        |
|:----|:-------------------------------------------------------------|
| I1  | All workflow commands runnable (not TBD)                     |
| I2  | Git remote and branch names specified (not "ask user")       |
| I3  | Progress Tracker has blockers section                        |
| I4  | Technical Context uses pseudocode not verbatim code          |
| I5  | Each phase has 3-7 steps, last is verification               |
| I6  | Steps have specific actions with file paths                  |
| I7  | Open Questions are answerable, not blockers                  |
| I8  | File paths are repo-relative, not absolute                   |
| I9  | No re-investigation needed (self-contained)                  |
| I10 | First action clear (NEXT pointer is specific and actionable) |

### How to evaluate

Run each workflow command mentally or check for obvious non-commands (TBD, TODO, placeholder). Verify git remote is a concrete name (e.g., `origin`) and branch follows a naming convention, not "ask user" or similar. Look for a blockers subsection in Progress Tracker. Check Technical Context for raw code dumps vs pseudocode summaries. Count steps per phase and confirm 3-7 range with the last being a verification step. Verify execution steps reference specific files. Review Open Questions for dependency on external input. Confirm all file paths are repo-relative. Assess whether the plan is self-contained or requires additional investigation. Check that the NEXT pointer targets a specific, actionable step.

---

## Polish Checks

Informational findings. These do not affect the pass/fail verdict.

| ID  | Check                                        |
|:----|:---------------------------------------------|
| P1  | No ambiguity (no "TBD", "ask user" patterns) |
| P2  | No duplicated context between sections       |
| P3  | Phases not overloaded (≤7 steps, ≤10 files)  |

### How to evaluate

Scan for "TBD", "ask user", "TODO", or `{placeholder}` patterns anywhere in the plan. Diff Technical Context against Execution Plan for repeated paragraphs or tables. Count steps and file references per phase — flag any exceeding the limits.

---

## Anti-Patterns

| Anti-Pattern           | Detection                                                | Severity  |
|:-----------------------|:---------------------------------------------------------|:----------|
| Placeholder text       | `{something}` patterns remaining in content              | Critical  |
| Empty sections         | Section header with no content or just "N/A"             | Critical  |
| Vague steps            | "Implement feature", "Make it work", "Fix bugs"          | Important |
| Missing verification   | Phase without verification/test step at end              | Important |
| Overloaded phases      | Phase with >7 steps or >10 files                         | Polish    |
| Absolute paths         | Full system paths instead of repo-relative               | Important |
| Multiple NEXT pointers | More than one `**NEXT**:` marker                         | Critical  |
| Commands as questions  | "What is the lint command?" instead of actual command    | Critical  |
| Duplicated context     | Same information in Technical Context and Execution Plan | Polish    |
