# Refactor-council persona registry

Canonical registry for the refactoring council. Each persona is a self-contained subagent in [../../../agents/](../../../agents/) with a full dossier in this `references/` directory. Spawn each via the Agent tool with `subagent_type` matching the registered name.

## The seven reviewers

| Persona (subagent) | Person | Lens | Dossier |
|---|---|---|---|
| `fowler-refactoring-reviewer` | Martin Fowler | Refactoring catalog + code smells; small behavior-preserving steps; two hats; make-the-change-easy; Rule of Three; Strangler Fig | [fowler-deep.md](fowler-deep.md) |
| `martin-clean-architecture-reviewer` | Robert C. Martin (Uncle Bob) | SOLID; Clean Architecture & the Dependency Rule; small functions; meaningful names; frameworks/DB as details | [martin-deep.md](martin-deep.md) |
| `feathers-legacy-reviewer` | Michael Feathers | Legacy code = code without tests; seams; characterization/golden-master tests; Sprout/Wrap; dependency-breaking; get-it-under-test-first | [feathers-deep.md](feathers-deep.md) |
| `beck-tidy-first-reviewer` | Kent Beck | Tidy First?; structural vs behavioral changes; tidyings; coupling/optionality economics; baby steps | [beck-deep.md](beck-deep.md) |
| `metz-abstraction-reviewer` | Sandi Metz | Duplication over the wrong abstraction; flocking rules; squint test; Shameless Green; depend on stable things | [metz-deep.md](metz-deep.md) |
| `ousterhout-deep-module-reviewer` | John Ousterhout | Deep modules; complexity is the enemy; anti-over-decomposition; comments are load-bearing; strategic vs tactical | [ousterhout-deep.md](ousterhout-deep.md) |
| `tornhill-hotspot-advisor` | Adam Tornhill | Behavioral code analysis; hotspots (complexity x churn); change/temporal coupling; *where* to refactor | [tornhill-deep.md](tornhill-deep.md) |

## The adversary (spawned after synthesis)

| Subagent | Role | File |
|---|---|---|
| `refactor-adversary` | Red-teams the synthesized findings + plan: behavior preservation, safety net, wrong-abstraction, over-decomposition, cold-code/ROI, scope creep, sequencing, latent correctness/security/perf. Returns SHIP / SHIP WITH CHANGES / HOLD. | [../../../agents/refactor-adversary.md](../../../agents/refactor-adversary.md) |

## What each persona is good at catching

- **Smell present, named, with the cure** -> Fowler.
- **Principle violation (SRP/OCP/DIP), boundary leak, framework bleeding into business rules** -> Uncle Bob.
- **Untested code about to be changed; no seam; behavior not pinned** -> Feathers.
- **Structure + behavior mixed in one commit; coupling that makes the next change expensive; is-this-tidy-worth-it** -> Beck.
- **Premature/wrong abstraction; parameters + conditionals accreting on a near-fit; DRY applied too early** -> Metz.
- **Over-decomposition into shallow entangled modules; missing load-bearing comments; the proposed refactor would *add* complexity** -> Ousterhout.
- **Effort about to be spent on cold code; the real hotspot is elsewhere; hidden change-coupling** -> Tornhill.

## Built-in disagreements (the value is the combination)

- **Uncle Bob vs Ousterhout** — small functions & "comments are failures" vs deep modules & load-bearing comments. The sharpest, most documented split.
- **Uncle Bob's DRY reflex vs Metz** — "extract this duplication now" vs "the wrong abstraction is worse than duplication."
- **Fowler/Uncle Bob's decomposition vs Ousterhout/Muratori** — extraction improves naming vs extraction adds indirection (and, for Muratori, runtime cost).
- **Everyone's "what to refactor" vs Tornhill's "where"** — Tornhill re-ranks the others' findings by what the git history says is actually touched.
- **Beck/Metz/Feathers vs an eager rewriter** — baby steps, duplication-until-earned, and seams-first all resist big-bang change.

## What no persona is good at catching

This council is a *refactoring* council: every persona except Tornhill reasons about preserving behavior, so none of them independently checks whether the **current behavior is correct, secure, or concurrency-safe**, and none does deep **performance** analysis (Muratori, who would, lives in the general `council` plugin, not here). The `refactor-adversary` partially covers these gaps as a final gate. For full correctness/security/perf review, use a different tool (e.g. `staff-code-review`, `go-code-review`, or `council all`).

## Adding a persona

1. Add a dossier in this directory matching the structure of the existing seven (identity & canon with sources, core philosophy with verbatim quotes, core lens, review technique, common questions, honest skew).
2. Add a subagent file in [../../../agents/](../../../agents/) following an existing persona as template (frontmatter, voice rules, core lens with sourced quotes, the required output format, debate scaffolding, honest skew).
3. Add a row to the table above and to the symptom map.
4. Add it to the spawn list in [../SKILL.md](../SKILL.md).
