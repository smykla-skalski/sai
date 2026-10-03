---
name: technical-debt-manager
description: Analyze repo for technical debt, research language-specific best practices, create umbrella tracker issue with one subissue per finding. On re-runs, reuses an existing umbrella and dedupes findings against its subissues.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs git and an authenticated GitHub CLI (gh 2.94 or newer for native sub-issue flags; older gh falls back to GraphQL). Uses network access for web research and for creating GitHub issues.
argument-hint: "[--focus area] [--label label-name]"
allowed-tools: Bash Glob Grep Read WebFetch WebSearch Write
user-invocable: true
context: fork
agent: general-purpose
metadata:
  short-description: Audit tech debt into a GitHub issue tracker
---

# Technical Debt Manager

Analyze current repo for technical debt by exploring codebase and researching version-specific best practices. Produce an umbrella ☂️ tracker issue plus one subissue per finding, all rated across 4 axes (impact, effort, contagion, business alignment) with concrete, actionable fix descriptions. Subissues are linked to the umbrella with the GitHub CLI's native sub-issue support (`gh issue create --parent`), so no extra helper scripts are needed.

**Re-run aware:** if an umbrella tracker issue already exists, the skill reuses it — new findings are deduplicated against existing subissues, and only genuinely new debt is filed as fresh subissues linked to the existing umbrella. It never opens a second umbrella.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take `--focus` and `--label` from the user's request; otherwise use the defaults |
| AskUserQuestion | Not used. The skill runs autonomously and reports anything that needs a human decision (regressions, weak dedup matches, stale umbrellas) in the Phase 7 summary |
| Subagent tool (Agent) | Not used. Every phase runs in the current agent loop |
| `context: fork` | Ignored elsewhere; the skill runs in the main agent loop. In Claude Code it runs in a forked general-purpose subagent so the long exploration stays out of the main conversation |
| WebSearch / WebFetch | If the agent has no web tools, or they are blocked, skip Phase 2c and note "limited research" in the umbrella's Research Context section |

In Codex, `gh` and web requests need network access: if the sandbox blocks them, request escalation with a short reason (for example "create tech-debt issues with gh").

## Requirements

- `git` and the GitHub CLI (`gh`), authenticated for the target repo (`gh auth status`)
- gh 2.94 or newer for `gh issue create --parent` and `gh issue view --json subIssues`. On older gh, use the GraphQL fallback in Phase 5d and Phase 1c

## Arguments

Parse from `$ARGUMENTS`:

- **--focus:** Optional — Narrow analysis to specific area (e.g., `error-handling`, `tests`, `dependencies`, `architecture`). Default: full scan.
- **--label:** Optional — GitHub issue label. Default: `tech-debt`. Store it as `LABEL` (`LABEL=tech-debt` when omitted); every command below uses `"$LABEL"`, so a custom label scopes both umbrella detection and dedup

**Shell variables do not persist.** Most agents start a fresh shell for every command, so `LABEL`, `EXISTING_UMBRELLA`, `WORK_DIR`, `PARENT` and `CHILD` set in one command are empty in the next. After a variable is first set, note its value and, in every later command, either substitute that literal value or re-assign the literal at the start of the command (for example `LABEL=tech-debt; PARENT=42; WORK_DIR=/tmp/tmp.Ab12; gh issue create ... --parent "$PARENT"`). Never re-run the command that produced a value: a second `mktemp -d` gives a new empty directory, and a second umbrella `gh issue create` files a duplicate umbrella. Never run a command with an empty `$LABEL`: `gh issue list --label ""` matches every issue, so an unrelated ☂️ issue could be mistaken for the umbrella

## Scope

Analyze technical debt in software repositories with a GitHub remote. Not designed for non-code repos (docs-only, design assets) or repos without version control.

---

## Workflow

### Phase 1: Repo Discovery

**1a. Detect language & framework:**

- Read project config files to identify stack:
  - `package.json`, `tsconfig.json` → TypeScript/JavaScript + framework
  - `go.mod` → Go
  - `pyproject.toml`, `setup.py`, `requirements.txt` → Python + framework
  - `Cargo.toml` → Rust
  - `Gemfile` → Ruby
  - `pom.xml`, `build.gradle` → Java/Kotlin
  - `mise.toml`, `.tool-versions` → Additional tool hints
- Identify test framework, linter, formatter from config
- Note monorepo structure if applicable

