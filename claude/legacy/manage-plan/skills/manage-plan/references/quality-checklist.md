# Implementation Plan Quality Checklist

Binary checklist for validating implementation plans. Each check is pass/fail.

## Table of Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements for executor-ready plans.

| ID  | Check                                                                          |
|:----|:-------------------------------------------------------------------------------|
| C1  | All 7 mandatory sections present (Title, Workflow Commands, Git Configuration, |
|     | Progress Tracker, Technical Context, Execution Plan, Files to Modify)          |
| C2  | Title uses `# Implementation Spec:` with action-oriented summary (5-10 words)  |
| C3  | Workflow Commands table has Lint, Fix/Format, Test -- all verified             |
| C4  | Git Configuration table has Base Branch, Feature Branch, Push Remote           |
| C5  | No anti-patterns: placeholder text, empty sections, commands as questions      |

### How to evaluate

Scan for each of the 7 mandatory section headers. Verify the title line starts with `# Implementation Spec:` and the summary is 5-10 words. Check the Workflow Commands table for actual runnable commands (not TBD or placeholder). Check Git Configuration for concrete values (not "ask user"). Scan the entire plan for `{something}` placeholder patterns, empty sections (header with no content or just "N/A"), and commands phrased as questions.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect plan quality.

| ID  | Check                                                                     |
|:----|:--------------------------------------------------------------------------|
| I1  | Progress Tracker has exactly one `**NEXT**:` pointer and blockers section |
| I2  | Progress Tracker is max 20 lines with checkbox format                     |
| I3  | Technical Context includes problem/solution context and rationale         |
| I4  | Technical Context uses pseudocode not verbatim code                       |
| I5  | Execution Plan phases each have 3-7 steps, last step is verification      |
| I6  | Execution Plan steps are specific actions with file paths where needed    |
| I7  | Execution Plan phases have ≤10 files each                                 |
| I8  | Files to Modify uses repo-relative paths (not absolute)                   |
| I9  | No re-investigation needed -- Technical Context has all necessary context |
| I10 | Commands verified -- executor can run lint/test without finding commands  |
| I11 | First action clear -- NEXT pointer points to specific, actionable step    |
| I12 | No "TBD", "ask user", or placeholder patterns remaining                   |

### How to evaluate

Check the Progress Tracker for exactly one `**NEXT**:` marker and a blockers section. Count lines in the tracker (must be ≤20) and verify checkbox format. Read Technical Context for problem/solution framing and rationale; flag verbatim code blocks that should be pseudocode. Count steps in each Execution Plan phase (3-7 required) and verify the last step is a verification action. Check each step for specificity -- "Implement feature" or "Fix bugs" fails. Count files per phase (≤10). Verify all paths in Files to Modify are repo-relative. Assess self-containment: could an executor start immediately without re-investigating the codebase, discovering commands, or resolving ambiguity?

---

## Polish Checks

Informational findings. These do not affect the verdict.

| ID  | Check                                                              |
|:----|:-------------------------------------------------------------------|
| P1  | Open Questions are answerable and not blockers                     |
| P2  | No duplicated context between Technical Context and Execution Plan |
| P3  | Vague steps avoided ("Implement feature", "Make it work")          |

### How to evaluate

Review Open Questions to confirm each can be answered without external input. Diff Technical Context against Execution Plan for duplicated paragraphs. Scan step descriptions for vague phrasing.

---

## Verdict Logic

Any Critical fails              --> FAIL
3+ Important fails              --> NEEDS WORK
All Critical pass, ≤2 Important --> PASS
