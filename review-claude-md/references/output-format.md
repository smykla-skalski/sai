# Output Format Templates

## Initial Report

```
## CLAUDE.md Review

**File**: <path>
**Lines**: <count>
**Verdict**: PASS | NEEDS WORK | FAIL

### Critical
- [PASS] C1: Build/test/lint commands present and correct
- [FAIL] C2: 247 lines exceeds 150 limit
...

### Important
- [PASS] I1: Architecture describes component relationships
- [FAIL] I3: No project-specific gotchas found
...

### Polish (--thorough only)
- [INFO] P1: No focused-test command documented
...

### Chain of Thought
<reasoning explaining how each check was evaluated and how the verdict was determined>

### Verdict: <VERDICT>
<summary — e.g., "4 Important checks failed (threshold: 3)" or "All Critical passed, 1 Important failed">
```

## Post-Fix Report

```
## Post-Fix Review

**File**: <path>
**Lines**: <count> (was: <old_count>)
**Verdict**: PASS

### Changes Made
- <change 1>
- <change 2>
...

### Rules Files Created
- .claude/rules/<name>.md — <purpose>
...
```