**1b. Codebase overview:**

- Glob for directory structure (top 2 levels)
- Count files per language
- Identify entry points, main modules
- Check for CI/CD config (`.github/workflows/`, `Makefile`, etc.)

**1c. Check existing debt items & umbrella issue:**

- If `git remote -v` lists no github.com remote, skip the `gh` steps below, use fresh mode, and expect the local-report path in Phase 5a. If a GitHub remote exists but `gh` fails (no network in a sandbox, not logged in), do not fall back to the local report: request network access or ask the user to run `gh auth login`, then retry
- List existing issues with the audit label (open + closed):
  `gh issue list --label "$LABEL" --state all --limit 1000 --json number,title,body,state,createdAt`
- **Detect an existing umbrella:** an umbrella's title starts with `☂️` (typically `☂️ Tech Debt Audit: …`). If one or more exist, pick the most recent open one as `EXISTING_UMBRELLA` and record its number. If only closed umbrellas exist, treat as none (a fresh audit reopens the cycle).
- **If `EXISTING_UMBRELLA` found, fetch its current subissues** (open + closed) — these are the deduplication baseline for Phase 4.5:
  ```bash
  gh issue view "$EXISTING_UMBRELLA" --json subIssues --jq '.subIssues.nodes[] | {number, title, state}'
  ```
  If `.subIssues.totalCount` is larger than the number of nodes returned, page through the rest with the GraphQL query below (add `pageInfo{hasNextPage endCursor}` and an `after:` cursor) so the baseline is complete.
  On gh older than 2.94 (no `subIssues` JSON field), query GraphQL instead (replace OWNER/REPO with the values from `gh repo view --json owner,name`):
  ```bash
  gh api graphql -H "GraphQL-Features: sub_issues" -f query='
    query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
      issue(number:$n){subIssues(first:100){nodes{number title state}}}}}' \
    -f o=OWNER -f r=REPO -F n="$EXISTING_UMBRELLA" \
    --jq '.data.repository.issue.subIssues.nodes[]'
  ```
  For each subissue, also read its body (`gh issue view N --json body`) to capture the `**Affected:**` file:line reference — needed for accurate dedup. Open subissues = active debt; closed subissues = already fixed.
- Set the run mode: **fresh** (no umbrella → Phase 5 creates one) or **incremental** (umbrella exists → Phase 5 reuses it).
- Read CLAUDE.md / AGENTS.md, README, CONTRIBUTING for known debt items/conventions
- Note any existing TODO/FIXME/HACK conventions

### Phase 2: Research Modern Practices

**2a. Detect specific versions:**

- Extract language VERSION from config (e.g., `"engines": {"node": ">=20"}`, `go 1.22` in go.mod)
- Extract framework VERSION (e.g., `"react": "^18.2"`, `"next": "14.1"`)
- Note: version-specific best practices differ significantly (e.g., Go 1.22 vs 1.18, React 18 vs 17)

**2b. Monorepo handling:**

- If monorepo detected (multiple `package.json`, workspace config, `apps/` + `packages/`), research separately per app/package
- Note shared dependencies and cross-package patterns

**2c. Search for current best practices.**

Search queries (adapt to detected stack — include detected version):

- `"{language} {version} best practices {year}" maintainable code`
- `"{framework} {version} common anti-patterns {year}"`
- `"{language} {version} migration guide" breaking changes` (if version is behind latest)
- `"{language} technical debt indicators checklist"`

Use the available web search capability, then fetch the result pages to extract specific recommendations. Save research summary internally for Phase 3 comparison.

### Phase 3: Codebase Analysis

Re-read the priority axes (Phase 4) before starting — record ratings as findings are discovered, not retroactively.

Read [references/grep-patterns.md](references/grep-patterns.md) before starting this phase.

Run analysis across these categories. For each finding, record: file:line, description, why it matters, fix approach.

**3a. Self-Admitted Debt (SATD markers) & Complexity**

- Search for `TODO`, `FIXME`, `HACK`, `XXX`, `WORKAROUND` comments with Grep
  - Extract 3 lines context around each match
  - Classify severity: `TODO` (low) → `FIXME` (medium) → `HACK` (high) → `XXX` (critical)
  - Check age via `git blame` on flagged lines — older = higher priority
  - Group by theme clusters (e.g., "error handling TODOs", "performance FIXMEs")
