# Implementation Plan Verdict Rubric

## Verdict Criteria

```text
Any Critical fails              → FAIL
3+ Important fails              → NEEDS WORK
All Critical pass, ≤2 Important → PASS
Polish checks                   → informational only
```

## Output Format

```markdown
# Implementation Plan Review: {spec-title}

## Summary

| Metric              | Value                    |
|:--------------------|:-------------------------|
| **Verdict**         | PASS / NEEDS WORK / FAIL |
| **Critical Issues** | {count}                  |
| **Warnings**        | {count}                  |
| **Suggestions**     | {count}                  |
| **Executor Ready**  | {Yes/No}                 |

## Critical Issues (MUST fix before execution)

- **[LINE {n}]** {Issue description} — {Why this blocks execution}

## Warnings (SHOULD fix)

- **[LINE {n}]** {Issue description} — {Impact on executor}

## Suggestions (CONSIDER)

- **[LINE {n}]** {Improvement opportunity} — {Benefit}

## Checklist Results

### Critical

- [PASS] C1: Title has `# Implementation Spec:` with action-oriented summary
- [FAIL] C2: Workflow Commands table missing verified commands
...

### Important

- [PASS] I1: All workflow commands runnable
- [FAIL] I3: Progress Tracker missing blockers section
...

### Polish

- [INFO] P1: No ambiguity detected
...

### Chain of Thought

{2-3 sentence reasoning explaining how the verdict was determined}

### Verdict: {VERDICT}

{One paragraph: what to fix first, priority order, whether executor can start}

| Metric             | Value    |
|:-------------------|:---------|
| **Executor Ready** | {Yes/No} |
```

## Density Rules

| Bad                                                              | Good                                                      |
|:-----------------------------------------------------------------|:----------------------------------------------------------|
| "The workflow commands section appears to have placeholder text" | "Workflow Commands: placeholder in Lint command"          |
| "Consider whether the technical context has enough information"  | "Technical Context: missing rationale for approach"       |
| "The plan looks mostly complete but could use some improvements" | "Verdict: PASS — 0 critical, 2 important, executor-ready" |
| "Phase 1 seems quite large and might be difficult to complete"   | "Phase 1: 9 steps (limit 7) — split required"             |
