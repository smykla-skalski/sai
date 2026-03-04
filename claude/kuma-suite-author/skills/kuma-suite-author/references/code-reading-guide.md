# Code reading guide

Where to find things in a Kuma repo for generating test suites.

## Policy-based features

| What | Path |
|:-----|:-----|
| Policy spec (struct, markers) | `pkg/plugins/policies/<name>/api/v1alpha1/<name>.go` |
| Validation logic | `pkg/plugins/policies/<name>/api/v1alpha1/validator.go` |
| Deprecation warnings | `pkg/plugins/policies/<name>/api/v1alpha1/deprecated.go` (optional) |
| xDS generation | `pkg/plugins/policies/<name>/plugin/v1alpha1/plugin.go` |
| Test golden files | `pkg/plugins/policies/<name>/plugin/v1alpha1/testdata/` |
| K8s types | `pkg/plugins/policies/<name>/k8s/v1alpha1/` |
| CRDs | `deployments/charts/kuma/crds/` |

## Non-policy features

Start from changed files (PR diff or branch diff against master). Common locations:

| Area | Path |
|:-----|:-----|
| Core resource types | `pkg/core/resources/apis/mesh/` |
| Common API types | `api/common/v1alpha1/` |
| Mesh proto definitions | `api/mesh/v1alpha1/` |
| xDS config generation | `pkg/xds/` |
| KDS sync | `pkg/kds/` |
| Control plane runtime | `pkg/plugins/runtime/` |
| Data plane config | `pkg/config/app/kuma-dp/` |
| Transparent proxy | `pkg/transparentproxy/` |
| REST API | `pkg/api-server/` |

## What to read for each group type

| Suite group | Read from code |
|:------------|:---------------|
| G1 CRUD | API spec struct fields, CRD schema |
| G2 Validation | `validator.go` - every `Err()` call is a rejection case |
| G3 Runtime config | `plugin.go` - what xDS resources get generated, what config dump sections to inspect |
| G4 E2E flow | Test golden files - expected xDS output, plus traffic generation patterns |
| G5 Edge cases | Validator edge cases, nil/empty handling in plugin.go |
| G6 Multi-zone | KDS sync markers on the resource type, `pkg/kds/` for sync behavior |
| G7 Backward compat | `deprecated.go`, old field names in API spec, migration notes |

## Tips

- Golden files in `testdata/` show exact expected Envoy configs - use these to derive validation commands.
- The `+kuma:policy` markers on the spec struct tell you about scope (Mesh vs Global), display name, etc.
- `validator.go` returns `admission.Warnings` for deprecations - these become G7 test cases.
- `plugin.go`'s `Apply()` method reveals which xDS resource types are affected (listeners, clusters, routes, endpoints).
