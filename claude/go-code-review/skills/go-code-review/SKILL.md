---
name: go-code-review
description: Auto-review Go code for 100+ common mistakes when analyzing .go files, discussing Go patterns, or reviewing PRs with Go code. Checks error handling, concurrency, interfaces, performance, testing, and stdlib usage.
allowed-tools: Read
user-invocable: true
---

# Go Code Review Skill

Auto-triggers when reviewing Go code to catch common mistakes from https://100go.co/

## Scope

Apply to `.go` files and Go PRs. Not a substitute for `go vet` or `golangci-lint` — use both alongside this review.

## Review Process

1. Read Go file(s) mentioned
2. Read [knowledge-base.md](knowledge-base.md) in full before step 4 — contains all 100+ mistake references
3. Read [real-world-patterns.md](real-world-patterns.md) in full before step 4 — contains OSS project patterns
4. Check each file against both references; identify every applicable mistake
5. Report each mistake with:
   - Severity (Critical/Major/Minor)
   - Location (file:line)
   - Mistake # from knowledge base
   - Suggested fix
   - Code example if applicable
6. Re-read each flagged location to confirm accuracy — remove false positives, escalate any missed Critical mistakes

## Severity Tiers

**Critical (fix before merge):**
- Error handling (#48-54) — silent failures are undebuggable after the fact; callers cannot recover
- Concurrency (#58, 69, 70, 74) — races surface only under load, typically in production
- Resource leaks (#26, 28, 76, 79) — accumulate until OOM or connection pool exhaustion

**Major (should fix):**
- Interface design (#5-7) — wrong-side interfaces lock in dependencies that are hard to untangle later
- Goroutine lifecycle (#62, 63) — leaked goroutines accumulate until process memory is exhausted
- Testing (#83, 86) — flaky tests mask real bugs and slow CI feedback loop

**Minor (consider):**
- Code organization (#1, 2, 15) — readability impact only, no correctness risk
- Performance (#21, 27, 39) — matters at scale; verify with profiling before flagging

## Edge Cases

- **No mistakes found:** State explicitly — do not invent issues to appear thorough
- **Ambiguous severity:** Flag as Critical and explain the context-dependency in the report
- **Non-.go files:** Skip silently; do not apply Go-specific checks to other file types

<example>
Input: `fetchUser` in handler.go returns raw error with no context

```go
func fetchUser(id int) (*User, error) {
    row := db.QueryRow("SELECT * FROM users WHERE id=?", id)
    var u User
    if err := row.Scan(&u.Name, &u.Email); err != nil {
        return nil, err
    }
    return &u, nil
}
```

Output:

**Mistake**: #49 — Ignoring When to Wrap an Error
**Severity**: Major
**Location**: handler.go:5
**Fix**: `return nil, fmt.Errorf("fetchUser id=%d: %w", id, err)`
**Why**: Without `%w`, callers cannot trace origin; `errors.Is`/`errors.As` chains break
</example>
