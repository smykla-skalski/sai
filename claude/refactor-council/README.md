# refactor-council

Run a refactoring review through seven sourced refactoring-and-architecture persona agents - Martin Fowler, Robert C. Martin (Uncle Bob), Michael Feathers, Kent Beck, Sandi Metz, John Ousterhout, and Adam Tornhill. The council scans the target for code smells and git hotspots, reviews it through opposed lenses, synthesizes a safety-first sequenced refactoring plan, then runs a separate adversarial agent that red-teams the plan before returning it. Each persona is built from the writer's primary public corpus and argues from their actual positions - and they disagree with each other on purpose.

## Install

```bash
claude --plugin-dir ~/Projects/github.com/smykla-skalski/sai/claude/refactor-council/
```

## Usage

```
/refactor-council <path|@file|directory> [--no-scan] [--no-adversary] [--since 12.month] [--personas a,b,c]

/refactor-council src/billing/                         # Scan + full council + adversary on a module
/refactor-council @src/payments/charge.py              # Single file
/refactor-council diff --no-scan                       # Review the current git diff, skip scanning
/refactor-council src/legacy/ --personas feathers-legacy-reviewer,beck-tidy-first-reviewer,tornhill-hotspot-advisor --since 24.month
```

## The roster

| Persona | Lens |
|---|---|
| **Martin Fowler** | Refactoring catalog + code smells; small behavior-preserving steps; two hats; Rule of Three; Strangler Fig |
| **Robert C. Martin** | SOLID; Clean Architecture & the Dependency Rule; small functions; naming; frameworks/DB as details |
| **Michael Feathers** | Legacy = code without tests; seams; characterization tests; Sprout/Wrap; get-it-under-test-first |
| **Kent Beck** | Structural vs behavioral changes; tidyings; coupling/optionality economics; baby steps |
| **Sandi Metz** | Duplication over the wrong abstraction; flocking rules; squint test; depend on stable things |
| **John Ousterhout** | Deep modules; complexity is the enemy; anti-over-decomposition; comments are load-bearing |
| **Adam Tornhill** | Behavioral code analysis; hotspots (complexity x churn); change coupling; *where* to refactor |

After synthesis a separate **adversary** agent stress-tests the plan: behavior preservation, safety net, wrong-abstraction risk, over-decomposition, cold-code/ROI, scope creep, sequencing, and latent correctness/security/perf the personas could not see. It returns SHIP / SHIP WITH CHANGES / HOLD.

## Built-in disagreements

The value is the combination of opposed lenses:

- **Uncle Bob vs Ousterhout** - small functions and "comments are failures" vs deep modules and load-bearing comments (the most documented split in the field).
- **Uncle Bob's DRY reflex vs Metz** - "extract this duplication now" vs "the wrong abstraction is worse than duplication."
- **Everyone's "what to refactor" vs Tornhill's "where"** - Tornhill re-ranks the findings by what the git history shows is actually touched.

## Scan scripts

Two heuristic, deterministic scanners run before the personas review:

- `scripts/smell_scan.py` - language-agnostic smell scan (long files/functions, long parameter lists, deep nesting, debt markers). NDJSON or `--human`.
- `scripts/hotspots.py` - git-history hotspots (churn x size) and change coupling. NDJSON or `--human`.

Both emit NDJSON on stdout and a human table on stderr with `--human`.

## Output

One integrated review: convergence across opposed lenses, named disagreements you must decide, per-persona top-3 in each voice, safety-net status, a sequenced smallest-first refactoring plan (characterization-tests-first when untested), an explicit "do NOT refactor" list, and the adversary's verdict and the risks it caught.

## Privacy

Persona dossiers under `skills/refactor-council/references/` are private review aids derived from each thinker's public writing. Do not republish wholesale. When a review leaves the team, strip the persona framing and restate the argument in your own voice.

## Scope

This is a *refactoring* council: it preserves behavior by definition, so it does not by itself verify correctness, security, or performance. The adversary partially covers those gaps; for a full audit use `staff-code-review`, a language reviewer, or `council all`.

## License

MIT