- Compare patterns found against Phase 2 research findings
- Apply code quality grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3b. Architecture**

- Compare project structure against language-specific recommendations from Phase 2
- Apply architecture grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3c. Dependencies**

- Check for outdated dependencies: `gh api repos/{owner}/{repo}/dependabot/alerts` or manual check
- Identify pinning issues (too loose or too strict version ranges)
- Check for deprecated packages
- Apply dependency grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3d. Testing**

- Identify untested modules (no corresponding test file)
- Compare test patterns against Phase 2 testing best practices
- Apply testing grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3e. DevOps & Tooling**

- Compare CI/CD setup against Phase 2 recommendations
- Apply DevOps grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3f. Documentation Debt**

- Apply documentation grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**3g. Security Debt**

- Cross-reference dependencies with `gh api repos/{owner}/{repo}/dependabot/alerts`
- Apply security grep patterns from [references/grep-patterns.md](references/grep-patterns.md)

**If `--focus` specified:** Only run the matching sub-phase (3a-3g).

### Phase 4: Prioritize Findings

Rate each finding on 4 axes:

| Rating | Impact | Effort | Contagion | Business Alignment |
|--------|--------|--------|-----------|-------------------|
| **High** | Causes bugs, security risk, blocks features | >1 day, architectural change | Foundational — touches architecture, affects many modules | Blocks product goals, compliance, or release velocity |
| **Medium** | Degrades developer experience, slows development | Hours, localized change | Spreads — affects 2-5 modules or shared patterns | Slows feature delivery but doesn't block |
| **Low** | Style, minor inconsistency, nice-to-have | Minutes, simple fix | Isolated — contained to 1 module | No direct business impact |

> **Contagion** (from Riot Games tech debt taxonomy): How much does this debt propagate? Isolated debt in a single module is less urgent than foundational debt baked into architecture that every new feature inherits.

**Priority matrix:**

- 🔴 **Critical Path Block:** High impact + High contagion → Do first even if high effort
- 🔴 **Quick Wins:** High impact + Low effort + Low contagion → Do immediately
- 🟠 **Strategic:** High impact + High effort → Plan & schedule, consider business alignment
- 🟡 **Velocity Improvers:** Medium impact + Low effort → Batch together
- ⚪ **Backlog:** Low impact → Track, do opportunistically

### Phase 4.5: Deduplicate Against Existing Subissues

**Skip this phase entirely in fresh mode** (no `EXISTING_UMBRELLA`). In incremental mode, classify every Phase 4 finding against the subissue baseline from Phase 1c:

- **Duplicate** — same `file:line` (or same module + same theme) as an existing subissue, open or closed. Drop it; do not refile.
  - If the matching subissue is **open**: it is already tracked — skip silently.
  - If the matching subissue is **closed**: the debt was fixed but reappeared (regression). Do not reopen automatically — list it under "Regressions" in the Phase 7 summary so the user decides.
- **Partial overlap** — touches the same area as an existing subissue but is a distinct fix (e.g. existing issue covers one handler, finding covers a different one). Keep it as a new finding; in its child-issue body add `**Related:** #N` pointing at the overlapping subissue.
- **New** — no match. Keep it; it becomes a fresh subissue.

Match on the `**Affected:**` file:line first, then fall back to title/theme similarity. When in doubt, treat as **new** but flag it in the Phase 7 summary for the user to merge manually — never silently drop a finding on a weak match.

Carry forward only **new** and **partial-overlap** findings into Phase 5. If zero findings survive dedup, skip issue creation and report "no new debt" in Phase 7.

### Phase 5: Create GitHub Issues

Recall the actionability standard and quality checklist (end of this file) before composing issues.

**Output structure:**
- **Fresh mode:** one new ☂️ umbrella tracker issue + one child subissue per finding.
- **Incremental mode:** reuse `EXISTING_UMBRELLA` — one child subissue per *surviving* finding, linked to it; umbrella body merged, not replaced.

All children are linked to the umbrella as native GitHub sub-issues.

Write issue bodies to a scratch directory outside the audited repo so the audit never leaves files behind in it:

```bash
WORK_DIR=$(mktemp -d)
```

**5a. Verify repo has GitHub remote:**

