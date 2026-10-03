---
name: service-mesh-debug
description: >
  Diagnose and fix flaky e2e tests and general connectivity issues in service mesh environments
  (Kuma, Istio, Linkerd, Consul). Trigger when: a user mentions intermittent test failures,
  "test is flaky", e2e failures in CI that don't reproduce locally, Ginkgo/Gomega test files
  that fail sometimes, 503/connection refused errors, mTLS handshake failures, pods not getting
  traffic, xDS NACKs or warming resources, cert delivery timing issues, or "works locally but
  not in cluster". Covers Kuma flakiness patterns (timing races, xDS propagation delays, Envoy
  circuit breakers, mTLS readiness, Gomega misuse) AND universal mesh debugging (control plane
  connectivity, proxy lifecycle, certificate problems, traffic routing/policy, service discovery).
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Diagnostic scripts need Python 3.9+ and kubectl with access to the target cluster; they only read Envoy admin endpoints and never change cluster state.
allowed-tools: Bash Grep Read
user-invocable: true
metadata:
  short-description: Debug flaky mesh tests and traffic
---

# Fix Flaky E2E / Service Mesh Debugging Skill

Two modes: **Flaky E2E Fix** (Kuma/Ginkgo test files) and **Mesh Connectivity Debug** (live cluster issues).

## Scope

- Designed for Kuma/Envoy e2e test flakiness and service mesh connectivity issues
- Not designed for unit test failures, application-level bugs, or non-mesh networking problems
- Assumes the test framework is Ginkgo/Gomega with the Kuma `test/framework/` helpers (Mode 1) or a live K8s cluster with mesh sidecar injection (Mode 2)

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | Not used: take the test file, pod, namespace or symptom from the user's request and local context, and ask only for what you cannot find |
| Skill directory substitution | Claude Code replaces the placeholder at the start of every script command with this skill's absolute directory. If a script path below does not start with `/`, replace everything before `/scripts/` with the absolute path of the directory holding this SKILL.md, and run the script from the user's working directory (`envoy_snapshot.py` writes its snapshot there). Never search plugin caches for the scripts |
| AskUserQuestion, subagents, `context: fork` | Not used; the skill runs in the main agent loop everywhere |

Cluster safety on every agent: the bundled scripts only read Envoy admin endpoints and `kubectl get` output. Commands from the references that change cluster or proxy state (Envoy `--post-data` log-level changes, sidecar or pod restarts, `kubectl apply`/`delete`, policy edits) are suggestions for the user; run one yourself only after the user explicitly asks for it or confirms it. Before the first script run, check `kubectl config current-context` and name that cluster in your reply.

In Codex, `kubectl` needs network access to the cluster API, so if a script or `kubectl` call fails because of sandbox or network restrictions, rerun the same command with escalation (`sandbox_permissions=require_escalated`) and a short reason. State whether a diagnosis is confirmed by live output or inferred from code and partial evidence.

## Mode 1: Flaky E2E Fix

Kuma e2e tests use Ginkgo/Gomega with a custom framework in `test/framework/`. Flakiness almost
always traces to one of ~11 known root causes. The fix is usually a 1-3 line change.

## Process (Flaky E2E)

### 1. Read the test

Read the file the user provides (or grep for it). Focus on:
- `Eventually` / `Consistently` calls and their timeout strings
- `Expect(...)` calls **inside** `Eventually` blocks
- Pod creation / deletion sequences
- Where traffic assertions happen relative to resource creation
- Any `time.Sleep` calls

### 2. Diagnose: match to the taxonomy

Read [references/root-causes.md](references/root-causes.md) in full before matching — it contains
code examples and fix patterns for all 11 root causes. The most common causes in order of frequency:

