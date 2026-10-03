# Grep-able Pattern Heuristics

Language-agnostic patterns for detecting technical debt via Grep. Apply patterns relevant to the detected stack.

## Code Quality

- Bare exception handlers: `except:`, `catch {}`, `catch(Exception`, `catch (...)`
- Swallowed errors: empty catch blocks (catch + next line is `}`)
- God objects: files >1000 lines with many public methods/exports
- Commented-out code: `//` followed by valid syntax patterns across 3+ consecutive lines
- Deep nesting: 4+ levels of indentation in control flow

## Architecture

- Mixed async: `Promise` + `callback` in same module, `.then()` + `async/await` mixed
- Circular imports: mutual import chains (A->B->A)
- Feature envy: functions accessing another module's internals more than their own
- Barrel file bloat: re-export files >50 entries

## Dependencies

- Version pin extremes: `"*"`, `"latest"`, or exact pins without range (`"1.2.3"` vs `"^1.2.3"`)
- Duplicate dependency: same lib in multiple package managers or lock files
- Vendored copies: lib source copied into `vendor/` or `lib/` that's also in deps

## Testing

- Tests without assertions: `test(` or `it(` blocks without `assert`/`expect`/`should`
- Sleep-based tests: `time.Sleep`, `setTimeout`, `sleep(` in test files
- Overly mocked: test files where mock count > assertion count

## DevOps

- Missing lint step: CI config without `lint`, `check`, or `fmt` step
- No lockfile: `package.json` without `package-lock.json`/`yarn.lock`/`pnpm-lock.yaml`
- Hardcoded CI versions: pinned action versions without Dependabot/Renovate for updates

## Documentation

- Stub `@param`: `@param \w+ - \w+ parameter` or `@param \w+ - the \w+`
- Stub `@returns`: `@returns the result`, `@returns {void}`
- Missing doc on exports: `export (function|class|const)` without preceding `/**`
- Stale README commands: `npm start` / `go run` in README that don't match `package.json` scripts or `Makefile`

## Security

- Hardcoded secrets: `password\s*=\s*"`, `api_key\s*=\s*"`, `token\s*=\s*"`, `secret\s*=\s*"`
- SQL injection: string concatenation in queries (`"SELECT.*" \+`, f-strings with SQL)
- Insecure random: `Math.random()` in security context, `rand.Intn` without crypto/rand
- Disabled TLS verification: `InsecureSkipVerify`, `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED`
