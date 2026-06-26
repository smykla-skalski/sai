---
name: staff-code-review
description: >-
  Run a staff-level code review from a normal Copilot session when the user asks to
  review a PR, a diff, or a set of changes (a GitHub PR URL, file paths, or a pasted
  diff). Triages the change, builds a research brief, delegates to seven native
  dimension reviewer agents plus a code adversary, synthesizes, then a findings
  adversary red-teams the result before it is returned or posted. Accepts the flag
  `--no-adversary` (skip both adversary passes). Do not use for a quick lint pass or
  a single-file style nit.
allowed-tools:
  - agent
  - list_agents
  - read_agent
  - write_agent
  - shell
  - read
---

# Staff-Level Code Review (Copilot)

Review code as a staff engineer from a normal Copilot session. Go beyond correctness — evaluate whether the change fits the system, handles failure gracefully, and won't create problems at scale or across teams. The mental-model shift: seniors ask "does this code work?"; staff engineers ask "should this code exist? does it fit our system? who else does this affect? what breaks in 18 months?"

You are the **orchestrator**. You stay in-session, do the triage and research yourself, delegate each review dimension to a native Copilot custom agent bundled with this plugin (under `agents/`, e.g. `staff-code-review:architecture-design-reviewer`), synthesize their findings, and gate the result through an adversary before returning or posting it. Keep reviewer framing internal — return one integrated staff review, not eight agent transcripts.

## The roster (7 dimensions + 2 adversaries)

| Agent | Role |
|---|---|
| `architecture-design-reviewer` | Architectural fit, API design, data-model evolution, cross-team impact |
| `reliability-operations-reviewer` | Failure modes, observability, migration/rollback safety |
| `security-dependencies-reviewer` | Input validation, authz, secrets, injection, dependency risk |
| `performance-scalability-reviewer` | Resource efficiency, scalability under growth, operational readiness |
| `backward-compatibility-reviewer` | Source/wire/behavioral compatibility, rollback, migration path |
| `convention-conformance-reviewer` | Repo conventions, code reuse, anti-duplication |
| `dead-code-reviewer` | Newly dead and orphaned code |
| `code-adversary` | Red-teams the **code** — finds the concrete bug with a failing input |
| `review-adversary` | Red-teams the **findings** post-synthesis — kills false positives |

## Phase 1 — Input parsing

Resolve the target from the request, then strip flags before resolving:

- **GitHub PR URL** → fetch with `gh pr diff <url>` and `gh pr view <url>` via `shell`. Remember owner/repo/number for the Post phase.
- **File paths** → read the files and use `git diff` (or `git diff <base>...HEAD`) for the changes.
- **Pasted diff** → analyze directly.

Flags:
- `--no-adversary` → skip **both** adversary passes (the Code Adversary in Phase 5 and the Findings Adversary in Phase 7). Default is to run both.

If no target is resolvable, ask which PR/diff/files to review — do not invent one.

## Phase 2 — Triage (fast, 2-3 min)

Before reading line-by-line, answer the six staff mental-model questions (Tanya Reilly):

1. **Necessity** — check for existing solutions; flag reinvention.
2. **Problem fit** — verify alignment with the issue/spec/design doc.
3. **Failure tolerance** — identify failure modes and blast radius.
4. **Comprehensibility** — can a future maintainer navigate this without the author?
5. **Architectural fit** — pattern consistency and alignment.
6. **Stakeholder awareness** — cross-team impact, unnotified API consumers.

Also check: PR description quality, scope (flag mixed unrelated changes), size (flag >500 lines, suggest splitting), test coverage (flag if not visible).

**If triage reveals fundamental issues** (wrong approach, missing design doc, scope problems), **stop and report the triage findings before the deep review.** Don't line-review code that needs rethinking.

## Phase 3 — Research Brief (build inline, do NOT delegate)

Build the Research Brief yourself with `shell` (grep/git) and `read`. Do not delegate this — every reviewer needs the same brief, so produce it once and pass it verbatim into every delegation.

Time budget 30-60s. Scale scope by size: <5 changed files → all changed functions/types; 5-20 → public APIs and exported interfaces; >20 → highest-risk only (new APIs, schema changes, security-sensitive paths).

Research dimensions, ordered by value:
1. **Callers & consumers** — grep who calls changed functions/APIs/types; count callers. This is the blast radius invisible in the diff.
2. **Existing patterns** — similar implementations; does the change follow or diverge from convention?
3. **Related tests** — test files for changed modules; coverage on critical (high-caller) paths.
4. **Git history** (lightweight) — `git log --oneline -10` on changed files; note volatility and recent refactors.
5. **Architecture context** (lightweight) — ADRs, design docs, READMEs in affected dirs; module-boundary crossings.

Emit it as a `## Research Brief` section with sub-headings (Callers & Consumers / Existing Patterns / Related Tests / Git History / Architecture Context). Cite concrete evidence (paths, caller counts, pattern matches).

