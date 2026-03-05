# Suite template - generic manual tests

Use this template to define a feature-specific manual suite.

## Suite metadata

- suite id:
- feature scope:
- target environments: single-zone / multi-zone / universal
- required dependencies:
- required baseline manifests:

## Group structure

| Group | Goal                              | Setup | Validation | Required artifacts |
| ----- | --------------------------------- | ----- | ---------- | ------------------ |
| G1    | CRUD baseline                     |       |            |                    |
| G2    | Validation failures               |       |            |                    |
| G3    | Runtime config verification       |       |            |                    |
| G4    | End-to-end flow                   |       |            |                    |
| G5    | Edge cases and negative paths     |       |            |                    |
| G6    | Multi-zone and isolation behavior |       |            |                    |
| G7    | Backward compatibility            |       |            |                    |

## Execution contract for this suite

- all manifests must be applied through `bash "$SKILL_DIR/scripts/apply-tracked-manifest.sh"`
- all failures must trigger immediate triage before next group
- all pass/fail decisions must include artifact pointers
- include edge cases from `references/mesh-policies.md` when suite uses Mesh\* policies

## Group details

### G1 - CRUD baseline

- manifests:
- commands:
- expected result:
- artifacts to capture:

### G2 - Validation failures

- invalid manifest cases:
- expected admission errors:
- artifacts to capture:

### G3 - Runtime config verification

- runtime entities to inspect (xDS, logs, status, endpoints):
- commands:
- expected result:
- artifacts to capture:

### G4 - End-to-end flow

- traffic generation steps:
- expected telemetry or behavior:
- artifacts to capture:

### G5 - Edge cases and negative paths

- dangling refs / missing dependencies / bad combinations:
- expected degraded behavior:
- artifacts to capture:

### G6 - Multi-zone and isolation behavior

- global to zone sync checks:
- cross-mesh isolation checks:
- artifacts to capture:

### G7 - Backward compatibility

- legacy path or deprecated path checks:
- expected behavior parity:
- artifacts to capture:

## Failure triage

See `references/agent-contract.md` (failure policy and bug triage protocol) for the full procedure.
