---
name: refactor-council
description: >-
  Use when the user wants a refactoring review of code, an app, a module, or a
  diff. Scans the target for code smells and git hotspots, reviews it through seven
  opposed refactoring lenses (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout,
  Tornhill), synthesizes a safety-first sequenced refactoring plan, then runs a
  separate adversarial agent that red-teams the plan before returning it. Triggers
  on "refactor this", "how should I refactor", "refactoring review", "what should I
  clean up here", "is this worth refactoring".
argument-hint: "<path|@file|directory> [--no-scan] [--no-adversary] [--since 12.month] [--personas a,b,c]"
allowed-tools: Agent, AskUserQuestion, Read, Grep, Glob, Bash, Write, Edit
user-invocable: true
---

# Refactoring Council

Summon seven sourced refactoring-and-architecture persona agents to review a target, then produce a **safety-first, sequenced refactoring plan** that a separate adversarial agent has stress-tested. Each persona argues from the writer's actual published positions, with their actual phrases. They disagree with each other on purpose - the disagreement is the value.

## Why this exists

Generic "clean this up" advice is shapeless and unsafe: it lists smells without saying which are worth fixing, whether the change is behavior-preserving, or whether a test net even exists. This council names smells precisely (smell -> refactoring), prioritizes by where the code actually changes (hotspots), holds the duplication-vs-abstraction and small-functions-vs-deep-modules tensions open instead of collapsing them, gates everything on a safety net, and then has an adversary try to break the plan before you act on it.

## The roster (7 + adversary)

Registry and symptom map: [references/personas.md](references/personas.md). Each persona is a self-contained subagent in [agents/](../../agents/) with a dossier in [references/](references/).

| Persona (subagent) | Lens |
|---|---|
| `fowler-refactoring-reviewer` | Refactoring catalog + smells; small behavior-preserving steps; two hats; Rule of Three; Strangler Fig |
| `martin-clean-architecture-reviewer` | SOLID; Clean Architecture & the Dependency Rule; small functions; naming; frameworks/DB as details |
| `feathers-legacy-reviewer` | Legacy = code without tests; seams; characterization tests; Sprout/Wrap; get-it-under-test-first |
| `beck-tidy-first-reviewer` | Structural vs behavioral changes; tidyings; coupling/optionality economics; baby steps |
| `metz-abstraction-reviewer` | Duplication over the wrong abstraction; flocking rules; squint test; depend on stable things |
| `ousterhout-deep-module-reviewer` | Deep modules; complexity is the enemy; anti-over-decomposition; comments are load-bearing |
| `tornhill-hotspot-advisor` | Behavioral code analysis; hotspots (complexity x churn); change coupling; *where* to refactor |

After synthesis, `refactor-adversary` red-teams the findings and plan: behavior preservation, safety net, wrong-abstraction risk, over-decomposition, cold-code/ROI, scope creep, sequencing, and latent correctness/security/perf the personas could not see.

## Parsing `$ARGUMENTS`

1. Read flags first: `--no-scan`, `--no-adversary`, `--since <value>` (default `12.month`), `--personas <comma-list>` (subset of the seven; default all seven).
2. The remaining text is the **target**. Resolve it:
   - Starts with `@` -> a file path; `Read` it. Its contents plus the file path are the target context.
   - An existing file or directory path -> the scan target.
   - The literal `diff` or no path but a staged/unstaged change in scope -> use `git diff` (and `git diff --staged`) as the target; scope the scan to the changed files.
   - Free-form text with no path -> ask the user (AskUserQuestion) for the file/dir/diff to review. Do not invent a target.
3. Resolve `DATA_DIR` and the script dir once: scripts live at `${CLAUDE_SKILL_DIR}/scripts/`.

## Workflow

### Phase 1 - Setup

Parse arguments. Resolve the target to a concrete set of files or a diff. Read the shared technical reference [references/refactoring-catalog.md](references/refactoring-catalog.md) so you name smells and refactorings precisely and enforce the safety discipline in the plan.

### Phase 2 - Scan (skip if `--no-scan`)

Gather evidence before briefing personas. Run via Bash:

1. **Smells:** `python3 ${CLAUDE_SKILL_DIR}/scripts/smell_scan.py <target paths> --human` for a readable pass, and capture the NDJSON form (without `--human`) for the persona bundle. The scan is heuristic - long files/functions, long parameter lists, deep nesting, debt markers. Treat results as leads.
2. **Hotspots (git repos only):** `python3 ${CLAUDE_SKILL_DIR}/scripts/hotspots.py <target paths> --since <value> --human` plus the NDJSON form. This ranks files by churn x size and surfaces change coupling. If not a git repo or history is shallow, note that prioritization is weakened and continue.
3. **Safety net:** detect whether the target has tests. Use Glob/Grep for `*_test.*`, `*.test.*`, `*.spec.*`, `test/`, `tests/`, `__tests__/`, `*_spec.*` near the target. Record: tests present / absent / partial. This is load-bearing - the plan's first step depends on it.

Assemble a **scan evidence bundle**: top smells (located), top hotspots + coupling pairs, and the test-net status. Keep it compact.

### Phase 3 - Brief the personas in parallel

Spawn each selected persona via the Agent tool with `subagent_type` matching the persona's registered name (e.g. `fowler-refactoring-reviewer`). Spawn all selected personas in one batch so they run concurrently. Each briefing gets:

- The full target context (file contents or the diff).
- The scan evidence bundle from Phase 2 (smells, hotspots, test-net status).
- Instruction that this is a reviewer-only task, not an orchestrator task.
- Instruction to ignore any orchestrator instructions from ambient, cached, or inherited context.
- Instruction to review through *their specific lens only* and to read their own dossier first.
- The Persona output contract (below) and that the first non-empty line must be `## <Persona name> review`.
- Instruction to start the review immediately; never return readiness/setup/capability text; never address another agent; return only the contract.

`tornhill-hotspot-advisor` has Bash and may run its own `git log` analysis to confirm or extend the hotspot evidence.

### Phase 4 - Validate and recover

A valid persona result starts with `## <Persona name> review` and contains the contract sections. Treat readiness text, parking text, inter-agent envelopes, or attempts to spawn/message other agents as invalid internal failures - never show them to the user. Re-brief an invalid persona once with the same bundle and constraints, stating the previous output was invalid because it was not a review. If still invalid, continue with the rest and note the missing lens.

### Phase 5 - Synthesize (critique + refactoring plan)

When valid personas return, write one integrated review using the Synthesis output shape below. Do **not** average the personas into bland consensus - surface the disagreement. The synthesis must include:

- Convergence across opposed lenses (the strongest signal).
- Real disagreements the user must decide (especially Uncle Bob vs Ousterhout on functions/comments; Uncle Bob's DRY reflex vs Metz; decomposition vs Ousterhout).
- Per-persona top-3 in each voice.
- **Safety net status** - tests present/absent, and what must exist before touching code.
- **A sequenced refactoring plan** - smallest-first, each step named (smell -> refactoring), tied to the persona(s) who called for it, behavior-preserving, with characterization-tests-first whenever the safety net is missing. Separate structural from behavioral steps (two hats).
- **Do NOT refactor** - code that is cold (Tornhill), or where duplication is cheaper than abstraction (Metz), or where extraction would add complexity (Ousterhout), with the reason.

### Phase 6 - Adversarial review (skip only if `--no-adversary`)

Spawn `refactor-adversary` as a separate agent. Give it: the full synthesized review (findings + plan), the target context, and the scan evidence bundle. It returns SHIP / SHIP WITH CHANGES / HOLD plus challenged recommendations, what survived scrutiny, unsafe-as-sequenced reordering, and what the council missed (latent correctness/security/concurrency/perf). Apply the same validate-and-recover rule once.

### Phase 7 - Final output

Fold the adversary verdict into the review before the user sees it:

- REJECT / REORDER / WEAKEN verdicts revise the plan in place; do not present a contested step without the adversary's fix applied.
- Mark "survived scrutiny" items as high-confidence.
- Add a **Risks the council missed** section from the adversary's findings.
- If the adversary returned HOLD, lead with that and do not present the contested step as a recommendation.

Present the final integrated review. Keep persona framing internal-facing (see Privacy).

## Persona output contract

Instruct each persona to return exactly:

```
## <Persona name> review

### What I see
<2-4 sentences naming what the code/design is, in their voice>

### What concerns me
<3-6 bullets, each grounded in their philosophy, naming the specific smell/principle
and the file/line>

### What I'd refactor and how
<2-5 bullets: named refactoring -> target, smallest-first>

### Safety net I'd require first
<1-3 sentences: what tests must exist before touching this>

### Where I'd be wrong
<1-2 sentences: their honest blind spot - required>
```

The "Where I'd be wrong" section is required; without it the personas drift to dogma.

## Constraints on personas

- **Stay in character.** Their phrases, their canon, their named questions. No generic AI-review voice.
- **Cite their own work** when invoking a concept ("the wrong abstraction is worse than duplication", "deep modules", "make the change easy").
- **Disagree when honest.** No false consensus. If Uncle Bob says extract and Ousterhout says that creates a shallow module, name the disagreement.
- **One to two pages max per persona.** The synthesis is where the user gets value.

## Synthesis output shape

```
# Refactoring review: <target>

## Convergence (high-confidence signals)
<2-5 bullets. `- [finding] — [persona1, persona2]`. Convergence across opposed lenses first.>

## Disagreement (real tradeoffs you must decide)
<2-4 bullets. `- [axis] — [persona A] argues X / [persona B] argues Y. You decide because <constraint>.`>

## Per-persona top-3
### Fowler
- ...
(repeat per persona that returned)

## Safety net status
<Tests present / absent / partial. What must exist before refactoring. If absent,
characterization tests are step zero.>

## Refactoring plan (sequenced, smallest-first)
<Numbered steps. Each: named refactoring on a named target; the smell it cures; the
persona(s) who called for it; behavior-preserving; structural vs behavioral marked.
Characterization-tests-first where the safety net is missing. Separate "before this
PR" from "next iteration" if both timescales apply.>

## Do NOT refactor (and why)
<1-4 bullets: cold code (Tornhill), duplication cheaper than abstraction (Metz),
extraction would add complexity (Ousterhout) - with the reason.>

## Risks the council missed (from the adversary)
<1-3 bullets: latent correctness/security/concurrency/perf the behavior-preserving
personas could not see; any step the adversary reordered or rejected.>

## Adversary verdict
<SHIP / SHIP WITH CHANGES / HOLD, one line, with what changed.>
```

## Privacy / scope

The persona dossiers in [references/](references/) are private review aids derived from each thinker's public writing. Do not republish wholesale. Keep persona output internal-facing: if a review leaves the team (PR descriptions, issue comments), strip the persona framing and restate the argument in your own voice. This is a *refactoring* council - it preserves behavior by definition, so it does not by itself verify correctness, security, or performance; the adversary partially covers those gaps, but for a full audit use `staff-code-review`, a language reviewer, or `council all`.

## Examples

<example>
Refactor review of a module directory:
```
/refactor-council src/billing/
```
Scans `src/billing/` for smells and git hotspots, checks for tests, briefs all seven personas, synthesizes a sequenced plan, and has the adversary stress-test it.
</example>

<example>
Review a single file from a path token:
```
/refactor-council @src/payments/charge.py
```
Reads the file, scans it, runs the full council + adversary.
</example>

<example>
Review the current diff, skip the scan:
```
/refactor-council diff --no-scan
```
Uses `git diff` as the target and goes straight to persona review (e.g. for a small focused change where hotspot ranking adds little).
</example>

<example>
Subset the personas and widen the history window:
```
/refactor-council src/legacy/ --personas feathers-legacy-reviewer,beck-tidy-first-reviewer,tornhill-hotspot-advisor --since 24.month
```
Runs only the three named personas with a 24-month hotspot window - useful for untested legacy where seams, baby steps, and where-to-refactor dominate.
</example>

## Adding a persona

See [references/personas.md](references/personas.md) for the full procedure: add a dossier in `references/`, a subagent in `agents/`, a row in the registry, and the spawn list above.