## Phase 4 — Dimension delegation (sequential by default)

Read `references/review-dimensions.md` before distributing work — it holds the detailed checklist for each dimension.

Delegate each of the seven dimension reviewers through the `agent` tool, one at a time, giving each: the diff / changed files, the Research Brief verbatim, and the instruction that **its first line must be `## <Dimension> review`**. The dimension reviewers already know their checklist and severity calibration from their own system prompts (and read their own deep references where applicable) — your job is to feed them the change and the brief.

> Default to sequential reviewer delegation - one agent at a time. Copilot parallel fan-out over-parallelizes and burns AI credits and offers no reliability guarantee for a multi-agent council; sequential is the reliable path. Only fan out in parallel if the user explicitly asks, then run small waves (<= 5), supervise with list_agents/read_agent, and confirm each agent returned a payload before synthesizing.

Expected first lines, in order:
1. `staff-code-review:architecture-design-reviewer` → `## Architecture & Design review`
2. `staff-code-review:reliability-operations-reviewer` → `## Reliability & Operations review`
3. `staff-code-review:security-dependencies-reviewer` → `## Security & Dependencies review`
4. `staff-code-review:performance-scalability-reviewer` → `## Performance & Scalability review`
5. `staff-code-review:backward-compatibility-reviewer` → `## Backward Compatibility review`
6. `staff-code-review:convention-conformance-reviewer` → `## Convention Conformance & Code Reuse review`
7. `staff-code-review:dead-code-reviewer` → `## Dead Code review`

**Validate each result starts with `## <Dimension> review`** and contains conventional-comment findings. If a result is invalid (wrong header, empty, or readiness/boilerplate text), re-delegate that dimension once with the same diff + brief; if still invalid, continue and note the missing lens in synthesis. Never surface raw reviewer envelopes.

## Phase 5 — Code Adversary (skip if `--no-adversary`)

Delegate `staff-code-review:code-adversary` with the diff / changed files and the Research Brief, plus: *"Assume this change has a bug. Find it and prove it with a concrete failing input or sequence. Read the surrounding code, not just the hunks. Emit findings as conventional comments with `*Location:*` and end with your verdict line."* It emits conventional-comment format directly and ends with `**Code adversary verdict:** ...` — pass its output straight to synthesis (no translation step).

## Phase 6 — Synthesis

Merge the seven dimension reviews and the Code Adversary findings into one integrated review:
1. **Deduplicate** overlapping concerns. The Code Adversary often lands on the same line as a dimension reviewer from another angle — merge into one finding, keeping the most concrete failing scenario.
2. **Rank by severity** (blocking first).
3. **Cross-cutting observations** that only emerge from seeing all dimensions together.
4. **Design-doc/RFC threshold** — note if one should have preceded this change (public API change, new service, new infrastructure, data model for a stateful system, security-sensitive subsystem).
5. **Note where research changed severity** — e.g., "47 callers makes this breaking change blocking" or "no callers found, downgrading to suggestion". Cite the codebase evidence.

The dimension agents already emit conventional comments, so there is **no persona-translation step**. Do not validate blocking findings inline here — that is the Findings Adversary's job.

## Phase 7 — Findings Adversary (skip if `--no-adversary`)

Delegate `staff-code-review:review-adversary` with the full synthesized findings (every finding with severity and `*Location:*`), the Research Brief, and the diff, plus: *"Red-team these findings. Default to skepticism. Verify every blocking and issue finding against the actual code. Return your verdict in the required output format."*

It returns SHIP / SHIP WITH CHANGES / HOLD plus challenged findings (UPHOLD / DOWNGRADE→label / REMOVE / REWORD), survived-scrutiny, findings the reviewers missed (escaped bugs), bad locations, and the evidence it checked. Apply the same validate-and-retry-once rule.

Fold its verdict in **before anything downstream sees the review:**
- REMOVE / DOWNGRADE / REWORD verdicts revise findings in place — never present a contested finding without the correction applied.
- Mark "survived scrutiny" findings high-confidence.
- Promote any escaped bug into the review with proper severity and `*Location:*`.
- Drop or correct every "bad location" so the GitHub post cannot fail on an out-of-diff line.
- Recompute the verdict and blocking/non-blocking counts in **Review Summary**.
- If the verdict is HOLD, lead with it; do not present the contested finding as a blocker without its fix.

## Phase 8 — Humanize (inline)

Rewrite the prose in all review comment messages to remove AI-writing patterns so the review reads like a human staff engineer wrote it. Do this inline — apply active voice, concrete language, omit needless words, vary sentence structure. **Never modify** the structural elements: label prefixes (`**blocking:**` etc.), `*Location:*` lines, markdown headings, the Review Summary, code blocks, file paths, line numbers, or any technical detail. Keep messages tight (≤280 chars). Do not add information that wasn't in the original.

## Phase 9 — Save the review

Persist the full review markdown:

```bash
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sai/staff-code-review/reviews"
mkdir -p "$DATA_DIR"
```