- `gh repo view --json nameWithOwner -q .nameWithOwner`
- If no remote, save as local markdown file instead (create the directory with `mkdir -p` first; this is the same SAI data directory earlier versions used): `${XDG_DATA_HOME:-$HOME/.local/share}/sai/technical-debt-manager/debt-report-{date}.md` (skip rest of Phase 5)

**5b. Check for existing label:**

- Exact-match check (`--search` is fuzzy, so `debt` would match `tech-debt`): `gh label list --limit 1000 --json name --jq '.[].name' | grep -Fxqi "$LABEL"` (label names are case-insensitive on GitHub)
- If missing (the check exits non-zero): `gh label create "$LABEL" --description "Technical debt items" --color "D93F0B"`

**5c. Resolve the umbrella issue.**

**Incremental mode:** reuse the existing umbrella — do not create a new one.

```bash
PARENT=$EXISTING_UMBRELLA
```

**Fresh mode:** create the umbrella first (so children can reference it). Read [references/issue-template.md](references/issue-template.md) for both umbrella and child body structures. Use the **Umbrella Tracker** template. Initially create with placeholder subissue list (or empty) — it will be rewritten in 5e.

```bash
PARENT_URL=$(gh issue create --title "☂️ Tech Debt Audit: {repo} ({date})" --label "$LABEL" --body-file "$WORK_DIR/umbrella.md")
PARENT=$(echo "$PARENT_URL" | grep -oE '[0-9]+$')
```

**5d. Create one child issue per finding, link to umbrella.**

For each finding, write a body to `$WORK_DIR` using the **Child Issue** template from [references/issue-template.md](references/issue-template.md). Title format: conventional commits (`type(scope): description`), max 70 chars. Map priority → type:

- Critical / Quick Win deps/build issues → `fix`, `build`, `chore`
- Strategic perf → `perf`
- Test coverage → `test`
- Refactors → `refactor`
- Docs → `docs`
- Plugin features → `feat`

```bash
for finding in findings; do
  CHILD_URL=$(gh issue create --title "$TITLE" --label "$LABEL" --body-file "$WORK_DIR/$body" --parent "$PARENT")
  CHILD=$(echo "$CHILD_URL" | grep -oE '[0-9]+$')
done
```

`--parent` creates the issue already linked as a sub-issue. To link an issue that already exists (for example after a partial failure), run `gh issue edit "$PARENT" --add-sub-issue "$CHILD"`.

On gh older than 2.94 (no `--parent` flag), create the child without `--parent` and link it with the GraphQL `addSubIssue` mutation:

```bash
# Resolve node IDs, then link (replace OWNER/REPO with the values from `gh repo view --json owner,name`)
PID=$(gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){id}}}' -f o=OWNER -f r=REPO -F n="$PARENT" --jq .data.repository.issue.id)
CID=$(gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){id}}}' -f o=OWNER -f r=REPO -F n="$CHILD" --jq .data.repository.issue.id)
gh api graphql -H "GraphQL-Features: sub_issues" -f query='mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}' -f p="$PID" -f c="$CID"
```

**5e. Update the umbrella body** (now that all new child numbers exist).

**Fresh mode:** write the umbrella body from scratch using the **Umbrella Tracker** template — list each child as `- [ ] #N — title` grouped by priority bucket.

**Incremental mode:** merge, don't replace. Fetch the current body (`gh issue view "$PARENT" --json body -q .body`), then:
- Append each new child as `- [ ] #N — title` into the matching priority bucket, after the existing entries.
- Recompute the Summary Table counts (existing subissues + new) and the `## Recommended Order` lists.
- Add a dated re-audit line under `## Summary`, e.g. `**Re-audit {date}:** +{N} new subissues (#{numbers}).`
- Preserve every existing entry and its checkbox state — never delete or uncheck a tracked item.

```bash
gh issue edit "$PARENT" --body-file "$WORK_DIR/tracker.md"
```

### Phase 6: Measurement Recommendations

Read [references/measurement-template.md](references/measurement-template.md) and append its content to the **umbrella** issue body (after the Summary table). Do not duplicate into child issues.

**Incremental mode:** skip if the umbrella body already contains the measurement section — do not append a second copy.

### Phase 7: Summary

Display in chat.

**Fresh mode:**

```
Tech debt audit complete

Umbrella: {parent-issue-url}
Subissues: {child-issue-numbers, comma-separated}
Findings: {total-count}
  Critical + Quick wins: {count}
  Strategic: {count}
  Velocity improvers: {count}
  Backlog: {count}

Top recommendation: {single most impactful action — reference child #}
```

