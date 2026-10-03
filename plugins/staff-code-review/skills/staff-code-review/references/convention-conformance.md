# Convention Conformance & Code Reuse — Deep Reference

Reference material for Agent 6. Use this checklist to systematically evaluate whether a PR follows repository conventions and reuses existing code.

## Table of Contents

1. [Naming Conventions](#naming-conventions)
2. [Code Reuse & Duplication](#code-reuse--duplication)
3. [Structural Patterns](#structural-patterns)
4. [Test Conventions](#test-conventions)
5. [Project Structure](#project-structure)
6. [Investigation Techniques](#investigation-techniques)

---

## Naming Conventions

Naming divergence is a leading indicator of convention drift. Check every new identifier against surrounding code.

### What to check

- **Functions/methods**: verb choice (`Get` vs `Fetch` vs `Find` vs `Retrieve`), casing (camelCase vs snake_case vs PascalCase), prefix/suffix patterns (`New*`, `Must*`, `Is*`, `With*`, `*Handler`, `*Service`, `*Repository`)
- **Types/structs/classes**: noun form consistency, suffix patterns (`*Config`, `*Options`, `*Request`, `*Response`, `*Error`)
- **Variables**: abbreviation style (is `ctx` used for context? `req`/`resp` or `r`/`w`?), plural conventions for collections
- **Files**: naming scheme (`snake_case.go` vs `kebab-case.ts`), suffix conventions (`_test.go`, `.spec.ts`, `.helper.`), grouping (one type per file vs grouped)
- **Packages/modules**: singular vs plural, depth conventions, boundary naming
- **Constants/enums**: casing, grouping, documentation style

### How to investigate

1. List files in the same package/directory — note naming patterns
2. Grep for similar functions in the same module (`grep -r "func (Get|Fetch|Find)" pkg/`)
3. Check if the project has a style guide, linter config, or naming conventions in docs

### Severity guide

- **issue:** naming that contradicts an enforced linter rule or documented convention
- **suggestion:** naming that diverges from the dominant pattern in the same package
- **nit:** valid alternative naming in areas without strong convention

---

## Code Reuse & Duplication

The most impactful finding in this dimension: the PR reimplements something that already exists.

### What to check

- **Internal packages**: does the codebase have shared utility packages (`pkg/`, `internal/`, `lib/`, `utils/`, `common/`, `shared/`)? Does one of them already solve the problem?
- **Near-duplicates**: does similar logic exist elsewhere? Look for the same algorithm, validation, transformation, or I/O pattern implemented differently.
- **Wrapper functions**: does the PR wrap a stdlib or third-party function in a way the codebase already does elsewhere?
- **Copy-paste signals**: identical error messages, magic numbers, regex patterns, or SQL fragments appearing in multiple places
- **Shared infrastructure**: retry logic, circuit breakers, HTTP clients, database helpers, auth middleware, validation frameworks — these should almost always be reused, not reimplemented

### How to investigate

1. Identify the core operation the PR implements (e.g., "retry with backoff", "parse config", "validate email")
2. Grep for keywords related to that operation across the codebase
3. Check shared/common directories for existing helpers
4. Look at imports in similar files — what shared packages do they use?
5. Check if the project has a "how to add X" guide or contributing docs

### Severity guide

- **blocking:** reimplements maintained shared infrastructure (auth, retry, circuit breaker, observability, validation framework) — creates divergence that leads to inconsistent behavior and double maintenance
- **issue:** duplicates a helper that exists in a shared package, or implements a pattern that a sibling module already solved and could be extracted
- **suggestion:** could use an existing utility but the duplication is minor (< 10 lines) or the existing utility doesn't perfectly fit
- **nit:** minor duplicate logic that's simpler to keep inline

### Red flags

- New `retry` or `backoff` implementation when `pkg/retry` exists
- New HTTP client wrapper when a configured shared client exists
- New config parsing when the project has a config framework
- New validation logic when a validation package is used elsewhere
- New error types that duplicate existing sentinel errors

---

## Structural Patterns

Every codebase has implicit conventions for how things are organized and connected. PRs that break these patterns create cognitive overhead.

### What to check

- **Error handling**: wrapping style (`fmt.Errorf("...: %w", err)` vs custom error types vs sentinel errors), logging at error site vs propagation, panic recovery conventions
- **Logging**: structured vs printf, logger injection pattern, log level conventions, what context fields are expected
- **Configuration**: env vars vs config files vs flags, how defaults work, how config is validated and injected
- **Initialization**: constructor patterns (`New*`), dependency injection style, lifecycle management
- **Request/response flow**: middleware ordering, context propagation, how request-scoped data flows
- **Database access**: repository pattern vs inline queries, transaction management, connection handling
- **Concurrency**: goroutine/thread spawning patterns, cancellation propagation, synchronization idioms

### How to investigate

1. Read 2-3 files in the same package/module that do similar things
2. Note the pattern: how do they handle errors? How do they log? How do they access config?
3. Compare the PR's approach to the established pattern
4. Check if the divergence is intentional (documented) or accidental

### Severity guide

- **issue:** error handling or logging approach differs from package convention, causing inconsistent behavior in the same module
- **suggestion:** structural divergence that works but will confuse maintainers familiar with the established pattern
- **nit:** minor stylistic difference in areas where the codebase itself isn't consistent

---

## Test Conventions

Test code has conventions too. Inconsistent test styles slow down debugging and review.

### What to check

- **Test structure**: table-driven vs individual cases, subtests, parallel execution
- **Naming**: `Test_functionName_scenario` vs `TestFunctionNameScenario` vs descriptive strings
- **Fixtures**: shared test fixtures, factory functions, builders, test helpers
- **Assertions**: stdlib `if` checks vs testify vs custom assertion helpers
- **Mocking**: mock generation tool, mock placement, interface-based vs function-based
- **Setup/teardown**: `TestMain` vs `t.Cleanup` vs `defer`, test database patterns
- **Test data**: inline vs fixture files vs generated, how test data is organized

### Severity guide

- **suggestion:** test style diverges from the dominant pattern in the same test file or package
- **nit:** valid alternative test organization

---

## Project Structure

File and directory organization conventions are often undocumented but strongly held.

### What to check

- **File placement**: are new files in the expected directory given the project's module organization?
- **Import organization**: does the import grouping (stdlib, external, internal) match existing files?
- **Module boundaries**: does the PR cross module boundaries that other code respects? Does it import from `internal/` packages of other modules?
- **Interface location**: are interfaces defined where consumers are (Go convention) or where implementations are?
- **Export/visibility**: does the PR export things that similar code keeps private, or vice versa?

### Severity guide

- **issue:** file placed in wrong directory or module boundary violated
- **suggestion:** import organization or export decisions diverge from convention

---

## Investigation Techniques

Practical commands and strategies for convention analysis.

### Grep patterns for reuse detection

```bash
# Find existing implementations of the concept
grep -r "func.*Retry" --include="*.go" .
grep -r "class.*Validator" --include="*.py" .
grep -r "function.*parse" --include="*.ts" .

# Find shared utility packages
find . -path "*/pkg/*" -name "*.go" | head -20
find . -path "*/internal/common/*" -o -path "*/lib/*" -o -path "*/utils/*" | head -20

# Find how similar files handle a pattern
grep -r "fmt.Errorf" --include="*.go" pkg/same-package/
grep -r "logger\." --include="*.go" pkg/same-package/

# Find naming conventions for similar constructs
grep -rn "func New" --include="*.go" pkg/same-package/
grep -rn "func (s \*" --include="*.go" pkg/same-package/
```

### Comparison strategy

1. **Same package first**: compare against files in the same directory — strongest signal
2. **Sibling packages**: compare against related modules at the same level
3. **Shared packages**: check what shared utilities exist and whether similar code uses them
4. **Project-wide**: only for naming and structural patterns that should be globally consistent

### What NOT to flag

- Intentional divergence documented in comments or commit messages
- New patterns that are clearly better than existing ones (flag as `thought:` with suggestion to migrate existing code)
- Convention differences between independent modules that don't interact
- Style variations in areas where the codebase itself is inconsistent (no clear convention to follow)
