# Contents

1. [Suite file format](#suite-file-format)
2. [Standard group structure](#standard-group-structure)
3. [Manifest conventions](#manifest-conventions)
4. [Validation step patterns](#validation-step-patterns)
5. [Artifact capture patterns](#artifact-capture-patterns)
6. [Execution contract](#execution-contract)
7. [Reference](#reference)

---

# Suite structure

Format spec for test suites consumed by `kuma-manual-test`.

## Suite file format

Every suite is a Markdown file with these sections:

### Metadata block

```markdown
## Suite metadata

- suite id: <kebab-case-name>
- feature scope: <what this tests>
- target environments: single-zone / multi-zone / universal
- required dependencies: <workloads, collectors, etc.>
- required baseline manifests: <mesh config, namespace setup, etc.>
```

### Group table

Summary table listing all test groups with columns:

```markdown
| Group | Goal | Minimum artifacts |
|---|---|---|
| G1 | ... | ... |
```

### Group details

Each group has a section with:

- manifests (inline YAML blocks)
- commands to run
- expected result
- artifacts to capture

## Standard group structure

| Group | Purpose | Typical contents |
|:------|:--------|:-----------------|
| G1 | CRUD baseline | create/get/update/delete the resource |
| G2 | Validation failures | invalid manifests that should be rejected (from validator.go) |
| G3 | Runtime config | xDS inspection commands (from plugin.go understanding) |
| G4 | End-to-end flow | traffic generation + expected behavior |
| G5 | Edge cases | dangling refs, missing deps, bad combinations |
| G6 | Multi-zone | KDS sync, cross-zone, cross-mesh isolation |
| G7 | Backward compat | legacy paths, deprecated fields, migration behavior |

Not all groups apply to every feature. Skip groups that don't make sense, but document why in the suite metadata.

## Manifest conventions

- `apiVersion`: use the correct group/version from the CRD (e.g., `kuma.io/v1alpha1`)
- `metadata.namespace`: `kuma-system` for mesh-scoped resources, workload namespace for namespace-scoped
- `metadata.labels`: include `kuma.io/mesh: <mesh-name>` where required
- `metadata.annotations`: include `kuma.io/mesh: <mesh-name>` for universal resources
- Use realistic but minimal manifests - enough to trigger the behavior, no extras

## Validation step patterns

Commands to verify expected state after applying manifests:

```bash
# Resource exists
kubectl get <resource-type> <name> -n <namespace> -o yaml

# kumactl inspection
"${KUMACTL}" inspect dataplanes --mesh default

# Envoy config dump (specific section)
kubectl exec deploy/<name> -c kuma-sidecar -- \
  wget -qO- localhost:9901/config_dump | \
  jq '.configs[] | select(."@type" | contains("<Section>"))'

# Control plane logs
kubectl logs -n kuma-system deploy/kuma-control-plane --tail=50
```

## Artifact capture patterns

| Group type | What to capture |
|:-----------|:----------------|
| CRUD | resource YAML before/after, kubectl output |
| Validation | admission error messages |
| Runtime config | config dump snippets for relevant xDS sections |
| E2E flow | traffic tool output, collector/backend logs |
| Edge cases | CP logs, resource status, error messages |
| Multi-zone | resource presence on global and zone CPs |
| Backward compat | deprecation warnings, runtime config comparison |

## Execution contract

Every suite must include this checklist:

- all manifests applied through `bash "$SKILL_DIR/scripts/apply-tracked-manifest.sh"`
- all failures trigger immediate triage before next group
- all pass/fail decisions include artifact pointers
- edge cases from `references/mesh-policies.md` included when suite tests Mesh* policies

## Reference

- Suite template: `kuma-manual-test` skill's `examples/suite-template.md`
- Example suite: `kuma-manual-test` skill's `examples/example-motb-core-suite.md`
- Edge case matrix: `kuma-manual-test` skill's `references/mesh-policies.md`
