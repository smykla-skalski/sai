# fix-flaky-e2e

Diagnose and fix flaky e2e tests in the [Kuma](https://kuma.io/) service mesh project.

## Features

- **11-cause taxonomy** — sourced from real Kuma PR history (timing, xDS races, Gomega misuse, pod races, mTLS/SDS, circuit breakers, outlier detection)
- **Minimal fixes** — matches each root cause to a precise code change, never refactors surrounding code
- **Kuma-specific timeouts** — 30s/60s/2m guidelines matched to operation type (pod, gateway, mTLS/cross-zone)
- **Envoy debug reference** — admin API cheat sheet, response flags, xDS diagnostic workflow
- **Anti-pattern detection** — flags `FlakeAttempts`, bare `Expect` in `Eventually`, `time.Sleep`, missing `AfterEachFailure`

## Usage

Auto-triggers on mentions of flaky tests, intermittent CI failures, or `test/e2e/` file paths. Also user-invocable:

```
/fix-flaky-e2e
```

## Reference Material

- `skills/fix-flaky-e2e/references/root-causes.md` — 11 root causes with diagnosis signals and examples
- `skills/fix-flaky-e2e/references/fix-patterns.md` — copy-paste fix templates per root cause
- `skills/fix-flaky-e2e/references/envoy-debug.md` — Envoy admin API, response flags, Kuma inspect commands
- `skills/fix-flaky-e2e/evals/evals.json` — eval test cases