| # | Pattern | Fast signal |
|---|---------|------------|
| 1 | Short `Eventually` timeout | `"30s"` near gateway/policy/mTLS code |
| 2 | Missing xDS readiness gate | Traffic asserted immediately after policy apply |
| 3 | Bare `Expect` inside `Eventually` | `Eventually(func() { Expect(...) })` — no `g Gomega` |
| 4 | Pod not available after create | `WaitUntilNumPodsCreatedE` without `WaitUntilPodAvailableE` |
| 5 | `PodNameOfApp` race after kill | Called immediately after `KillAppPod` |
| 6 | External component not awaited | SPIRE / cert-manager / Postgres creation without availability wait |
| 7 | xDS config diff before convergence | `config_dump` compare without `Eventually` wrapper |
| 8 | SDS secret timing | mTLS test fails with `Secret is not supplied by SDS` |
| 9 | Statistical tight margins | Traffic split % assertion with small N |
| 10 | Circuit breaker tripped | Concurrent test runs exhaust CB defaults |
| 11 | Outlier detection ejection | Fault-injection test leaves host ejected for 30s |

### 3. Apply the minimal fix

Read [references/fix-patterns.md](references/fix-patterns.md) before applying any fix — it contains
copy-paste templates matched to each root cause.

Key rules:
- Change **only** what's flaky — keep the diff minimal so reviewers can verify the fix in isolation.
- Use the root-cause-specific fix pattern from fix-patterns.md. Never use `FlakeAttempts(n)` as the primary fix because it hides root causes and lets the underlying race regress silently.
- Replace `time.Sleep` with `Eventually` because sleep-based waits are fragile under variable CI load and slow down the suite unnecessarily.
- After fixing, run: `make format && make check`
- If `make check` reports failures, return to Step 2 with the error output and re-diagnose — the original root cause may have been misidentified.

### 4. Add `AfterEachFailure` if missing

If the test lacks a failure debug hook, suggest adding:
```go
AfterEachFailure(func() {
    DebugKube(KubeCluster, meshName, namespace)
})
```
This dumps CP logs, dataplane state, and pod info on failure — essential for future debugging.

### 5. Envoy diagnosis (if needed)

If the failure involves connectivity, xDS config, or mTLS and you need to guide the user through
live debugging, read [references/envoy-debug.md](references/envoy-debug.md) before starting — it
contains the full admin API reference and 7-step diagnostic workflow.

For live cluster debugging, suggest running the scripts in `scripts/` directly against the pod:

```bash
# Full diagnostic snapshot (saves to ./envoy-snapshot-<pod>-<ts>/)
"${CLAUDE_SKILL_DIR}/scripts/envoy_snapshot.py" <pod> -n <namespace>

# xDS health: CP connected? NACKs? Warming resources? Specific cluster present?
"${CLAUDE_SKILL_DIR}/scripts/xds_check.py" <pod> -n <namespace> --cluster <cluster-name>

# mTLS health: warming secrets? cert expiry? TLS error stats?
"${CLAUDE_SKILL_DIR}/scripts/mtls_check.py" <pod> -n <namespace>
```

Scripts require only `kubectl` in PATH and Python 3.9+. No extra dependencies.
All scripts support `--admin-port` (default 9901) for non-Kuma meshes (Istio: 15000, Consul: 19000).

---

## Mode 2: Mesh Connectivity Debugging

For general connectivity issues in any service mesh (503s, cert errors, traffic blocked, no healthy
hosts, policy denials), follow the 7-phase workflow.

### Quick start

```bash
# 1. Auto-detect mesh and check control plane health
"${CLAUDE_SKILL_DIR}/scripts/mesh_health.py"

# 2. Run Envoy diagnostics on the affected pod (adjust --admin-port for your mesh)
"${CLAUDE_SKILL_DIR}/scripts/xds_check.py" <pod> -n <ns>              # Kuma
"${CLAUDE_SKILL_DIR}/scripts/xds_check.py" <pod> -n <ns> --admin-port 15000 --container istio-proxy  # Istio
"${CLAUDE_SKILL_DIR}/scripts/mtls_check.py" <pod> -n <ns>             # cert/mTLS issues
"${CLAUDE_SKILL_DIR}/scripts/envoy_snapshot.py" <pod> -n <ns>         # full snapshot for offline analysis
```

