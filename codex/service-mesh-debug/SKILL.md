---
name: service-mesh-debug
description: Diagnose flaky service-mesh tests and connectivity failures across Kuma, Istio, Linkerd, and Consul. Use when the user is debugging mesh flakiness, xDS issues, or mTLS failures.
metadata:
  short-description: Debug flaky mesh tests and traffic
---

# Service Mesh Debug

Use this skill when the user is debugging flaky e2e tests, xDS propagation issues, mTLS failures, or service-mesh traffic problems.

This is a Codex-oriented port of the Claude skill at `claude/service-mesh-debug/skills/service-mesh-debug`. Keep the domain workflow and bundled resources, but ignore Claude-only frontmatter and runtime wiring.

## Use This Skill

- Use this skill when the user is debugging flaky e2e tests, xDS propagation issues, mTLS failures, or service-mesh traffic problems.

## Do Not Use This Skill

- Do not use this skill for unit tests, pure application bugs, or networking problems unrelated to service-mesh behaviour.

## Workflow

1. Decide whether the problem is primarily a flaky test issue, a live-cluster connectivity issue, or both.
2. Read `references/root-causes.md`, `references/fix-patterns.md`, `references/failure-taxonomy.md`, and `references/mesh-debug-workflow.md` before diagnosing. Read `references/envoy-debug.md` when working with Envoy admin output.
3. Use the bundled scripts when they match the environment: `scripts/mesh_health.py`, `scripts/xds_check.py`, `scripts/mtls_check.py`, and `scripts/envoy_snapshot.py`.
4. Prefer the smallest fix that matches the diagnosed root cause. Do not broaden a targeted flake fix into a refactor unless the evidence demands it.
5. Summarize symptoms, probable root cause, confirming signals, and the specific fix or next data to collect.

## Bundled Resources

- `agents/openai.yaml`
- `evals/`
- `references/`
- `scripts/`

Load only the files needed for the current task. Prefer bundled scripts over ad hoc reimplementation when they already encode the workflow safely.

## Codex Notes

- Infer inputs from the user request, current repository state, and nearby files before asking follow-up questions.
- If a networked or sandboxed command is important and fails because of restrictions, rerun it with escalation and a short justification.
- For destructive or irreversible actions, confirm intent unless the user was already explicit.
- Keep outputs concise and evidence-based. Cite files, commands, or sources that materially support the conclusion.

## Porting Notes

- Be explicit about whether the diagnosis is confirmed versus inferred from partial evidence.
- When working on current cluster state, use up-to-date command output rather than memory.

## Verification

After any fix or state-changing action, rerun the narrowest relevant validator, script, listing command, or source check and compare the before/after result.

1. Re-check the key output, diff, command result, or rendered text after you act.
2. If the task changed files or external state, rerun the narrowest relevant validator, script, listing command, or source query.
3. Report what was verified, what remains unverified, and any residual risk.

## Examples

<example>
User: "This Kuma e2e test flakes in CI with 503s."
Assistant: Matches the symptoms to the taxonomy, checks the copied fix patterns, and proposes the smallest credible fix.
</example>

<example>
User: "We have intermittent mTLS failures between services in the cluster."
Assistant: Uses the workflow and helper scripts to narrow the cause and identify the next commands or changes.
</example>
