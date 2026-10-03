# Evaluation cases for technical-debt-manager

Test cases for verifying skill behavior across different repo types.

## Cases

### 1. Go repo with outdated deps and TODOs

- **Input:** Go 1.21 repo with 5 TODO comments, 2 deprecated deps, no tests
- **Expected:** Issue created with findings grouped by priority; Go 1.22+ migration noted in research; untested modules flagged in 3d
- **Verify:** All findings have file:line, concrete fix, 4-axis rating

### 2. No GitHub remote

- **Input:** Local-only git repo (no remote)
- **Expected:** Markdown report saved to `${XDG_DATA_HOME}/sai/technical-debt-manager/debt-report-{date}.md`
- **Verify:** No `gh issue create` attempted; report has same structure as issue

### 3. Clean repo

- **Input:** Well-maintained repo with no TODOs, current deps, full test coverage
- **Expected:** Issue created noting clean audit, practices verified
- **Verify:** Issue body mentions which practices were checked

### 4. --focus flag

- **Input:** `--focus dependencies` on a Node.js repo with wildcard pins
- **Expected:** Only Phase 3c runs; other sub-phases skipped
- **Verify:** No architecture or testing findings in output

### 5. Monorepo

- **Input:** Turborepo with 3 packages, mixed TypeScript versions
- **Expected:** Per-package research in Phase 2b; findings reference specific package paths
- **Verify:** Cross-package dependency issues noted under contagion
