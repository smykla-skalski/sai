---
name: kuma-suite-author
description: >-
  Generate test suites for kuma-manual-test by reading Kuma source code.
  Produces ready-to-run suites with manifests, validation steps, and expected outcomes.
argument-hint: "<feature-name> [--repo /path/to/kuma] [--mode generate|wizard] [--from-pr PR_URL] [--from-branch BRANCH]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, AskUserQuestion, Agent
user-invocable: true
---

# Kuma suite author

Generate test suites for `kuma-manual-test` by reading Kuma source code. Produces ready-to-run suites with inline manifests, validation steps, and expected outcomes.

## Arguments

Parse from `$ARGUMENTS`:

| Argument | Default | Purpose |
|:---------|:--------|:--------|
| (positional) | - | Feature or policy name (e.g., `meshretry`, `meshtrace`, `meshexternalservice`) |
| `--repo` | auto-detect cwd | Path to Kuma repo checkout |
| `--mode` | `generate` | `generate` (full AI) or `wizard` (interactive step-by-step) |
| `--from-pr` | - | GitHub PR URL to scope the feature from |
| `--from-branch` | - | Git branch to diff against master for scope |
| `--suite-name` | derived from feature | Override output filename |

## Workflow - generate mode (default)

### Step 1: Resolve paths

```bash
DATA_DIR="$(echo "${XDG_DATA_HOME:-$HOME/.local/share}/sai/kuma-manual-test")"
mkdir -p "${DATA_DIR}/suites" "${DATA_DIR}/runs"
```

Resolve `REPO_ROOT`: `--repo` flag > check if cwd has `go.mod` with `kumahq/kuma` > fail with message.

### Step 2: Scope the feature

Identify what code to read based on the input:

- **From feature name**: find policy dir in `pkg/plugins/policies/`, API spec, plugin.go, tests.
- **From PR URL**: run `gh pr diff <number> --repo kumahq/kuma` to identify changed files.
- **From branch**: run `git diff master...<branch> --name-only` to identify changed files.

### Step 3: Read code

Read `references/code-reading-guide.md` for where to look in the Kuma repo.

For each identified file, read and extract:

- **Policy API spec** (`api/v1alpha1/<policy>.go`): struct fields, markers, validation constraints.
- **Plugin implementation** (`plugin/v1alpha1/plugin.go`): xDS generation logic, which resource types are affected.
- **Existing tests** (`plugin/v1alpha1/testdata/`): golden files show expected Envoy configs.
- **Validator** (`api/v1alpha1/validator.go`): what inputs are rejected and why.
- **Non-policy features**: read relevant `pkg/` code based on changed files list.

### Step 4: Generate suite

Read `references/suite-structure.md` for the format spec.

Build the suite with these groups (skip groups that don't apply, document why):

| Group | Source | Contents |
|:------|:-------|:---------|
| G1 CRUD | API spec struct | create/read/update/delete manifests with realistic field values |
| G2 Validation | validator.go | invalid manifests that trigger each rejection path |
| G3 Runtime config | plugin.go | xDS inspection commands based on what Apply() generates |
| G4 E2E flow | golden files + plugin logic | traffic generation + expected behavior |
| G5 Edge cases | validator edge cases, nil handling | dangling refs, missing deps, boundary values |
| G6 Multi-zone | KDS markers, sync config | global-to-zone presence checks |
| G7 Backward compat | deprecated.go, old fields | legacy path behavior, deprecation warnings |

For each group:
- Generate actual YAML manifests inline.
- Include specific validation commands (kubectl, kumactl, config_dump).
- State expected outcomes clearly.
- List artifacts to capture.

### Step 5: Save suite

```bash
SUITE_NAME="${SUITE_NAME:-<derived-from-feature>}"
SUITE_PATH="${DATA_DIR}/suites/${SUITE_NAME}.md"
```

Write the generated suite to `${SUITE_PATH}`.

### Step 6: Report

Print the saved path and suggest how to run it:

```
Suite saved to: ${SUITE_PATH}
Run with: /kuma-manual-test ${SUITE_NAME} --repo ${REPO_ROOT}
```

## Workflow - wizard mode

Interactive step-by-step suite generation:

1. Same path resolution as generate mode.
2. Ask feature name, target environment, scope using AskUserQuestion.
3. Show the group structure from `references/suite-structure.md`, ask which groups to include.
4. For each selected group: ask what to test, generate manifests, show for review.
5. User edits/approves each group before moving to next.
6. Save and report same as generate mode.

## Bundled resources

- `references/code-reading-guide.md` - where to find policy specs, xDS generators, tests in a Kuma repo
- `references/suite-structure.md` - suite format spec, group structure, manifest conventions
- `examples/example-motb-core-suite.md` - worked example of a complete test suite

## Example invocations

```bash
# Generate suite for MeshRetry policy
/kuma-suite-author meshretry --repo ~/Projects/kuma

# Generate from a PR
/kuma-suite-author meshexternalservice --from-pr https://github.com/kumahq/kuma/pull/15571

# Generate from a branch
/kuma-suite-author motb --from-branch feat/implement-motb --repo ~/Projects/kuma

# Interactive wizard mode
/kuma-suite-author meshtrace --mode wizard --repo ~/Projects/kuma

# Custom suite name
/kuma-suite-author meshretry --suite-name meshretry-timeout-edge-cases
```