### Classify the failure first

Read [references/failure-taxonomy.md](references/failure-taxonomy.md) to classify the issue into
one of 6 categories before spending time on mesh-specific commands.

| Symptom | Category |
|---------|---------|
| All pods broken simultaneously | 1 – Control Plane |
| Single pod, no sidecar | 2 – Proxy Lifecycle |
| `Secret is not supplied by SDS` | 3 – Certificates |
| TLS handshake failure | 3 – Certificates |
| 403 / `UAEX` flag | 4 – Policy |
| `UH` / no healthy hosts | 5 – Service Discovery |
| Works on some nodes, not others | 6 – Infrastructure |
| Flaky in CI, passes locally | 1 or 3 |

### Full debugging workflow

Read [references/mesh-debug-workflow.md](references/mesh-debug-workflow.md) for the 7-phase
workflow with mesh-specific commands for Kuma, Istio, Linkerd, and Consul.

## Framework helpers quick reference

| Helper | Location | Use for |
|--------|----------|---------|
| `WaitForMesh` | `test/framework/resources.go` | Multi-zone mesh sync |
| `WaitForResource` | `test/framework/resources.go` | Any resource to appear |
| `DebugKube` / `DebugUniversal` | `test/framework/debug.go` | State dump on failure |
| `AfterEachFailure` | `test/framework/ginkgo.go` | Hook debug to failure only |
| `ControlPlaneAssertions` | `test/framework/debug.go` | Assert CP not crashed |
| `CollectEchoResponse` | `test/framework/client/collect.go` | HTTP connectivity check |
| `CollectFailure` | `test/framework/client/collect.go` | Assert expected conn failure |
| `MustPassRepeatedly(n)` | Gomega | Require N consecutive passes |
| `Within(timeout, task)` | `pkg/test/within.go` | Goroutine with timeout |

## Gomega timeout guidelines

| Context | Timeout | Rationale |
|---------|---------|-----------|
| Pod creation + readiness | `"30s"` | Scheduler + kubelet startup |
| Policy propagation (simple) | `"30s"` | CP reconcile + xDS push |
| Gateway / ingress policies | `"60s"` | Extra reconcile cycles |
| mTLS / SVID / cross-zone | `"2m"` | Cert issuance + KDS sync |
| `MustPassRepeatedly(5)` | `"2m"` | Needs many attempts to confirm stable |

Polling interval: `"1s"` is standard. Use `"500ms"` only for fast local assertions.

## Anti-patterns to flag

- `Expect(x)` inside `Eventually(func() { ... })` — must be `Eventually(func(g Gomega) { g.Expect(x) })`
- `WaitUntilNumPodsCreatedE` alone — always follow with `WaitUntilPodAvailableE` per pod
- Asserting traffic before checking xDS config convergence
- `time.Sleep(N * time.Second)` — replace with `Eventually`
- `FlakeAttempts(3)` as first resort

<example>
Input: Test uses `Eventually(func() { Expect(resp.Instance).To(Equal("server")) }, "30s", "1s")`.
Diagnosis: Root cause #3 — bare Expect panics on first failure, bypassing retry logic.
Fix: `Eventually(func(g Gomega) { g.Expect(resp.Instance).To(Equal("server")) }, "30s", "1s").Should(Succeed())`
</example>

<example>
Input: `Install(policy)` immediately followed by traffic assertion; test passes locally but fails in CI.
Diagnosis: Root cause #2 — xDS propagation delay. CP reconcile + push takes 25s+ under CI load.
Fix: Insert xDS readiness gate (Pattern 2 in fix-patterns.md) between Install and traffic assertion.
</example>

<example>
Input: Test creates pods with `WaitUntilNumPodsCreatedE(t, opts, "app", 2, 30, 1*time.Second)` then immediately sends traffic.
Diagnosis: Root cause #4 — pods exist but containers are not ready. Created != Available.
Fix: Add `WaitUntilPodAvailableE(t, opts, podName, 30, 1*time.Second)` for each pod after the create wait.
</example>
