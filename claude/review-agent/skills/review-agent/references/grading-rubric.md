# Agent Quality Verdict Logic

## Verdict Criteria

```text
Any Critical fails              → FAIL
3+ Important fails              → NEEDS WORK
All Critical pass, ≤2 Important → PASS
Polish checks                   → informational only
```

## Output Format

```markdown
# Agent Quality Review: {agent-name}

## Summary

| Metric      | Value                    |
|:------------|:-------------------------|
| **Verdict** | PASS / NEEDS WORK / FAIL |
| **Path**    | {path}                   |

### Critical

- [PASS] C1: Description includes trigger keyword and scenarios
- [FAIL] C2: Missing Constraints section
...

### Important

- [PASS] I1: Role statement is specific and action-oriented
- [FAIL] I3: No concrete examples found
...

### Polish

- [INFO] P1: Density Rules table present
...

### Chain of Thought

{2-3 sentence reasoning leading to verdict}

### Verdict: {VERDICT}

{one-line summary}
```

## Density Rules

| Bad                                                                                                  | Good                                                 |
|:-----------------------------------------------------------------------------------------------------|:-----------------------------------------------------|
| "The description field is missing a trigger keyword which means Claude won't know when to invoke it" | "description: missing trigger keyword"               |
| "Consider adding more edge cases to handle various scenarios"                                        | "[LINE 45] Edge Cases: missing uncertainty handling" |
| "The agent looks mostly good overall"                                                                | "Verdict: PASS — 0 critical, 1 important"            |
| "You might want to think about adding..."                                                            | "Add `STATUS: NEEDS_INPUT` pattern"                  |
