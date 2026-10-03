# Section Authoring Guide

For each section: what to put in, what to leave out, and a good/bad example pair.
Build sections in this order. Include a section only when it has real,
project-specific content — never emit an empty or filler section.

## Contents

- [Header / identity](#header--identity)
- [Commands](#commands)
- [Architecture](#architecture)
- [Code style](#code-style)
- [Testing](#testing)
- [Repo etiquette](#repo-etiquette)
- [Gotchas](#gotchas)
- [Security / boundaries](#security--boundaries)

---

## Header / identity

One line, only if the project's purpose is not obvious from its name. No tagline,
no marketing, no tech-stack list (that duplicates the README and the package file).

Often the best header is just `# <name>` with no description, then straight to
Commands.

---

## Commands

The single highest-value section. List the exact, copy-pasteable invocations
Claude needs every session. Always include a focused/single-test command and the
pre-commit gate.

### Good

```markdown
## Commands
- Build: `make build`
- Test (full): `go test ./...`
- Test (focused): `go test ./pkg/auth -run TestLogin`
- Lint: `golangci-lint run`
- Pre-commit gate: `make lint && go test ./...`
```

### Bad

```markdown
## Commands
- Build the project
- Run the tests
- Make sure linting passes
```

No actual commands, no focused-test option, no gate. Claude cannot run these.

---

## Architecture

Explain how components relate and what boundaries are enforced. One line per
relationship. Point at the one or two entry points that matter with `file:line`.
**Never a directory tree.**

### Good

```markdown
## Architecture
- `internal/http/` handlers call `internal/svc/` services; services never import
  handlers (enforced by `make lint`)
- All Stripe webhooks enter through one handler: `internal/svc/billing.go:34`
- Request flow: handler → service → `internal/store/` query → response
```

### Bad

```markdown
## Architecture
internal/
  http/
  svc/
  store/
  util/
```

A file tree with no relationships, no boundaries, no entry points. Claude learns
nothing it could not get from `ls`.

---

## Code style

Only conventions that **differ** from the language default. Point at the config
file; do not restate its rules. If the project's style is just "the formatter's
defaults", omit this section entirely.

### Good

```markdown
## Style
- DB columns are `snake_case` (differs from the JS `camelCase` elsewhere)
- Every error response includes an `error_code` — registry in `src/errors.ts:8`
- Import order is enforced by ESLint (`.eslintrc.js`); do not hand-order
```

### Bad

```markdown
## Style
We use TypeScript. Add type annotations to all parameters and return values.
Prefer `const` over `let`. Use 2-space indentation. Name variables descriptively.
```

Restates language defaults and linter-enforced rules Claude already follows.

---

## Testing

Framework, how to run a single test, what to mock, and any fixture/teardown
requirement that bites if missed.

### Good

```markdown
## Testing
- Framework: pytest; run one test with `pytest tests/test_auth.py::test_login`
- Mock the network at the `httpx` transport layer — see `tests/conftest.py:20`
- Integration tests need a live Postgres: `docker compose up -d db` first
```

### Bad

```markdown
## Testing
Write tests for your code. Make sure all tests pass before committing. Aim for
high coverage.
```

Generic advice with no framework, no run command, no project specifics.

---

## Repo etiquette

Only conventions the project actually enforces. Commit format, branch naming, PR
rules. Skip if the project has no special convention.

### Good

```markdown
## Commits
- Conventional commits, scope required: `feat(api): add login endpoint`
- Branch from `main`; PRs need one approval and green CI
```

---

## Gotchas

Project-specific traps that cost time when unknown. Each must point at a `file:line`
and describe the failure mode. This is where tribal knowledge becomes durable.

### Good

```markdown
## Gotchas
- Tests touching the `orders` table must call `resetOrderSequence()` in teardown
  or later tests hit duplicate-key errors (`test/helpers.ts:12`)
- The payment service is eventually consistent — check `transaction.status`
  before assuming completion (`services/payment.ts:45`)
- `DATABASE_URL` must be set even for unit tests; the client constructs at import
  time (`src/db/client.ts:3`)
```

### Bad

```markdown
## Gotchas
- Handle errors gracefully
- Don't forget to update documentation
- Be careful with the database
```

Generic, no locations, no failure modes. Applies to any project; helps with none.

---

## Security / boundaries

Only if real for this repo: generated files never to edit, paths off-limits,
secret-handling rules.

### Good

```markdown
## Boundaries
- `src/generated/` is codegen output — edit the `.proto` files, never the `.ts`
- Never commit `.env`; secrets load from Vault at boot (`src/config/secrets.ts:10`)
```
