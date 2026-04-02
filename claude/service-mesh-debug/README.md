# service-mesh-debug

Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul).

## Features

- **11-cause taxonomy** — sourced from real Kuma PR history (timing, xDS races, Gomega misuse, pod races, mTLS/SDS, circuit breakers, outlier detection)
- **Minimal fixes** — matches each root cause to a precise code change, never refactors surrounding code
- **Kuma-specific timeouts** — 30s/60s/2m guidelines matched to operation type (pod, gateway, mTLS/cross-zone)
- **Envoy debug reference** — admin API cheat sheet, response flags, xDS diagnostic workflow
- **Anti-pattern detection** — flags `FlakeAttempts`, bare `Expect` in `Eventually`, `time.Sleep`, missing `AfterEachFailure`
- **Multi-mesh support** — Kuma (9901), Istio (15000), Consul (19000), Linkerd

## Usage

Auto-triggers on mentions of flaky tests, intermittent CI failures, `test/e2e/` file paths, 503 errors, mTLS failures, or service mesh connectivity issues. Also user-invocable:

```
/service-mesh-debug
```

## Reference Material

- `skills/service-mesh-debug/references/root-causes.md` — 11 root causes with diagnosis signals and examples
- `skills/service-mesh-debug/references/fix-patterns.md` — copy-paste fix templates per root cause
- `skills/service-mesh-debug/references/envoy-debug.md` — Envoy admin API, response flags, Kuma inspect commands
- `skills/service-mesh-debug/references/failure-taxonomy.md` — 6-category failure classifier for mesh connectivity
- `skills/service-mesh-debug/references/mesh-debug-workflow.md` — 7-phase debugging workflow across mesh implementations
- `skills/service-mesh-debug/evals/evals.json` — eval test cases
