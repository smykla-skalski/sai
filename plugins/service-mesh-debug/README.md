# service-mesh-debug

Diagnose and fix flaky e2e tests and connectivity issues in service mesh environments (Kuma, Istio, Linkerd, Consul).

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **11-cause taxonomy** — sourced from real Kuma PR history (timing, xDS races, Gomega misuse, pod races, mTLS/SDS, circuit breakers, outlier detection)
- **Minimal fixes** — matches each root cause to a precise code change, never refactors surrounding code
- **Kuma-specific timeouts** — 30s/60s/2m guidelines matched to operation type (pod, gateway, mTLS/cross-zone)
- **Envoy debug reference** — admin API cheat sheet, response flags, xDS diagnostic workflow
- **Anti-pattern detection** — flags `FlakeAttempts`, bare `Expect` in `Eventually`, `time.Sleep`, missing `AfterEachFailure`
- **Multi-mesh support** — Kuma (9901), Istio (15000), Consul (19000), Linkerd
- **Read-only diagnostics** — bundled scripts only read Envoy admin endpoints through `kubectl`; commands that change cluster or proxy state run only when you ask for them

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install service-mesh-debug@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add service-mesh-debug@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/service-mesh-debug/` directly:

```bash
ln -s /path/to/sai/plugins/service-mesh-debug/skills/service-mesh-debug ~/.config/opencode/skills/service-mesh-debug
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/service-mesh-debug/`

## Usage

Auto-triggers on mentions of flaky tests, intermittent CI failures, `test/e2e/` file paths, 503 errors, mTLS failures, or service mesh connectivity issues. Also invocable by name: `/service-mesh-debug` in Claude Code and Copilot CLI, `$service-mesh-debug` in Codex.

The diagnostic scripts need Python 3.9+ and `kubectl` pointed at the cluster you are debugging.

## Reference Material

- `skills/service-mesh-debug/references/root-causes.md` — 11 root causes with diagnosis signals and examples
- `skills/service-mesh-debug/references/fix-patterns.md` — copy-paste fix templates per root cause
- `skills/service-mesh-debug/references/envoy-debug.md` — Envoy admin API, response flags, Kuma inspect commands
- `skills/service-mesh-debug/references/failure-taxonomy.md` — 6-category failure classifier for mesh connectivity
- `skills/service-mesh-debug/references/mesh-debug-workflow.md` — 7-phase debugging workflow across mesh implementations
- `skills/service-mesh-debug/evals/evals.json` — eval test cases

## License

MIT
