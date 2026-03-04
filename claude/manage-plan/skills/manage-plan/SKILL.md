---
name: manage-plan
description: Create, modify, or transform implementation plans with codebase investigation and built-in quality validation. Use when starting new implementation tasks, improving existing plans, or converting specs/RFCs into actionable execution plans for executor sessions.
argument-hint: "<task-description|plan-path|doc-path> [--create|--modify|--transform]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion
user-invocable: true
---

# Manage Plan

Investigate codebases and produce self-contained implementation plans for executor sessions. Supports creating plans from task descriptions, modifying existing plans, and transforming specs/RFCs into actionable execution plans. Includes automatic quality validation.

## Arguments

Parse from `$ARGUMENTS`:

| Flag          | Default | Purpose                                            |
|:--------------|:--------|:---------------------------------------------------|
| (positional)  | ---     | Task description, plan file path, or document path |
| `--create`    | auto    | Force create mode (new plan from task description) |
| `--modify`    | auto    | Force modify mode (improve existing plan)          |
| `--transform` | auto    | Force transform mode (convert spec/RFC to plan)    |

## Workflow

### Phase 1: Input Resolution & Mode Detection

1. Parse `$ARGUMENTS` for file path, description, and flags.
2. If no input provided, use AskUserQuestion to ask what to plan.
3. Determine mode (auto-detect if no flag):
   - Path to existing plan (contains `Implementation Spec:` or plan-like structure) -> **Modify**
   - Path to spec/RFC/document -> **Transform**
   - No file path (task description only) -> **Create**

### Phase 2: Read Reference Material

1. Read `references/plan-template.md` for the plan template, decision trees, and phase guidelines.
2. Read `references/quality-checklist.md` for the quality checklist to validate against.

### Phase 3: Codebase Investigation

For **Create** and **Transform** modes, investigate the codebase:

1. Discover workflow commands using the decision tree from `references/plan-template.md`:

     ```text
     Makefile exists?
     +-- YES -> parse targets (lint, test, format, check)
     +-- NO  -> Taskfile.yml, package.json, .mise.toml, or CI config
     ```

2. Discover git configuration:

     ```text
     upstream remote exists?
     +-- YES -> use upstream (fork workflow)
     +-- NO  -> use origin (direct contributor)
     ```

3. Identify files to modify using Grep and Glob.
4. Understand architectural context by reading key files.
5. Verify all discovered commands actually work (run them).

### Phase 4: Plan Construction

Based on mode:

**Create mode**:

1. Use the plan template from `references/plan-template.md` as the skeleton.
2. Fill in Workflow Commands with verified commands from Phase 3.
3. Fill in Git Configuration with discovered remote and branch info.
4. Create Progress Tracker with `**NEXT**:` pointer.
5. Write Technical Context with investigation findings.
6. Design Execution Plan phases (3-7 steps each, verification at end).
7. List Files to Modify with repo-relative paths.

**Modify mode**:

1. Read the existing plan.
2. Identify gaps against the quality checklist.
3. Verify commands still work, update if needed.
4. Improve each section while preserving the plan's intent.
5. Apply changes using Edit tool.

**Transform mode**:

1. Read the source document (do NOT modify the source).
2. Extract requirements, scope, and constraints.
3. Investigate the codebase (Phase 3) to ground the plan in reality.
4. Map to the plan template structure.
5. Write the new plan.

### Phase 5: Quality Validation

1. Run the quality checklist from `references/quality-checklist.md` against the output.
2. Check all 7 mandatory sections exist and meet requirements.
3. Check self-containment criteria (executor can start immediately).
4. Scan for anti-patterns.
5. If issues found:
   - Auto-fix what can be fixed (absolute paths to repo-relative, duplicate NEXT pointers).
   - Report remaining issues that need manual attention.

### Phase 6: Output

1. Present the completed implementation plan.
2. Show quality validation results (verdict, findings, executor-readiness).
3. Suggest next step: run the plan with an executor session.

## Example

```bash
/manage-plan "Add retry logic to the API client with exponential backoff"
```

Output: new implementation plan with investigated commands, git config, and phased execution plan.

```bash
/manage-plan tmp/tasks/add-retry-logic/implementation_plan.md --modify
```

Output: improved plan with changes applied in place and quality report.

```bash
/manage-plan docs/rfcs/api-pagination.md --transform
```

Output: new implementation plan grounded in codebase investigation, source RFC untouched.
