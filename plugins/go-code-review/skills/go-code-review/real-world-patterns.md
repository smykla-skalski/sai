# Real-World Go Patterns - Code Review Reference

Source: <https://github.com/baz-scm/awesome-reviewers>

Patterns extracted from actual PR reviews in leading OSS projects.

## Testing

### Comprehensive Test Coverage (kubernetes/kubernetes)

**Check For:** Tests systematically cover all scenarios, edge cases, and feature combinations

**Pattern:**

- Every feature path has test case
- Edge cases explicitly tested
- Negative scenarios included
- Feature combinations validated

**Why:** Prevents regressions, ensures reliability

### Use Testify Assertion Libraries (vitessio/vitess)

**Check For:** Manual error checks vs testify assert/require

**Anti-pattern:**

```go
if got != want {
    t.Errorf("got %v, want %v", got, want)
}
```

**Pattern:**

```go
assert.Equal(t, want, got)
require.NoError(t, err)
```

**Why:** Improved readability, better error messages, clearer intent

## Naming Conventions

### Consistent Descriptive Naming (prometheus/prometheus)

**Check For:** Names following Go conventions, self-documenting

**Pattern:**

- Descriptive over terse
- Consistent across codebase
- Reflects actual purpose
- Follows Go idioms

**Why:** Code clarity, reduced cognitive load

### Use Semantically Clear Names (kubernetes/kubernetes)

**Check For:** Names reflecting actual functionality vs generic identifiers

**Anti-pattern:**

```go
func process(data interface{}) error
func handle(item *Thing) error
```

**Pattern:**

```go
func validatePodSpec(spec *v1.PodSpec) error
func reconcileDeployment(deploy *apps.Deployment) error
```

**Why:** Self-documenting code, clear intent

### Follow Naming Patterns (temporalio/temporal)

**Check For:** Names reflecting precise behavior and semantic meaning

**Pattern:**

- Verbs for functions: `createUser`, `validateInput`
- Nouns for types: `UserManager`, `ConfigValidator`
- Adjectives for booleans: `isValid`, `hasPermission`
- Match domain language

**Why:** Consistency, predictability, domain alignment

## Code Organization

### Extract Reusable Functions (volcano-sh/volcano)

**Check For:** Duplicate code that should be extracted

**Pattern:**

- Identify repeated logic (3+ occurrences)
- Extract to well-named function
- Single responsibility
- Clear parameters

**Anti-pattern:**

```go
// Same logic repeated in multiple places
if err := validate(x); err != nil {
    return fmt.Errorf("validation failed: %w", err)
}
// ... later ...
if err := validate(y); err != nil {
    return fmt.Errorf("validation failed: %w", err)
}
```

**Pattern:**

```go
func validateAndWrap(val Validator) error {
    if err := val.Validate(); err != nil {
        return fmt.Errorf("validation failed: %w", err)
    }
    return nil
}
```

**Why:** DRY principle, maintainability, single source of truth

### Extract Repeated Code (grafana/grafana)

**Check For:** Repeated patterns across multiple locations

**Pattern:**

- Identify similar code blocks
- Abstract common behavior
- Preserve clarity

**Why:** Reduces duplication, easier updates, fewer bugs

### Simplify Code Structure (istio/istio)

**Check For:** Opportunities to use stdlib, improve control flow

**Pattern:**

- Use stdlib functions over custom implementations
- Early returns over nested ifs
- Clear control flow
- Leverage Go idioms

**Why:** Less code, fewer bugs, better performance

## Performance

### Minimize Memory Allocations (prometheus/prometheus)

**Check For:** Unnecessary allocations, buffer reuse opportunities

**Pattern:**

- Reuse buffers via `sync.Pool`
- Preallocate slices/maps with known size
- Use efficient data structures
- Avoid repeated allocations in loops

**Example:**

