---
name: council
description: Run council reviews with sourced engineering, UX, reliability, performance, AI, and strategy persona lenses. Use when the user asks for council review, multi-persona critique, debate, design review, code review, architecture feedback, UX review, or tradeoff analysis.
---

# Council of Experts

Run an engineering council review from Codex. Use generic Codex subagents, not Claude named subagents. Each persona is loaded from a Markdown file under `agents/`, reviews through one sourced lens, and returns material for one integrated synthesis.

## Path Sanity

If you need to inspect or debug this skill from repo files, keep the skill-name segment in the path:

- SAI Codex skill: `codex/council/SKILL.md`
- SAI persona source: `codex/council/agents/<persona>.md`
- SAI persona registry: `codex/council/references/personas.md`

Do not guess `skills/codex/body.md` or `.agents/skills/council/agents/<persona>.md`. Those paths do not hold the persona roster for council reviews.

## Mode Selection

If the request starts with `@<path>`, read that file first and treat it as the problem context.

- `core`: default; auto-pick `core-eng`, `core-ux`, or `core-mix` and announce why.
- `core-eng` / `eng`: code, architecture, refactor, perf, protocols, infra, ops.
- `core-ux` / `ux`: interaction design, layout, dashboard, accessibility, usability.
- `core-mix` / `mix` / `random`: features that ship code and UI together.
- `all`: all 27 personas; reserve for substantial multi-domain reviews.
- `debate`: 3-6 selected personas for hard tradeoff calls.

For bare `core`, use path hints and wording. UI paths and words like `view`, `screen`, `SwiftUI`, `accessibility`, `layout`, or `dashboard` bias UX. Engineering paths and words like `refactor`, `architecture`, `api`, `schema`, `concurrency`, `performance`, `ci`, or `test` bias engineering. Explicit two-surface framing such as `backend + UI`, `API and view`, or `code and UI` wins and picks `core-mix`. Never silently fall back to `core-eng`.

Persona files live in [agents/](agents/). Read [references/personas.md](references/personas.md) when selecting non-default or debate lenses, or when diagnosing which persona should catch a symptom. Each persona file names its own deep dossier under `references/`; read only dossiers for selected personas when the persona file asks for it.

## Core Rosters

- `core-eng`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`.
- `core-ux`: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`.
- `core-mix`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`.

## Codex Workflow

1. Resolve `mode` and problem context. For file-backed requests, read the file before spawning reviewers. If `mode` is bare `core`, run auto-detect and announce the chosen profile (`core-eng`, `core-ux`, or `core-mix`) in one sentence so the user can override on the next call.
2. Select personas from the matching roster: `core-eng` for the engineering 6, `core-ux` for the UX 6, `core-mix` for the 3+3 split, `all` for every persona deduped, and 3-6 focused personas for debate.
3. For each selected persona, call `spawn_agent` with `agent_type: default` and a unique task name. Put the full assignment in the initial `spawn_agent` message; do not send a setup-only spawn and rely on `followup_task` for the real work. The message must be self-contained and tell the subagent to:
   - read `codex/council/agents/<persona>.md` when working in the SAI repo, or `agents/<persona>.md` when working from an installed skill copy
   - read any referenced dossier only if needed
   - perform the review immediately
   - not answer with `ready`
   - not wait for more input
   - not modify files
   - not spawn agents
   - review the supplied context through that persona's lens only
   - return only the Persona Output Contract below
4. Use `wait_agent` until every reviewer has returned. If one reviewer fails, continue with the successful reviewers and call out the missing lens in the synthesis.
5. Synthesize the returned reviews. Do not average the personas into bland consensus. The value is convergence across opposed lenses and named disagreement where constraints decide the tradeoff.

For debate mode, read [references/personas.md](references/personas.md), pick 3-6 relevant personas, then run opening positions, responses to other positions, and final positions before synthesizing.

## Persona Output Contract

Ask each reviewer to return:

```markdown
## <Persona name> review

### What I see
<2-4 sentences naming what the proposal/code is, in their voice>

### What concerns me
<3-6 bullets grounded in that persona's philosophy and the concrete context>

### What I'd ask before approving
<3-5 questions from their canonical question list>

### Concrete next move
<1 sentence: the single change they would push for>

### Where I'd be wrong
<1-2 sentences: their honest blind spot>
```

The "Where I'd be wrong" section is required. Without it the personas drift toward dogma.

## Synthesis Shape

Return one integrated review:

```markdown
# Council review: <topic>

## Convergence (high-confidence signals)

<2-5 bullets. Format: `- [finding] - [persona1, persona2, persona3]`.>

## Disagreement (real tradeoffs the user must decide)

<2-4 bullets. Format: `- [axis] - [persona A] argues X / [persona B] argues Y. Decision is yours because <constraint>.`>

## Per-persona top-3

<For each persona that returned, three concrete bullets in that persona's voice.>

## What to do next

<3-7 numbered concrete actions, smallest first, tied back to personas.>

## What we did not address

<1-3 bullets naming gaps the council does not cover for this problem.>
```

## Privacy / Scope

Persona dossiers in [references/](references/) are private review aids derived from public writing. Do not republish dossiers wholesale. If a council review leaves the team, strip persona framing and restate the arguments in your own voice.
