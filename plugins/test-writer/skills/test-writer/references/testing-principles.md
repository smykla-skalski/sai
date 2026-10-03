# Testing Principles Knowledge Base

Quick-reference for the test-writer skill. Internalize these before writing tests.

---

## The Core Mental Model

> The trigger for a new test is a new **behavior/requirement**, not a new class or method.
> — Ian Cooper, "TDD, Where Did It All Go Wrong?"

> If I refactor the internals of my module without changing any external behavior, how many tests break?
> Zero = testing behavior. Many = testing implementation.

---

## Behavior vs Implementation — Quick Decision

Ask yourself:
1. If I refactor internals, does this test break? YES = implementation test
2. Does this test use verify() on internal methods? YES = implementation test
3. Could a caller describe what this test checks? NO = implementation test
4. Does the test name describe a business rule? NO = probably implementation test
5. Am I mocking more than module boundaries? YES = implementation test

---

## Test Double Preference Hierarchy

```
1. Real implementation  ← if fast (<1ms) and deterministic, always use this
2. Fake                 ← in-memory implementation of same interface
3. Stub                 ← hardcoded return values, only for external boundaries
4. Mock                 ← behavior verification, ABSOLUTE last resort
```

Why this order matters:
- Real objects catch integration bugs mocks hide
- Fakes maintain state across calls (mocks don't)
- Stubs at least don't assert on HOW things were called
- Mocks couple tests to implementation — every refactor breaks them

---

## What Makes a Good Test Name

The test name is a specification. Reading all test names should produce a readable description of the system's behavior.

**Pattern:** `[subject]_[scenario]_[expected]` or `should_[behavior]_when_[condition]`

| Bad | Good |
|-----|------|
| `testProcess` | `TestProcess_TransfersFundsBetweenAccounts` |
| `test_validate` | `test_rejects_empty_email_address` |
| `it("works")` | `it("returns 404 for unknown user")` |

---

## Table-Driven Test Rules

**Use when:** Cases share the same assertion shape, differ only in data
**Don't use when:** Cases need different assertion logic, setup, or verification

### Structure Rules
1. Always include a descriptive `name` field — first field in struct
2. Group inputs together, then expected outputs
3. Expected values are concrete literals, NEVER computed
4. One table = one behavior under test
5. <=8 fields per test case struct (otherwise use functional modifiers or split)
6. No conditional logic in the test loop body

### The Complexity Canary
> If the test table is hard to write, the function is too complex.
> Convoluted tables signal the SUT needs refactoring.

---

## Mock Discipline

### Only Mock External Boundaries

```
VALID mock targets:          INVALID mock targets:
├── Database                 ├── Domain objects
├── HTTP/network             ├── Value objects / DTOs
├── Filesystem               ├── Internal helpers
├── System clock             ├── Data structures
├── Random generators        ├── Your own classes
└── Message queues           └── Anything fast + deterministic
```

### "Don't Mock What You Don't Own"
Don't mock third-party libraries directly. Wrap external deps in your own thin adapter, mock that. Test the adapter with integration tests.

### When >2 Mocks Are Needed
If a test needs 3+ mocks, the code under test likely has too many responsibilities. Fix the design, don't add more mocks.

---

## Edge Cases Checklist

Always test these boundaries:

**Inputs:**
- null/nil/undefined
- Empty string, empty collection, empty map
- Single element collections
- Very large inputs (overflow, max int)
- Negative numbers where positive expected
- Unicode, emoji, special characters
- Whitespace-only strings

**State:**
- Duplicate entries where uniqueness expected
- Concurrent access / race conditions
- Resource exhaustion (full disk, connection limit)

**Time:**
- Timezone boundaries (midnight, DST)
- Leap years, Feb 29
- Clock skew, out-of-order timestamps

**Numbers:**
- Boundary values: 0, -1, max, min, max+1, min-1
- Floating point precision
- Division by zero

---

## Test Smells Quick Reference

| Smell | Signal | Fix |
|-------|--------|-----|
| Change detector | Test mirrors production code | Assert outcomes, not structure |
| Mock explosion | 3+ mocks in one test | Use real objects, refactor SUT |
| General fixture | setUp has fields most tests ignore | Use builders, inline setup |
| Conditional logic | if/switch in test body | Split into separate tests |
| Fragile test | Breaks on refactor without behavior change | Test through public API |
| Computed expected | `expected: fmt.Sprintf(...)` | Use literal: `expected: "Hello, Alice"` |
| Obscure test | Can't tell what's tested in 10 seconds | Better names, inline data |
| Assertion roulette | Multiple undocumented assertions | Add messages or split tests |

---

## Sources

- Kent Beck — Programmer Test Principles, Canon TDD
- Ian Cooper — TDD, Where Did It All Go Wrong? (InfoQ)
- Google — Software Engineering at Google (Ch. 12-13)
- Martin Fowler — Mocks Aren't Stubs, Practical Test Pyramid
- Vladimir Khorikov — Unit Testing: Principles, Practices, Patterns
- Eric Elliott — Mocking is a Code Smell
- Hynek Schlawack — Don't Mock What You Don't Own
- James Shore — Testing Without Mocks
- Dave Cheney — Prefer Table Driven Tests
