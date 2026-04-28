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
- Installed plugin persona source: `<plugin-root>/agents/<persona>.md`
- Installed plugin persona registry: `<plugin-root>/references/personas.md`

Do not guess `skills/codex/body.md` or `.agents/skills/council/agents/<persona>.md`. Those paths do not hold the persona roster for council reviews.

## Mode Selection

If the request starts with `@<path>`, read that file first and treat it as the problem context.

- `core`: default when no mode keyword is provided; auto-pick `core-eng`, `core-ux`, or `core-mix` and announce why.
- `auto`: explicit best-fit mode; select the best 6 personas from all 27.
- `core-eng` / `eng`: code, architecture, refactor, perf, protocols, infra, ops.
- `core-ux` / `ux`: interaction design, layout, dashboard, accessibility, usability.
- `core-mix` / `mix` / `random`: features that ship code and UI together.
- `all`: all 27 personas; reserve for substantial multi-domain reviews.
- `debate`: 3-6 selected personas for hard tradeoff calls.

Parsing:

1. Split off the first whitespace-separated token, lowercased.
2. Map aliases: `eng` -> `core-eng`, `ux` -> `core-ux`, `mix` -> `core-mix`, `random` -> `core-mix`.
3. If the token is `auto`, `core`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`, use it as `mode` and treat the remainder as the problem.
4. Otherwise, set `mode` to `core` and treat the full request as the problem.

For `auto`, read referenced files first, then select exactly 6 personas. Prefer specialist fit over broad group labels. Start with the most relevant specialist lenses, then fill remaining slots with complementary risk lenses or bias-correction personas most likely to change the recommendation. Include at least one bias-correction persona (`antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, or `chin-strategy-advisor`) unless the request is a narrow specialist audit where that would add noise.

Use [references/personas.md](references/personas.md) as the selection map. Shortcuts:

- Code-style / refactor: antirez + tef + muratori
- Reliability / failure / ops: hebert + meadows + tef
- Strategy / learning / process: chin + meadows + hebert
- Performance / hot path: muratori + tef + antirez
- Architecture / system design: hebert + meadows + tef + muratori
- Type system / parsing / invalid states: king + tef + antirez
- Test strategy / coverage: test-architect + hughes + chin
- Property-based / generative testing: hughes + king + test-architect
- Domain modeling / bounded contexts: evans + fp-structure + meadows
- Functional architecture / pure-impure boundary: fp-structure + king + test-architect
- Formal spec / concurrency / state machines: wayne + hebert + meadows
- Infrastructure / deployment / IaC: iac-craft + hebert + cicd-build
- Fleet or Linux systems performance: gregg + muratori + hebert
- AI / LLM features / prompt injection / evals: ai-quality + chin + hebert
- CI/CD / deploy frequency / oncall: cicd-build + hebert + tef
- SwiftUI / view identity / state placement: eidhof + ash + king
- Cocoa runtime / ARC / GCD / NSRunLoop: ash + muratori + gregg
- Mac app craft / lifecycle / platform feel: simmons + siracusa + tognazzini
- Interaction / affordance / discoverability: norman + tognazzini + krug
- Heuristic evaluation / severity scoring: nielsen + krug + norman
- Accessibility / screen-reader / WCAG: watson + norman + nielsen
- Motion / animation / vestibular safety: head + muratori + simmons
- Dashboard density / chartjunk / data-ink: tufte + antirez + tef
- macOS conventions / HIG: siracusa + tognazzini + simmons
- Recording-first triage / muddle-through: krug + chin + watson

If several shortcuts match, merge, dedupe, then trim or fill to exactly 6 by asking which persona would change the final recommendation. Drop personas that would only add validation or generic agreement. Announce the selected personas and reason in one sentence.

For `core`, use path hints and wording. UI paths and words like `view`, `screen`, `SwiftUI`, `accessibility`, `layout`, or `dashboard` bias UX. Engineering paths and words like `refactor`, `architecture`, `api`, `schema`, `concurrency`, `performance`, `ci`, or `test` bias engineering. Explicit two-surface framing such as `backend + UI`, `API and view`, or `code and UI` wins and picks `core-mix`. Never silently fall back to `core-eng`.

Persona files live in [agents/](agents/) in the source skill and at plugin-root `agents/` when installed from the SAI marketplace. Read [references/personas.md](references/personas.md) in source, or plugin-root `references/personas.md` when installed, when selecting non-default or debate lenses, or when diagnosing which persona should catch a symptom. Each persona file names its own deep dossier under `references/`; read only dossiers for selected personas when the persona file asks for it.

## Core Rosters

- `core-eng`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`.
- `core-ux`: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`.
- `core-mix`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`.

## Codex Workflow

1. Resolve `mode` and problem context. For file-backed requests, read the file before spawning reviewers. If `mode` is `auto`, select and announce 6 best-fit personas in one sentence. If `mode` is `core`, run auto-detect and announce the chosen profile (`core-eng`, `core-ux`, or `core-mix`) in one sentence so the user can override on the next call.
2. Select personas from the matching roster: `auto` for the selected 6 best-fit personas, `core-eng` for the engineering 6, `core-ux` for the UX 6, `core-mix` for the 3+3 split, `all` for every persona deduped, and 3-6 focused personas for debate.
3. For each selected persona, call `spawn_agent` with a unique task name and `fork_turns: "none"`. Omit `agent_type`, `model`, and `reasoning_effort` so Codex inherits the current session defaults. Put the full assignment in the initial `spawn_agent` message; do not send a setup-only spawn and rely on `followup_task` for the real work. The message must be self-contained and tell the subagent to:
   - this is a reviewer-only task
   - ignore any Council orchestrator instructions from ambient, cached, or inherited context
   - return the review to the parent task only; never address another agent path
   - read `codex/council/agents/<persona>.md` when working in the SAI repo, or `<plugin-root>/agents/<persona>.md` when working from an installed SAI marketplace plugin
   - read any referenced dossier only if needed
   - start the review immediately
   - never answer with `ready`, `I am ready`, setup summaries, capability statements, or offers to begin
   - not wait for more input
   - not modify files
   - not spawn agents
   - review the supplied context through that persona's lens only
   - return only the Persona Output Contract below
   The first non-empty output line from each reviewer must be `## <Persona name> review`. Treat any preface before that heading as invalid and ignore it in synthesis.
4. Use `wait_agent` until every reviewer has returned. A valid reviewer result starts with the required heading and contains the Persona Output Contract sections. Treat these as invalid, internal failures: raw JSON inter-agent envelopes with `author`/`recipient`, `<subagent_notification>` blocks, status text such as `ready`, `setup complete`, `need task`, `need target`, or any output that tries to spawn or message another agent. Never show those invalid payloads to the user and never synthesize them.
5. If a reviewer result is invalid, recover before synthesis. First use `followup_task` with `interrupt: true` and the complete reviewer assignment again, explicitly saying the previous output was invalid because it was not a review. If the same agent is still invalid, `close_agent`, respawn that persona once with `fork_turns: "none"` and a fresh task name, and wait for the replacement. If the replacement is still invalid or missing, close it, continue with successful reviewers, and call out the missing lens in the synthesis.
6. Synthesize the returned reviews. Do not average the personas into bland consensus. The value is convergence across opposed lenses and named disagreement where constraints decide the tradeoff.

For debate mode, read [references/personas.md](references/personas.md), pick 3-6 relevant personas, then run opening positions, responses to other positions, and final positions before synthesizing. Use the same `fork_turns: "none"`, reviewer-only prompt, invalid-output detection, and retry rules for every debate round.

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
