# Issue Templates

Two templates: **Umbrella Tracker** (single `☂️` parent) and **Child Issue** (one per finding). Replace `{placeholders}` with actual values.

---

## Umbrella Tracker

Title: `☂️ Tech Debt Audit: {repo-name} ({date})`

```markdown
## Summary

Tech debt audit of {repo} ({version}). Each finding is tracked as a subissue below.

**Audit Date:** {date}
**Stack:** {language} / {framework}
**Test Coverage:** {coverage stats if available}
**Vulnerabilities:** {count + severity range, or "none"}

---

## Subissues

### 🔴 Critical Path Blocks
- [ ] #{N} — {child title}

### 🔴 Quick Wins
- [ ] #{N} — {child title}

### 🟠 Strategic
- [ ] #{N} — {child title}

### 🟡 Velocity Improvers
- [ ] #{N} — {child title}

### ⚪ Backlog
- [ ] #{N} — {child title}

**Parallel work:** {note which subissues can be done independently vs need sequencing}

---

## Research Context

Key best practices for {language}/{framework} ({year}):
- {Practice 1 — compared against codebase}
- {Practice 2 — compared against codebase}
- {Practice 3 — compared against codebase}

Sources: {URLs from Phase 2}

---

## Summary Table

| Category | Count | Issues |
|----------|-------|--------|
| Critical Path | {N} | {#numbers} |
| Quick Wins | {N} | {#numbers} |
| Strategic | {N} | {#numbers} |
| Velocity Improvers | {N} | {#numbers} |
| Backlog | {N} | {#numbers} |
| **Total** | {N} | — |

---

## Recommended Order

**This week (Quick Wins):**
1. #{N} — {one-line action}

**This sprint (Strategic):**
1. #{N} — {one-line action}

**Backlog (when prioritized):**
1. #{N} — {one-line action}
```

---

## Child Issue

Title: conventional commits format — `type(scope): description` (max 70 chars). Map by debt category:

- Deps/security → `fix(deps)` / `chore(deps)`
- Test coverage → `test(scope)`
- Build/tooling → `build(scope)` / `ci(actions)`
- Performance → `perf(scope)`
- Refactor → `refactor(scope)`
- Documentation → `docs(scope)`
- New plugin/server feature → `feat(scope)`

```markdown
**Parent:** #{umbrella-issue-number}
**Priority:** {🔴 Critical Path Block | 🔴 Quick Win | 🟠 Strategic | 🟡 Velocity Improver | ⚪ Backlog}

**Affected:** `path/to/file:line` (or module-level reference)

**Why:** {one-sentence motivation — what breaks or hurts because of this}

**Impact:** {High|Medium|Low} — {1-line justification}
**Contagion:** {High|Medium|Low} — {1-line justification}
**Effort:** {High|Medium|Low|Minutes|Hours|Days}

**Fix:**
{Numbered list of concrete steps. Must pass actionability standard: developer can start within 2 days without architectural redesign.}

{Optional: **Test approach:** how to verify the fix works}
{Optional: **Related:** links to related issues, PRs, docs}
{Optional: **Risk:** known unknowns or sequencing constraints}

**Estimated:** {time estimate}
```

---

## Notes

- Apply the audit label (`--label`, default `tech-debt`) to **both** umbrella and children.
- Do not duplicate finding bodies into the umbrella — the umbrella is a tracker only. Subissues hold the detail.
- Keep child titles tight — they appear in the umbrella's tracker list, GitHub issue lists, and commit messages when fixed.
- If a finding spans multiple files but shares one fix, it can be a single child issue. If it spans multiple fixes, split.
