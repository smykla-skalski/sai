---
name: refactor-council
description: >-
  Run the refactoring council from a normal Copilot session when the user asks for
  a refactoring review of code, a module, an app, or a diff. Scans the target for
  code smells and git hotspots, reviews it through seven opposed refactoring lenses
  (Fowler, Uncle Bob, Feathers, Beck, Metz, Ousterhout, Tornhill), synthesizes a
  safety-first sequenced refactoring plan, then a separate adversary agent red-teams
  the plan before it is returned. Accept flags `--no-scan`, `--no-adversary`,
  `--since <value>`, `--personas <comma-list>`. Do not use for a quick lint pass or
  a standalone correctness/security/performance audit.
allowed-tools:
  - agent
  - list_agents
  - shell
  - read
---

# Refactor Council (Copilot)

Summon seven sourced refactoring-and-architecture reviewer agents, then produce a safety-first, sequenced refactoring plan that a separate adversary agent has stress-tested. The reviewers are native Copilot custom agents bundled with this plugin; the current session agent acts as the orchestrator. The reviewers argue from the writers' actual published positions and disagree with each other on purpose - the disagreement is the value.

## The roster (7 + adversary)

Bundled as custom agents under `agents/` (namespaced, e.g. `refactor-council:fowler-refactoring-reviewer`). Registry and symptom map: [references/refactoring-catalog.md](references/refactoring-catalog.md) for the smell/refactoring vocabulary and safety discipline.

| Reviewer agent | Lens |
|---|---|
| `fowler-refactoring-reviewer` | Refactoring catalog + smells; small behavior-preserving steps; two hats; Rule of Three; Strangler Fig |
| `martin-clean-architecture-reviewer` | SOLID; Clean Architecture & the Dependency Rule; small functions; naming; frameworks/DB as details |
| `feathers-legacy-reviewer` | Legacy = code without tests; seams; characterization tests; Sprout/Wrap; get-it-under-test-first |
| `beck-tidy-first-reviewer` | Structural vs behavioral changes; tidyings; coupling/optionality economics; baby steps |
| `metz-abstraction-reviewer` | Duplication over the wrong abstraction; flocking rules; squint test; depend on stable things |
| `ousterhout-deep-module-reviewer` | Deep modules; complexity is the enemy; anti-over-decomposition; comments are load-bearing |
| `tornhill-hotspot-advisor` | Behavioral code analysis; hotspots (complexity x churn); change coupling; *where* to refactor |

After synthesis, `refactor-adversary` red-teams the findings and plan.

## Parsing the request

1. Read flags: `--no-scan`, `--no-adversary`, `--since <value>` (default `12.month`), `--personas <comma-list>` (subset of the seven; default all seven).
2. The remaining text is the target: a path, a directory, an `@file`, or `diff` (use `git diff`). If none is resolvable, ask which file/dir/diff to review - do not invent one.

## Workflow

### Phase 1 - Setup

Resolve the target. Read [references/refactoring-catalog.md](references/refactoring-catalog.md) so you and the reviewers name smells and refactorings precisely and enforce the safety discipline in the plan.

### Phase 2 - Scan (skip if `--no-scan`)

Run the bundled scanners via shell and gather a compact evidence bundle:

- Smells: `python3 scripts/smell_scan.py <target paths> --human`
- Hotspots (git repos only): `python3 scripts/hotspots.py <target paths> --since <value> --human`
- Safety net: detect tests near the target (`*_test.*`, `*.test.*`, `*.spec.*`, `test/`, `tests/`, `__tests__/`). Record present / absent / partial.

The bundle (top located smells, top hotspots + coupling pairs, test-net status) is load-bearing - pass it to every reviewer. If not a git repo or history is shallow, say so and note that prioritization is weakened.

### Phase 3 - Reviewer delegation (sequential by default)

Delegate each selected reviewer through the `agent` tool, giving each: the target context, the scan evidence bundle, the Persona output contract below, and the instruction that the first line must be `## <display name> review`.

**Default to sequential delegation - one reviewer at a time.** Copilot parallel fan-out via `/fleet` over-parallelizes and burns AI credits, and offers no reliability guarantee for an 8-agent council; sequential delegation is the reliable path here. Only fan out in parallel if the user explicitly asks, and then run small waves (<= 5) and confirm each reviewer returned a payload before synthesizing.

Validate each reviewer result: it must start with `## <display name> review` and contain the contract sections. Re-delegate an invalid reviewer once with the same bundle; if still invalid, continue and note the missing lens. Never surface raw reviewer envelopes or readiness text.

### Phase 4 - Synthesize (critique + plan)

Write one integrated review using the Synthesis output shape below. Surface disagreement (especially Uncle Bob vs Ousterhout on functions/comments; Uncle Bob's DRY reflex vs Metz; decomposition vs Ousterhout); do not flatten it. Include the safety-net status, a sequenced smallest-first refactoring plan (characterization-tests-first when untested; structural vs behavioral separated, two hats), and an explicit "Do NOT refactor" list (cold code, duplication cheaper than abstraction, extraction that adds complexity).

### Phase 5 - Adversarial pass (skip only if `--no-adversary`)

Delegate `refactor-adversary` with the full synthesized review (findings + plan), the target context, and the scan evidence. It returns SHIP / SHIP WITH CHANGES / HOLD plus challenged recommendations, what survived scrutiny, unsafe-as-sequenced reordering, and what the council missed. Apply the same validate-and-retry rule once.

### Phase 6 - Final output

Fold the adversary verdict in before presenting: REJECT/REORDER/WEAKEN revise the plan in place; mark "survived scrutiny" items high-confidence; add a "Risks the council missed" section; if HOLD, lead with it and do not present the contested step without the fix. Keep reviewer framing internal (see Privacy).

## Persona output contract

```
## <display name> review

### What I see
<2-4 sentences naming what the code/design is, in their voice>

### What concerns me
<3-6 bullets, each naming the specific smell/principle and the file/line>

### What I'd refactor and how
<2-5 bullets: named refactoring -> target, smallest-first>

### Safety net I'd require first
<1-3 sentences: what tests must exist before touching this>

### Where I'd be wrong
<1-2 sentences: their honest blind spot - required>
```

## Synthesis output shape

```
# Refactoring review: <target>

## Convergence (high-confidence signals)
## Disagreement (real tradeoffs you must decide)
## Per-persona top-3
## Safety net status
## Refactoring plan (sequenced, smallest-first)
## Do NOT refactor (and why)
## Risks the council missed (from the adversary)
## Adversary verdict
```

(Same content as the Claude skill: convergence first, named disagreement, per-persona top-3 in voice, safety-net status with characterization-tests-first when untested, a sequenced behavior-preserving plan with structural vs behavioral marked, an explicit do-not-refactor list, and the adversary's caught risks and verdict.)

## Privacy / scope

The reviewer dossiers under `agents/references/` are private review aids derived from each thinker's public writing. Do not republish wholesale; keep reviewer framing internal - if a review leaves the team, restate the argument in your own voice. This is a *refactoring* council: it preserves behavior by definition, so it does not by itself verify correctness, security, or performance. The adversary partially covers those gaps; for a full audit use a staff-level or language-specific review.