```go
// Anti-pattern
for _, item := range items {
    buf := make([]byte, size) // allocates every iteration
    // use buf
}

// Pattern
buf := make([]byte, size)
for _, item := range items {
    buf = buf[:0] // reuse
    // use buf
}
```

**Why:** Reduces GC pressure, improves throughput

### Simplify Complex Algorithms (prometheus/prometheus)

**Check For:** Over-optimization, premature complexity

**Pattern:**

- Optimize only with profiling data
- Document complexity trade-offs

**Why:** Code clarity, easier debugging, prevents bugs

### Optimize Algorithmic Efficiency (volcano-sh/volcano)

**Check For:** Inefficient algorithms, wrong data structures

**Pattern:**

- Choose appropriate data structures (map vs slice vs tree)
- Consider time complexity (O(n) vs O(n²))
- Avoid unnecessary iterations
- Use indexes for lookups

**Example:**

```go
// Anti-pattern: O(n²)
for _, item := range items {
    for _, target := range targets {
        if item.ID == target.ID { ... }
    }
}

// Pattern: O(n)
targetMap := make(map[string]*Target, len(targets))
for _, t := range targets {
    targetMap[t.ID] = t
}
for _, item := range items {
    if target, ok := targetMap[item.ID]; ok { ... }
}
```

**Why:** Scales better, faster execution

## Concurrency

### Prevent Concurrent Access Races (vitessio/vitess)

**Check For:** Shared data accessed without synchronization

**Pattern:**

- Use `sync.Mutex` for shared state
- Channels for communication
- Atomic operations for simple counters
- Document locking strategy

**Anti-pattern:**

```go
type Counter struct {
    count int
}

func (c *Counter) Increment() {
    c.count++ // RACE
}
```

**Pattern:**

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

**Why:** Prevents data races, ensures correctness

## Configuration

### Configuration Validation Consistency (traefik/traefik)

**Check For:** Consistent validation patterns, appropriate types

**Pattern:**

- Validate early (fail fast)
- Use appropriate types (duration, size, enum)
- Consistent error messages
- Document constraints

**Example:**

```go
type Config struct {
    Timeout time.Duration `yaml:"timeout"`
    MaxSize int64         `yaml:"max_size"`
}

func (c *Config) Validate() error {
    if c.Timeout <= 0 {
        return errors.New("timeout must be positive")
    }
    if c.MaxSize <= 0 {
        return errors.New("max_size must be positive")
    }
    return nil
}
```

**Why:** Catches errors early, clear feedback, type safety

## Documentation

### Add Explanatory Comments (istio/istio)

**Check For:** Complex logic without explanation

**Pattern:**

- Comment WHY, not WHAT
- Explain non-obvious decisions
- Document edge cases
- Link to issues/design docs

**Example:**

```go
// Use exponential backoff with jitter to prevent thundering herd
// when multiple clients reconnect simultaneously after network partition.
// See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
backoff := time.Duration(rand.Int63n(int64(baseDelay * (1 << attempt))))
```

**Why:** Maintainability, knowledge transfer, prevents rework

## Project Sources

- **kubernetes/kubernetes**: Comprehensive testing, semantic naming
- **prometheus/prometheus**: Performance optimization, naming consistency
- **vitessio/vitess**: Testify usage, concurrency safety
- **istio/istio**: Code simplification, documentation
- **grafana/grafana**: Code extraction, DRY principle
- **volcano-sh/volcano**: Algorithm optimization, function extraction
- **traefik/traefik**: Configuration validation
- **temporalio/temporal**: Naming patterns

## Usage in Reviews

**Priority Order:**

1. **Critical:** Concurrency races, configuration validation
2. **Major:** Testing quality, naming clarity, code duplication
3. **Minor:** Performance optimization, documentation, algorithm efficiency

**When to Report:**

- Pattern clearly applies
- Improvement measurable (readability, performance, correctness)
- Consistent with project style
- Not over-engineering

**When to Skip:**

- Pattern doesn't fit context
- Would reduce clarity
- Premature optimization
- Project has different conventions
