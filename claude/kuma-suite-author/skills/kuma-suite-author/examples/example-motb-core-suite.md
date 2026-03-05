# Example suite - MOTB core manual tests

Reference example for MOTB testing. Copy `suite-template.md` for new features.

## How to execute

- run in order
- capture artifacts per test group
- stop on first unexpected failure and triage
- do not skip groups unless explicitly scoped in run metadata

## Artifacts required for every test group

- tracked manifest copies in `runs/<run-id>/manifests/`
- command outputs in `runs/<run-id>/artifacts/`
- command log entries in `runs/<run-id>/commands/command-log.md`
- result notes in `runs/<run-id>/reports/manual-test-report.md`

## Test groups

| Group   | Goal                                                   | Minimum artifacts                                           |
| ------- | ------------------------------------------------------ | ----------------------------------------------------------- |
| G1      | Resource CRUD                                          | create/get/update/delete outputs + resource YAML            |
| G2      | Validation rejects invalid specs                       | admission errors for invalid inputs                         |
| G3      | `backendRef` policy acceptance and mutual exclusion    | accepted and rejected applies                               |
| G4      | xDS correctness for MeshMetric/MeshTrace/MeshAccessLog | config dump snippets for clusters/listeners                 |
| G5      | Signal flow (metrics/traces/logs)                      | collector logs with all signal types                        |
| G6      | HTTP protocol behavior                                 | no forced HTTP/2 for HTTP trace backend, URI path artifacts |
| G7      | Dangling reference behavior                            | no crash, info log, skipped backend artifacts               |
| G8      | Backward compatibility (inline endpoint)               | deprecation warning and expected runtime config             |
| G9      | KDS sync in multi-zone                                 | global to zone presence/update/delete artifacts             |
| G10     | Mixed backend usage                                    | OTel and Prometheus/mixed backend artifacts                 |
| G11     | Path suffix semantics                                  | URI with and without base path artifacts                    |
| G12     | Unified naming mode                                    | listener/cluster naming and signal flow artifacts           |
| G13     | Gap analysis and edge semantics                        | expected limitations and mismatch confirmations             |
| G14     | Endpoint optionality and schema parity                 | backendRef-only policy acceptance artifacts                 |
| G15     | Mesh isolation                                         | cross-mesh dangling behavior artifacts                      |
| G16     | nodeEndpoint behavior                                  | HOST_IP + STATIC cluster + all signal flow artifacts        |
| G17-G26 | Pipe mode pre-unified                                  | per-signal sockets, dynconf, E2E artifacts                  |
| G27-G39 | Universal multi-zone                                   | k8s and universal zone parity artifacts                     |
| G40-G53 | Unified pipe mode                                      | shared socket, `/otel` route, opt-out behavior              |

## Failure triage

See `references/agent-contract.md` (failure policy and bug triage protocol) for the full procedure.

## Baseline references

- `tmp/madr-095-implementation/11-manual-testing.md`
- `tmp/madr-095-implementation/13-manual-test-report.md`
- `tmp/madr-095-implementation/manual-test-report.md`
- `tmp/madr-095-implementation/16-motb-e2e-verification-guide.md`
- `tmp/madr-095-implementation/k3d-test/`