**Incremental mode:**

```
Tech debt re-audit complete

Umbrella: {existing-umbrella-url} (reused)
New subissues: {new-child-numbers, comma-separated} ({count})
Deduplicated: {count} finding(s) already tracked — skipped
Regressions: {closed subissues whose debt reappeared — #numbers, or "none"}
Needs manual review: {weak-match findings flagged for the user, or "none"}

Top new recommendation: {most impactful new action — reference child #}
```

---

## Error Handling

- **No GitHub remote:** Save report as `${XDG_DATA_HOME:-$HOME/.local/share}/sai/technical-debt-manager/debt-report-{date}.md`
- **No findings:** Create issue noting clean audit, mention practices verified
- **No findings survive dedup (incremental mode):** Skip issue creation; comment on the umbrella that a re-audit on `{date}` surfaced no new debt
- **Multiple open umbrellas found:** Use the most recent; note the others in the Phase 7 summary and suggest the user close the stale ones
- **`sub_issues` GraphQL feature unavailable:** Fall back to listing umbrella subissues by parsing the `- [ ] #N` lines in the umbrella body
- **Rate limited on web search:** Proceed with codebase analysis only, note limited research in issue
- **Very large repo:** Focus on src/lib/app directories, skip vendor/generated/node_modules
- **`--focus` area not applicable:** Inform user, suggest valid areas for this repo

**Do not:**

- Report style-only issues (naming, formatting) as technical debt — those belong in linter config
- Count a finding twice under different categories; deduplicate before Phase 4
- Recommend rewrites without a migration path that fits the actionability standard

## Actionability Standard

Every finding's "Fix" field must pass this litmus test: can a developer start work within 2 days without architectural redesign? If no, break into smaller items.

<example>
Input: A bare exception handler found at `src/api.py:42`
Finding entry:
- [ ] **Bare exception swallows errors** — `src/api.py:42`
  Impact: Silent failures mask bugs in production
  Contagion: Low — isolated to one handler
  Fix: Replace `except:` with `except ValueError as e: logger.error(f'Invalid input: {e}')`
  Effort: Minutes
</example>

<example>
Input: A 65-line function with 4 nested ifs at `main.go:120-185`
Finding entry:
- [ ] **God function in main.go** — `main.go:120-185`
  Impact: Untestable, hard to modify without regressions
  Contagion: Medium — called from 3 handlers
  Fix: Extract `parseConfig()` into `pkg/config/parser.go`, flatten nested ifs with early returns
  Effort: Hours
</example>

<example>
Input: Wildcard dependency pin `"lodash": "*"` in `package.json:15`
Finding entry:
- [ ] **Wildcard dependency pin** — `package.json:15`
  Impact: Allows breaking changes on install
  Contagion: Low — single dependency
  Fix: Pin `lodash` from `*` to `^4.17.21`
  Effort: Minutes
</example>

## Quality Checklist

Before creating issues, verify:

- [ ] Language and framework correctly identified (including version)
- [ ] Web research completed with current-year sources
- [ ] Every finding has file:line reference (or module-level for architecture)
- [ ] Every finding has concrete fix approach (passes actionability standard)
- [ ] All 4 priority axes rated
- [ ] Findings grouped by priority matrix
- [ ] Summary table counts are accurate
- [ ] No duplicate findings
- [ ] Research context section links findings to best practices

- [ ] Incremental mode: every finding classified against existing subissues (duplicate / partial / new)

After creating issues, verify:

- [ ] Exactly one umbrella exists — fresh mode created one, incremental mode reused `EXISTING_UMBRELLA` (no second umbrella opened)
- [ ] Umbrella issue title starts with ☂️
- [ ] Each child issue title follows conventional commits format (`type(scope): description`)
- [ ] Each child issue references the umbrella in its body (`**Parent:** #N`)
- [ ] Every new child is linked to the umbrella as a sub-issue (`gh issue view "$PARENT" --json subIssues --jq .subIssues.totalCount` shows the correct count; `subIssuesSummary` can lag behind)
- [ ] Umbrella body is the tracker (not duplicated finding bodies)
- [ ] Incremental mode: existing subissue entries and checkbox states preserved; new entries appended; Summary Table counts recomputed
