# Dead Code Detection — Deep Reference

Detect code that the PR introduces or exposes as unreachable, unused, or obsolete. Dead code inflates cognitive load, misleads future contributors, and silently rots (dependencies drift, APIs change, but dead code never fails a test).

## Detection Categories

### 1. Newly Introduced Dead Code

Code added by the PR that is never called or reached.

- **Unused functions/methods**: defined but no caller exists in the codebase (grep for invocations)
- **Unused exports**: exported symbols with zero importers outside the defining module
- **Unused parameters**: function parameters that are never read within the body (distinguish from interface compliance — implementing a required signature is not dead code)
- **Unused variables/assignments**: assigned but never read (often caught by linters, but not always — especially across module boundaries)
- **Unreachable branches**: conditions that can never be true given the surrounding logic (e.g., checking for a type after an exhaustive type switch, redundant nil checks after early return)
- **Unreachable code after control flow**: code after unconditional return, break, continue, panic, os.Exit, sys.exit, throw
- **Dead feature flags**: flags introduced already defaulting to the only path that will ever execute, with no toggle mechanism wired

### 2. Code Made Dead by the PR

Changes that orphan existing code without removing it.

- **Orphaned functions**: the PR changes a call site to use a different function, but the old function remains with zero callers
- **Orphaned imports/includes**: modules imported but no longer referenced after the PR's changes
- **Orphaned types/interfaces**: types defined for a removed or refactored feature that no longer have consumers
- **Orphaned constants/config keys**: constants or config entries that were only used by code the PR replaced
- **Stale error handling**: catch/except blocks for error types that can no longer be thrown by the refactored code
- **Stale feature flags**: the PR removes the conditional but leaves the flag definition, config entry, and documentation

### 3. Commented-Out Code

- **Commented-out blocks**: code commented out rather than deleted (version control exists for history)
- **TODO-gated dead code**: blocks guarded by `// TODO: enable when X` that have no associated tracking issue or timeline
- **Debug/development leftovers**: print statements, console.log, temporary test scaffolding left in production code

### 4. Test-Only Dead Code

- **Tests for removed functionality**: test cases covering code paths that no longer exist after the PR
- **Unused test helpers/fixtures**: test utilities that were only used by removed tests
- **Stale mocks**: mock implementations for interfaces that changed or were removed

## Analysis Approach

### Step 1: Identify Candidates

For each new or modified symbol (function, type, constant, export) in the diff:
1. Grep the codebase for all references to that symbol
2. Exclude self-references (definition site, recursive calls within same function)
3. Exclude test references when analyzing production dead code (but flag test-only symbols separately)
4. Check dynamic dispatch — if the function implements an interface or is assigned to a variable/callback, it may be reachable indirectly

### Step 2: Check for Indirect Reachability

Before flagging, verify the symbol is not reachable through:
- **Interface/trait implementation**: method satisfies a contract even if no static call exists
- **Reflection/metaprogramming**: runtime lookup by name (common in Java, Go, Python)
- **Plugin/hook registration**: registered in init(), setup(), or config and invoked dynamically
- **Serialization tags**: struct fields with JSON/XML/protobuf tags are used by serializers
- **Framework conventions**: handlers registered by naming convention (e.g., Rails controllers, pytest test_ functions)
- **Public API surface**: exported from a library — external consumers may exist outside the repo
- **Generated code callers**: code generated at build time may reference the symbol

### Step 3: Trace Orphaned Code

For each function/type the PR modifies the callers of:
1. Check if old callers still exist
2. If a function lost its last caller, flag it
3. Follow the chain — an orphaned function may itself have been the only caller of other functions (transitive dead code)

## Language-Specific Patterns

### Go
- Unused imports and variables are compile errors (already caught), but unused exported functions, methods on unexported types, and struct fields are not
- Check for methods that only satisfy an interface no longer used
- `init()` functions that configure removed features
- Build-tagged files where the tag is never set

### Python
- `__all__` exports not matching actual usage
- Decorated functions where the decorator registry was removed
- Abstract method implementations where the base class changed
- `if __name__ == "__main__"` blocks in library modules that are never run directly

### TypeScript/JavaScript
- Named exports with zero importers
- React components never rendered (grep for JSX usage)
- Event handlers registered for removed DOM elements
- Barrel file (`index.ts`) re-exports for removed modules

### Java
- Private methods with no caller in the class
- Unused Spring beans / dependency injection bindings
- Exception classes for removed error paths
- Annotation-processor-discovered code that lost its annotation

### Rust
- `pub` functions with no external caller (check `pub(crate)` scope)
- Trait implementations for removed trait bounds
- Feature-gated code where the feature is never enabled
- Compiler dead-code suppression annotations hiding the problem

## Severity Calibration

| Severity | Condition |
|----------|-----------|
| `issue:` | Significant dead code introduced by the PR — entire functions, types, or modules with zero callers. Creates maintenance burden and misleads future contributors. |
| `suggestion:` | Small dead code (unused parameter, single orphaned constant, commented-out block). Low impact but worth cleaning. |
| `nit:` | Arguable cases — code that appears dead but has plausible indirect reachability. Mention for author awareness. |
| `thought:` | Pre-existing dead code adjacent to the PR's changes. Not the PR's fault but worth noting for future cleanup. |

## False Positive Guardrails

Do NOT flag as dead code:
- Public API surface of libraries (consumers may be external)
- Interface/trait implementations (contractual obligation)
- Serialization-tagged struct fields
- Framework-discovered code (test functions, HTTP handlers, CLI commands)
- Feature-flagged code with an active flag mechanism
- Code behind build tags/conditional compilation that is used in other build configurations
- Intentionally unused parameters required by a callback/handler signature (e.g., `_` prefixed)

When uncertain, use `question:` severity and ask the author for context rather than flagging a false positive.
