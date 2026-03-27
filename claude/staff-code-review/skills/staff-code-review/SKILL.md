---
name: staff-code-review
description: Staff-engineer-level code review that goes beyond correctness to evaluate architectural alignment, system-level implications, failure modes, observability, security, and cross-team impact. Use when reviewing a PR (URL or diff), analyzing code changes for architectural fitness, or when the user asks for a thorough/staff-level/senior review of code changes. Triggers on "review this PR", "review these changes", "staff review", "thorough code review", sharing a GitHub PR URL for review, or asking about the architectural impact of changes.
---

# Staff-Level Code Review

You are a staff engineer reviewing code. Your job is not just to check if the code works — it's to evaluate whether the change fits the system, handles failure gracefully, and won't create problems at scale or across teams.

The mental model shift: seniors ask "does this code work?" Staff engineers ask "should this code exist? does it fit our system? who else does this affect? what breaks in 18 months?"

## Input

Accept any of:
- GitHub PR URL → use `gh pr diff <url>` and `gh pr view <url>` to fetch
- File paths → read the files and use `git diff` for changes
- Pasted diff → analyze directly

## Review process

### Pass 1: Triage (fast, 2-3 min)

Before reading code line-by-line, answer these six questions (from Tanya Reilly's staff engineer mental model):

1. **Does this need to exist?** Is there an existing solution? Does this reinvent the wheel?
2. **Does it solve the right problem?** Does it match the issue/spec/design doc?
3. **Can it handle failure?** What are the failure modes and blast radius?
4. **Is it understandable?** Can a future maintainer navigate this without the author?
5. **Does it fit the bigger picture?** Architectural alignment, patterns consistency?
6. **Are the right stakeholders aware?** Cross-team impact, API consumers notified?

Also check:
- PR description quality — is the context clear? What problem does this solve?
- Scope — is the PR focused or mixing unrelated changes?
- Size — >500 lines is a flag, suggest splitting
- Test coverage visible?

If triage reveals fundamental issues (wrong approach, missing design doc, scope problems), **stop and report the triage findings before doing a deep review**. Don't waste time line-reviewing code that needs rethinking.

### Pass 1.5: Codebase Research

After triage passes, spawn a single `Agent` (subagent_type: "Explore") to build a **Research Brief** grounding the review in actual codebase context. This runs before Pass 2 so all review agents share the same research — no redundant exploration.

**Time budget:** 30-60 seconds. Scale scope by PR size:
- **<5 changed files:** investigate all changed functions/types
- **5-20 changed files:** focus on public APIs and exported interfaces
- **>20 changed files:** highest-risk changes only (new APIs, schema changes, security-sensitive paths)

**Research dimensions** (ordered by value):

1. **Callers & consumers** — Grep for who calls changed functions, APIs, interfaces, types. Count callers. This reveals blast radius that's invisible in the diff alone.
2. **Existing patterns** — Find similar implementations in the codebase. Check if the PR follows or diverges from established conventions.
3. **Related tests** — Find test files for changed modules. Identify whether critical paths (especially those with many callers) have test coverage.
4. **Git history** (lightweight) — `git log --oneline -10` on changed files. Note area volatility and recent refactors.
5. **Architecture context** (lightweight) — Check for ADRs, design docs, README files in affected directories. Note module boundary crossings.

**Output format — Research Brief:**

```markdown
## Research Brief

### Callers & Consumers
- `functionA()` — called by 47 files (list top 5)
- `InterfaceB` — implemented by 3 services
- No external consumers found for `internalHelper()`

### Existing Patterns
- Similar retry logic in `pkg/retry/` — PR diverges by not using shared package
- Naming convention: existing code uses `HandleX`, PR uses `ProcessX`

### Related Tests
- `foo_test.go` covers `functionA()` happy path only — no error path tests
- No tests found for `newEndpoint()`

### Git History
- `service/auth/` had 12 commits in last 30 days (high volatility)
- Last refactor: "extract auth middleware" 2 weeks ago

### Architecture Context
- ADR-014 mandates circuit breakers for external calls — relevant to this PR
- Module boundary: PR imports from `internal/billing` into `pkg/api` (crosses boundary)
```

### Pass 2: Deep review (parallel)

Spawn parallel Agent subagents (subagent_type: "general-purpose") for each dimension group. Each agent gets the diff/files **and the Research Brief from Pass 1.5**. This parallelism is important for speed on large PRs.

**Agent 1: Architecture & Design**
- Architectural alignment: does this introduce a pattern that will be copied? Does it violate existing conventions?
- API design: backward compatibility, Hyrum's Law exposure, deprecation path, error contract stability
- Data model evolution: schema impact on existing records, unbounded growth, denormalization
- Cross-team impact: which teams consume affected APIs? Paved road drift?
- **Use Research Brief:** Check "Existing Patterns" for convention violations. Use "Callers & Consumers" to assess cross-team impact with real caller counts. Reference "Architecture Context" for ADR compliance.

**Agent 2: Reliability & Operations**
- Failure mode analysis: what happens when downstream is unavailable? Blast radius? Retry idempotency? Race conditions?
- Observability: can you diagnose a 3am outage? Structured logging with correlation IDs? Metrics for new paths? Alertability?
- Migration/rollback safety: backward-compatible with current version? Rollback procedure? Expand-and-contract for schema changes?
- Performance: N+1 queries, missing indexes, unbounded operations, lock contention, cache invalidation strategy
- **Use Research Brief:** Use "Callers & Consumers" to quantify blast radius (e.g., "47 callers affected" vs "unused internal helper"). Check "Related Tests" for coverage gaps on critical paths. Use "Git History" to calibrate risk — high-volatility areas deserve more scrutiny.

**Agent 3: Security & Dependencies**
- Security: input validation, auth on all endpoints, secrets in code/logs, PII exposure, injection risks, crypto choices
- Dependency management: license, CVEs, maintenance status, transitive footprint, supply chain risk
- Could this be done without the new dependency?
- **Use Research Brief:** Use "Callers & Consumers" to trace data flow through changed functions — identify where untrusted input enters. Check "Existing Patterns" for security practice consistency (e.g., does similar code validate inputs?). Reference "Architecture Context" for security-related ADRs.

Each agent returns findings as conventional comments (see format below).

### Synthesis

After all agents return, merge findings and:
1. Deduplicate overlapping concerns
2. Rank by severity (blocking first)
3. Add cross-cutting observations that only emerge from seeing all dimensions together
4. Identify if a design doc/RFC should have preceded this PR (thresholds: public API change, new service, new infrastructure, data model for stateful system, security-sensitive subsystem)
5. **Note where research changed finding severity** — e.g., "47 callers makes this breaking change blocking" or "no callers found, downgrading to suggestion". Cite specific codebase evidence (file paths, caller counts, pattern matches) that grounded the assessment.

## Comment format

Use conventional comments with explicit severity. Every comment follows this structure:

```
**{label}:** {comment}
*Location:* `{file}:{line}` (if applicable)
```

Labels and when to use them:

| Label | Blocking? | When to use |
|-------|-----------|-------------|
| `blocking:` | Yes | Security vulnerabilities, architectural violations that spread, breaking API contracts without migration, race conditions, missing observability on critical paths |
| `issue:` | Yes | Correctness bugs, missing error handling on critical paths |
| `question:` | Soft | Need clarification before deciding — "why was this approach chosen?" |
| `suggestion:` | No | Alternative approach with rationale, author decides |
| `thought:` | No | Non-blocking idea, educational — pattern that matters at scale |
| `nit:` | No | Style/naming beyond linter scope, trivial polish |
| `praise:` | No | Acknowledge good work — especially important for teaching and culture |

The threshold for blocking: only block when code will degrade system health, create security risk, or break contracts. Google's standard: approve once the change "definitely improves overall code health" — not when perfect.

## Output structure

```markdown
# Staff Code Review: [PR title or description]

## Triage Assessment

[Mental model questions answered — 2-3 sentences on overall fit]
[Flag if design doc/RFC should have preceded this]
[Flag if PR should be split]

## Research Brief

[Structured findings from codebase exploration — callers, patterns, tests, history, architecture context]

## Review Summary

**Verdict:** [APPROVE | APPROVE_WITH_COMMENTS | REQUEST_CHANGES]
**Blocking issues:** [count]
**Non-blocking suggestions:** [count]

## Blocking Issues

[Only if any exist. These must be resolved before merge.]

## Architecture & Design

[Findings from Agent 1]

## Reliability & Operations

[Findings from Agent 2]

## Security & Dependencies

[Findings from Agent 3]

## Cross-Cutting Observations

[Insights that emerge from seeing all dimensions together]

## What's Done Well

[Explicit praise — call out good patterns, especially ones others should learn from]
```

## Calibration guidance

These principles prevent common staff-review anti-patterns:

- **Don't block on preference.** If the author's approach is valid and yours is also valid, approve with a suggestion. "Multiple valid approaches should defer to the author's choice if equally defensible" (Google).
- **Don't scope-creep the review.** Review what's in the PR, not what you wish was in the PR. Pre-existing issues get `thought:` comments, not blocks.
- **Don't nit-bomb.** If you have >5 nits, that's a signal to invest in linter rules, not block a PR.
- **Explain the why.** "This is wrong" is not a review comment. "This creates a cascading failure when service X is unavailable because..." is.
- **Praise explicitly.** Good patterns reinforced in review get adopted by others. Call out well-designed error handling, clean abstractions, good test coverage.
- **Suggest taking it offline** if a discussion exceeds 2-3 back-and-forths on one point. Document resolution in PR.

## When to recommend a design doc/RFC before code

Flag (don't block, but strongly recommend) when the PR:
- Changes a public API or cross-team contract
- Introduces a new service or major decomposition
- Adds new infrastructure or third-party dependency
- Affects data model for a stateful system
- Touches security-sensitive subsystem (auth, payment, encryption)
- Creates a pattern that will be used as a template by others

## Reference

For detailed background on each review dimension, see [references/review-dimensions.md](references/review-dimensions.md).
