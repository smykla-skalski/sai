# Manifest validation

Pre-apply checks for every resource or policy manifest.

For `Mesh*` policy specifics (roles, `targetRef` rules, inspect flow), read
`references/mesh-policies.md`.

## Pre-apply checklist

- Confirm all `kind` values exist in the live API (`kubectl explain`)
- Confirm namespace and labels match test intent
- Confirm required fields and enum values are valid for the cluster's CRDs
- If the manifest references other resources, confirm those names exist in the same mesh and expected namespace
- Run server-side dry-run and block on any failure

## Validate

```bash
bash "$SKILL_DIR/scripts/validate-manifest.sh" \
  --kubeconfig "${KUBECONFIG}" \
  --manifest "<manifest-file>"
```

Validation is not optional.

## Safe apply flow

1. Author or copy manifest into the run directory.
2. Validate with `bash "$SKILL_DIR/scripts/validate-manifest.sh"`.
3. Apply with `bash "$SKILL_DIR/scripts/apply-tracked-manifest.sh"`.
4. Verify runtime state from suite expectations.
5. Record artifacts in report.

## Tracked apply example

```bash
bash "$SKILL_DIR/scripts/apply-tracked-manifest.sh" \
  --run-dir "${RUN_DIR}" \
  --kubeconfig "${KUBECONFIG}" \
  --manifest "<manifest-file>" \
  --step "<step-name>"
```

This creates a versioned manifest copy, logs validation and apply output, and updates manifest and command indexes.
