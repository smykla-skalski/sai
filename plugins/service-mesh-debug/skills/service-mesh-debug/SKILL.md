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
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Diagnostic scripts need Python 3.10+ and kubectl with access to the target cluster; they only read Envoy admin endpoints and never change cluster state.
allowed-tools: Bash Grep Read
user-invocable: true
metadata:
  short-description: Debug flaky mesh tests and traffic
---


# Fix Flaky E2E / Service Mesh Debugging Skill

Two modes: **Flaky E2E Fix** (Kuma/Ginkgo test files) and **Mesh Connectivity Debug** (live cluster issues).

## Required guidance

Before taking any action, read [references/workflow.md](references/workflow.md) completely. It is the authoritative procedure and preserves every platform fallback, decision rule, template, command, validation step, and output contract. Follow its sections in order and load the deeper references it names only at their stated gates.

Paths in the workflow are relative to this skill directory. If argument substitution is unavailable or unresolved, take the input and flags from the user's request. When a named tool, agent, or interaction primitive is unavailable, use the workflow's compatibility fallback; never silently skip the behavior.

## Core flow

1. Scope
2. Agent compatibility
3. Mode 1: Flaky E2E Fix
4. Process (Flaky E2E)
5. Mode 2: Mesh Connectivity Debugging
6. Framework helpers quick reference
7. Gomega timeout guidelines
8. Anti-patterns to flag

## Execution contract

- Resolve the target and flags before side effects.
- Execute every applicable workflow section in the listed order; headings are an index, not a replacement for the detailed instructions.
- Preserve explicit read gates: load each supporting reference immediately before the phase that needs it.
- Follow repository instructions and the user's authorized scope.
- Preserve validation, state-update, deduplication, adversarial-check, and output requirements exactly as defined in the workflow.
- Stop at every hard stop named by the workflow and state the required next action.
