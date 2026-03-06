# Contents

1. [Resuming a partial run](#resuming-a-partial-run)
2. [Phase 0 - environment check](#phase-0---environment-check)
3. [Phase 1 - initialize run](#phase-1---initialize-run)
4. [Phase 2 - bootstrap cluster](#phase-2---bootstrap-cluster)
5. [Phase 3 - preflight](#phase-3---preflight)
6. [Phase 4 - execute tests](#phase-4---execute-tests)
7. [Phase 5 - failure handling](#phase-5---failure-handling)
8. [Phase 6 - closeout](#phase-6---closeout)

---

# Workflow

Supplementary detail for the seven-phase execution flow in SKILL.md. Code blocks live in SKILL.md - this file adds gates, edge cases, and the directory suite loading pattern.

## Resuming a partial run

If a previous run was interrupted, check `runs/<run-id>/run-status.yaml` for `last_completed_group` and `next_planned_group`. Skip to the next planned group and continue from there. Do not re-run already-passed groups unless investigating a failure.

## Phase 0 - environment check

Resolve persistent storage, repo root, Docker, and kumactl as described in SKILL.md Phase 0.

**Gate**: kumactl version output matches the repo HEAD.

## Phase 1 - initialize run

Suite resolution uses the three-step order from SKILL.md Phase 1 (directory suite, legacy `.md` file, literal path). Set `SUITE_DIR` and `SUITE_FILE` accordingly.

Fill `run-metadata.yaml` before touching the cluster.

**Gate**: `run-metadata.yaml` exists and has profile, feature scope, and environment filled in.

## Phase 2 - bootstrap cluster

Read `references/cluster-setup.md` before starting this phase.

Use the cluster-lifecycle.sh invocations from SKILL.md Phase 2. If changes modify CRDs, refresh them after deploy using the kubectl apply command from Phase 2.

**Gate**: `kubectl get pods -n kuma-system` shows all pods Running/Ready.

## Phase 3 - preflight

Use the preflight.sh and capture-state.sh invocations from SKILL.md Phase 3.

**Gate**: preflight script exits 0 and state snapshot is saved.

## Phase 4 - execute tests

Read `references/validation.md` before applying manifests.
Read `references/mesh-policies.md` for Mesh\* policy targeting and debug flow.

Select a suite that matches the feature area, or copy `examples/suite-template.md` if none exists.

For directory suites (`SUITE_DIR` is set):

1. Read `${SUITE_DIR}/suite.md` for overview, group table, and execution contract.
2. Before G1, apply each baseline manifest listed in the baseline table from `${SUITE_DIR}/baseline/`.
3. Before each group, read the group file from `${SUITE_DIR}/groups/` using the path from the group table.
4. After completing a group, the group file content can be dropped from context.

For legacy single-file suites: read the entire suite file as before.

For each test step:

1. Create or copy manifest to a working file.
2. Apply through the tracked script only (see SKILL.md Phase 4 for the invocation).
3. Collect runtime artifacts (log ad-hoc commands with `"$SKILL_DIR/scripts/record-command.sh"`).
4. Write result into the report.

After each test group, update `run-status.yaml` with `last_completed_group`, `next_planned_group`, and pass/fail counts.

On first unexpected failure, go to Phase 5.

**Gate**: all planned tests have pass/fail entries in the report.

## Phase 5 - failure handling

Read `references/troubleshooting.md` for known failure modes.

1. Stop progression.
2. Capture immediate state snapshot (see SKILL.md Phase 5 for the capture-state.sh invocation).
3. Document expected vs observed.
4. Classify the issue (manifest, environment, product bug).
5. Continue only when classification is explicit.

## Phase 6 - closeout

Use the capture-state.sh and report-compactness-check.sh invocations from SKILL.md Phase 6.

**Gate**: all of these are true before marking the run complete:

- Command log is complete
- Manifest index includes every apply
- Report has pass or fail for all planned tests
- Failures include triage details and artifact paths
- Report compactness check passes

Cluster teardown is optional. Leave clusters running if another run follows immediately.

### Performance toggle example

```bash
HARNESS_BUILD_IMAGES=0 HARNESS_LOAD_IMAGES=0 \
  "$SKILL_DIR/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1
```

See SKILL.md "Performance toggles" table for all profiles.
