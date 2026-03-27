# go-code-review

Auto-review Go code for 100+ common mistakes from [100go.co](https://100go.co/).

## Features

- **100+ mistake patterns** — error handling, concurrency, interfaces, performance, testing, stdlib
- **Severity tiers** — Critical (fix before merge), Major (should fix), Minor (consider)
- **Mistake references** — every finding links to the numbered mistake in the knowledge base
- **False-positive guard** — re-reads flagged locations to confirm accuracy before reporting
- **Real-world patterns** — OSS project examples alongside the canonical reference

## Usage

Auto-triggers when reviewing `.go` files or Go PRs. Also user-invocable:

```
/go-code-review
/go-review
```

## Reference Material

- `skills/go-code-review/knowledge-base.md` — full 100 Go mistakes reference
- `skills/go-code-review/real-world-patterns.md` — OSS project patterns
- `skills/go-code-review/evals/test-cases.md` — eval test cases
