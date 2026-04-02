---
name: test-writer
description: Write tests that verify behavior (not implementation), use table-driven/parameterized patterns, and minimize mocking. Triggers when asked to write tests, add test coverage, or create test files. Also triggers when reviewing existing tests for quality.
argument-hint: "[file-or-function-to-test] [--review] [--lang go|python|ts|java|rust]"
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# Test Writer

Write tests that survive refactoring, catch real bugs, and don't waste maintenance effort.

**Philosophy:** Test what the code does, not how it does it. If you refactor internals and tests break — the tests are wrong, not the code.

## Arguments

Parse from `$ARGUMENTS`:
- **target** — file path, function name, or module to test
- `--review` — review existing tests for anti-patterns instead of writing new ones
- `--lang` — override language detection (go, python, ts, java, rust)

If no arguments: ask what to test.

## Phase 1: Understand the Code

1. **Read the target** — understand what it does, its public API, inputs/outputs
2. **Identify behaviors** — list what the code guarantees to callers. Think in Given/When/Then:
   - "Given [state], when [action], then [outcome]"
   - Each behavior = one test (or one row in a table)
3. **Find boundaries** — identify external dependencies (DB, HTTP, filesystem, clock, randomness)
4. **Check existing tests** — use Glob to find test files, Read them, understand what's covered
5. **Detect language** — from file extension or `--lang` flag

**Behavior identification checklist:**
- What does a caller/user care about? (outcomes, not internals)
- What are the success cases?
- What are the error/edge cases? (null, empty, overflow, boundary values)
- What side effects are observable? (not internal method calls)

## Phase 2: Design Test Structure

Read the knowledge base before writing:

```bash
cat "$(dirname "$0")/references/testing-principles.md" 2>/dev/null || cat references/testing-principles.md
```

### Decision: Table-Driven or Individual Tests?

Use **table-driven** when:
- Multiple cases share the same test logic (same arrange/act/assert shape)
- Testing input/output mapping, validation, parsing, transformation
- Cases differ only in data, not in assertion logic

Use **individual tests** when:
- Each case needs different setup/teardown
- Each case asserts different things (state vs error vs side-effect)
- Complex scenarios that would require conditionals in the test loop

### Decision: What to Mock?

**Mock only external boundaries:**
- Database/storage calls
- HTTP/network requests
- Filesystem I/O
- System clock / `time.Now()`
- Random number generators
- Message queues, email gateways

**Do not mock:**
- Internal collaborators (classes/functions you own)
- Data structures, value objects, DTOs
- Things you can use for real (in-memory, fast, deterministic)

**Preference hierarchy (try in order):**
1. Real implementation (if fast + deterministic)
2. Fake (in-memory implementation of same interface)
3. Stub (hardcoded return values)
4. Mock (behavior verification) — absolute last resort

**If you need >2 mocks, stop and reconsider** — the code may need restructuring, not more mocks.

## Phase 3: Write Tests

### Structure: Arrange-Act-Assert

Every test follows AAA with blank line separation:

<example>
```
// Arrange — set up test data and preconditions

// Act — execute the single behavior under test

// Assert — verify the expected outcome
```
</example>

### Naming Convention

Test names describe behavior, not method names:

<example>
- `TestTransferFunds_RejectsInsufficientBalance` (Go)
- `test_rejects_withdrawal_when_balance_insufficient` (Python)
- `it("rejects withdrawal when balance is insufficient")` (JS/TS)
</example>

**Format:** `[action]_[scenario]_[expected outcome]` or `should_[behavior]_when_[condition]`

### Table-Driven Patterns by Language

Read [references/language-patterns.md](references/language-patterns.md) for idiomatic table-driven test patterns in Go, Python, TypeScript, Java, and Rust.

### Assertions

- **Assert outcomes** — return values, state changes, observable side-effects
- **Never assert interactions** — don't verify internal method call order
- **Use concrete literals** — `want: "Hello, Alice"` not `want: fmt.Sprintf("Hello, %s", name)`
- **Multiple assertions OK** if they verify facets of the same behavior
- **No logic in assertions** — no string concatenation, no computation, no conditionals

### Edge Cases Checklist

Always consider:
- `null`/`nil`/`undefined` inputs
- Empty string, empty slice/array, empty map
- Boundary values (0, -1, max int, min int)
- Unicode, emoji, special characters in strings
- Duplicate entries where uniqueness expected
- Concurrent access if applicable

## Phase 4: Quality Check

Before finishing, verify each test against this checklist:

### Behavior Tests (must pass ALL)
- [ ] Test name describes a behavior/requirement, not a method name
- [ ] Assertions check outcomes (state, return values), not interactions
- [ ] Test would survive internal refactoring without changes
- [ ] No `verify()` on internal method calls
- [ ] Can explain what this tests without reading production code

### Table Quality (if table-driven)
- [ ] Every case has a descriptive name (not "case 1")
- [ ] No conditional logic in the test loop
- [ ] Expected values are concrete literals, not computed
- [ ] One table = one behavior (not mixing validation + formatting + error handling)
- [ ] Table struct has <=8 fields (otherwise restructure)

### Mock Discipline
- [ ] Only external boundaries are mocked (DB, HTTP, clock, filesystem)
- [ ] No internal collaborators mocked
- [ ] No data structures/value objects mocked
- [ ] <=2 mocks per test (if more: reconsider design)
- [ ] Using real objects or fakes where possible

### General Quality
- [ ] AAA structure with blank line separation
- [ ] No logic in test code (no if/for/switch)
- [ ] Each test is independent — runs in any order
- [ ] No flakiness sources (time, randomness, network)
- [ ] Error paths tested, not just happy path

## Phase 5: Review Mode (--review)

When `--review` flag is set, analyze existing tests for anti-patterns:

### Anti-Pattern Detection

Use Grep to scan for these smells and report with file:line references:

1. **Change detectors** — tests that mirror implementation structure, verify internal call order
2. **Mock explosion** — tests with 3+ mocks, especially mocking internal collaborators
3. **Missing table opportunities** — 3+ tests with identical structure differing only in data
4. **Obscure tests** — hard to understand what's being tested (magic numbers, unclear names)
5. **Conditional test logic** — if/switch inside test methods
6. **General fixture** — shared setup with fields most tests don't use
7. **Fragile tests** — coupled to implementation (private field access, internal API calls)
8. **Missing edge cases** — no error path testing, no boundary values
9. **Computed expected values** — expected values derived from same logic as production code
10. **Interaction verification** — `verify()`/`assert_called_with()` on non-boundary dependencies

### Review Output Format

<example>
```markdown
## Test Review: [file]

### Critical (must fix)
- **[anti-pattern]** at line N: [explanation + fix suggestion]

### Improvement (should fix)
- **[anti-pattern]** at line N: [explanation + fix suggestion]

### Opportunities
- Lines N-M: could consolidate into table-driven test
- Missing coverage: [behavior not tested]
```
</example>

## Hard Rules

<!-- justify: I27 aggressive emphasis is intentional in this constraints section — these are the skill's core invariants -->

1. **Do not test implementation** — if you catch yourself writing `verify(mock.someMethod())` on an internal dependency, stop
2. **Do not compute expected values** — hardcode them as literals
3. **Do not add conditional logic to tests** — split into separate tests/cases
4. **Do not mock internal collaborators** — use real objects
5. **Do not name tests after methods** — name them after behaviors
6. **Table-driven by default** when 3+ cases share the same assertion shape
7. **Every test must be readable standalone** — no jumping to helpers to understand what's tested (DAMP > DRY)
8. **One behavior per test** — one "when", one "then"
