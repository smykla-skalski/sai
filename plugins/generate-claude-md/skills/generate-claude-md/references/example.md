# Worked Example

A complete, ideal CLAUDE.md for a Go payments API (~35 lines), then notes on why
each choice was made. Use it as a shape reference, not a template to copy
verbatim — every line is specific to its project.

## The file

```markdown
# Acme Payments API

## Commands
- Build: `make build`
- Run (local): `make run` (needs `docker compose up -d db redis` first)
- Test (full): `go test ./...`
- Test (focused): `go test ./internal/ledger -run TestApply`
- Lint: `golangci-lint run` (also the pre-commit gate, via `.pre-commit-config.yaml`)

## Architecture
- `internal/http/` handlers validate + decode, then call `internal/svc/`;
  services never import `internal/http/` (enforced by `make lint`)
- `internal/svc/` orchestrates domain logic; `internal/ledger/` is the only
  package that writes money rows, always inside a DB transaction
- All Stripe webhooks enter through one handler: `internal/http/webhook.go:41`
- Request flow: handler → service → ledger → `internal/store/` → response

## Domain
- "Intent" = a not-yet-captured charge (`internal/ledger/intent.go`); "Entry" =
  an immutable ledger row. Never mutate an Entry — append a reversing Entry.

## Testing
- Single test: `go test ./internal/ledger -run TestApply`
- Mock external calls at the `Gateway` interface (`internal/svc/gateway.go:12`);
  do not hit Stripe in unit tests
- Ledger tests need Postgres: `docker compose up -d db`, then `make migrate`

## Gotchas
- The ledger is append-only — a "correction" is a new reversing Entry, never an
  UPDATE (`internal/ledger/apply.go:88`)
- Webhook handlers must be idempotent on `idempotency_key`; Stripe retries
  (`internal/http/webhook.go:41`)
- `make migrate` must run before ledger tests or they fail on a missing table

## Commits
- Conventional commits, scope required: `fix(ledger): guard against double apply`
- Branch from `main`; PRs need green CI + one approval
```

## Why each choice

- **No tech-stack section, no directory tree.** The language is obvious from the
  files and the README already lists dependencies. A tree would add lines and zero
  signal.
- **Commands first, with a focused-test command and the gate named.** This is the
  section Claude uses every session.
- **Architecture states boundaries and the one webhook entry point** with
  `file:line`, instead of listing packages. The "services never import handlers"
  rule is the kind of thing Claude would otherwise violate.
- **Domain maps two terms to code** — the append-only ledger model is the project's
  core invariant and not inferable from a quick read.
- **Gotchas all have locations and failure modes.** Each one prevents a concrete
  mistake; none is generic advice.
- **~35 lines.** Well under the 150 limit; every line passes "would removing this
  cause a mistake?".

## Counter-example (what NOT to generate)

```markdown
# Acme Payments API

Acme Payments API is a Go service for processing payments. It is built with Go
1.22 and uses PostgreSQL, Redis, and the Stripe API.        ← README duplication

## Project Structure                                         ← directory tree
internal/
  http/
  svc/
  ledger/
  store/

## Code Style
Write clean, idiomatic Go. Handle all errors. Use gofmt.     ← generic + defaults

## Testing
Write tests for new code and make sure they pass.            ← self-evident filler
```

Every line here fails the rubric: README dup, a tree, generic advice, and
self-evident filler. This is roughly what naive auto-generation (`/init`) tends to
produce, and what this skill exists to avoid.