- Prefix: the PR number (the `/pull/{number}` segment) if the input was a PR URL, otherwise `local`.
- Timestamp: `date -u +%Y%m%dT%H%M%S`.
- Write the complete review markdown to `${DATA_DIR}/{pr|local}-{timestamp}.md` and report the saved path.

## Phase 10 — Post to GitHub (only if the input was a PR URL)

**Skip this phase entirely if the input was not a GitHub PR URL.** Create a PENDING (draft) review — invisible to the author until they submit it from GitHub's UI.

1. Parse owner/repo/PR number from the URL.
2. Extract inline comments from the saved review file:
   ```bash
   python3 scripts/parse_review_comments.py "$REVIEW_FILE"
   ```
   The script keeps all blockers/issues, up to 5 suggestions, up to 3 praises, and excludes questions/thoughts/nits.
3. Write a concise top-level review body (2-4 sentences): lead with the verdict and why; mention the 1-2 most important findings; state blocking counts only if there are blockers. Do **not** mention the tool, "staff code review", or that this was AI-generated.
4. Build a PENDING payload — `{"body": ..., "comments": [...]}` with `"side": "RIGHT"` on each comment and **no `event` field** (omitting `event` is what makes it PENDING) — and submit:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{number}/reviews --input -
   ```
5. Report the review URL and comment count, and **remind the user the review is PENDING** — they must open GitHub and click "Submit review" to publish; they can edit/delete comments first.
6. **Do not re-run the API call after it exits 0** — creation is atomic. If it fails, the most common cause is a `file:line` not visible in the diff; report the error and the saved file path so the user can inspect and retry.

## Comment format

Every file-specific finding is a conventional comment with explicit severity — exactly two lines, because `parse_review_comments.py` depends on it:

```
**{label}:** {message}
*Location:* `{path/to/file}:{line}`
```

Rules: label + message on the first line; `*Location:*` on its own line immediately after, with backtick-wrapped `path:line`; path relative to repo root, no leading `./`; line is the exact current-file line (not the diff line); message ≤280 chars, problem-and-impact first then the fix, explain the *why*. Cross-cutting observations and overall praise that don't map to a line may omit `*Location:*` — those go in the review body.

| Label | Blocking? | When to use |
|-------|-----------|-------------|
| `blocking:` | Yes | Security vulns, architectural violations that spread, breaking contracts without migration, race conditions, missing observability on critical paths |
| `issue:` | Yes | Correctness bugs, missing error handling on critical paths |
| `question:` | Soft | Need clarification before deciding |
| `suggestion:` | No | Alternative approach with rationale; author decides |
| `thought:` | No | Non-blocking idea, educational, scale-relevant |
| `nit:` | No | Style/naming beyond linter scope |
| `praise:` | No | Acknowledge good work |

Threshold for blocking: only block when code will degrade system health, create security risk, or break contracts. Google's bar — approve once the change "definitely improves overall code health", not when perfect. Don't block on preference; don't nit-bomb (>5 nits → linter rule, not a block); explain the why; praise explicitly.

## Output structure

```markdown
# Staff Code Review: <title>

## Triage Assessment
[Six mental-model questions answered — 2-3 sentences on overall fit. Flag if a design doc/RFC should have preceded this. Flag if the PR should be split.]

## Research Brief
[Callers & Consumers / Existing Patterns / Related Tests / Git History / Architecture Context]

## Review Summary
**Verdict:** [APPROVE | APPROVE_WITH_COMMENTS | REQUEST_CHANGES]
**Blocking issues:** [count]
**Non-blocking suggestions:** [count]
**Adversary verdicts:** Code: [FOUND BLOCKING (N) | FOUND ISSUES (N) | MINOR ONLY (N) | CLEAN] · Findings: [SHIP | SHIP WITH CHANGES | HOLD]

## Blocking Issues
[Only if any exist — must be resolved before merge.]

## Architecture & Design
## Reliability & Operations
## Security & Dependencies
## Performance & Scalability
## Backward Compatibility
## Convention Conformance & Code Reuse
## Dead Code
[Per-dimension findings, deduped and severity-ranked.]

## Adversarial Findings
[Bugs the Code Adversary found by red-teaming the change, each with a concrete failing input. Findings already merged into a dimension section need not repeat — list only adversary-unique ones.]

## Cross-Cutting Observations
[Insights that emerge from seeing all dimensions together.]

## Adversary Verdict
[Code Adversary verdict (Phase 5) and Findings Adversary verdict (Phase 7). Note which findings survived scrutiny (high-confidence), which were downgraded/removed, and any escaped bug. Omit entirely if `--no-adversary`.]

## What's Done Well
[Explicit praise — call out patterns others should learn from.]
```

## Privacy / scope

Keep reviewer framing internal — the user gets one integrated staff review, not the individual agent transcripts. This skill reviews a change; it does not run the code. Run it only when the user explicitly asks for a review.
