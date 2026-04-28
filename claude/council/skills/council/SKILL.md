---
name: council
description: >-
  Use when the user asks for council review, multi-persona critique, debate, design
  review, code review, architecture feedback, UX review, or tradeoff analysis. Bare
  invocations use `core` profile auto-detect; explicit `auto` selects the best-fit
  6 personas from the sourced 27-persona engineering and UX roster. Users can still
  pin `core`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`.
argument-hint: "auto|core|core-eng|core-ux|core-mix|all|debate <problem-description|@file>"
allowed-tools: Agent, AskUserQuestion, Read, Grep, Glob, Bash, Write, Edit
user-invocable: true
---

# Council of Experts

Summon engineering persona agents to review code, debate a plan, or advise on strategy. Each persona is built from the writer's primary public corpus (essays, talks, books). Personas argue from their actual positions, with their actual phrases and evidence. They will disagree with each other.

## Why this exists

Generic AI review drifts to safe, hedged, template-shaped output. Opinionated persona agents pull responses out of that middle. Each persona is sharp in one direction and blind in others - the council's value is the *combination* of their disagreements.

## Mode dispatch

| Mode     | Keyword  | Agents Summoned                  | Cost & purpose |
|----------|----------|----------------------------------|----------------|
| **Core** | `core` or no keyword | 6 personas, profile auto-picked from problem text (eng / ux / mix) | Default compatibility preset. ~6 persona calls + 1 synthesis. Profile is selected by content heuristics; user can pin one with `core-eng`, `core-ux`, or `core-mix`. |
| **Auto** | `auto` | 6 best-fit personas selected from the full roster | Explicit best-fit mode when the user has not already chosen an engineering/UX group. Selects by problem evidence, not broad preset. |
| **Core (engineering)** | `core-eng` (alias `eng`) | 6 engineering bias-correction personas | Pin when the problem is code, architecture, refactor, perf, protocol, infra, ops. |
| **Core (UI/UX)** | `core-ux` (alias `ux`) | 6 UI/UX bias-correction personas | Pin when the problem is interaction design, layout, dashboard, accessibility, usability test, visual density. |
| **Core (mixed)** | `core-mix` (alias `mix`, `random`) | 3 engineering + 3 UX personas | Pin when the surface is a feature shipping both code and UI - the mix forces both lenses in one pass. |
| **All**  | `all`    | All 27 personas (6 engineering core + 6 UX core overlap + 10 extended domain + 11 extended UX/platform) | ~27 persona calls + 1 wider-context synthesis (~4.5x core cost). Use when the problem touches multiple domains (type design, deployment, observability, perf at scale, UX, accessibility, motion, macOS-platform craft) in one review and you want every lens. Reserve for substantial designs. |
| **Debate** | `debate` | 3-6 personas you select for the topic | ~3-6 calls per round x 3 rounds + 1 synthesis. Multi-round - personas read each other's positions and respond. Use for hard tradeoff calls where disagreement is the point. |

### Parsing `$ARGUMENTS`

Apply this algorithm in order:

1. Split off the first whitespace-separated token, lowercased.
2. Map aliases: `eng` -> `core-eng`, `ux` -> `core-ux`, `mix` -> `core-mix`, `random` -> `core-mix`.
3. If that token is `auto`, `core`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`: set `mode` to that value and `problem` to the remainder of `$ARGUMENTS`.
4. Otherwise: set `mode` to `core` and `problem` to the full `$ARGUMENTS`.
5. If `problem` (after trimming) begins with `@`, treat the rest of that token as a file path and use `Read` on it - the file contents become the problem context. Any text after the `@<path>` token is appended as additional framing.
6. If `mode == auto`, run Auto persona selection. Tell the user which personas you picked and why in one compact sentence before spawning.
7. If `mode == core`, run Core profile auto-detect to resolve to one of `core-eng`, `core-ux`, or `core-mix`. Tell the user which profile you picked and why in one sentence before spawning, so they can override on the next call.

### Auto persona selection

Use this only for explicit `/council auto <problem>`. Do not ask the user to choose `eng`, `ux`, or `mix` unless the request is too ambiguous to review at all.

Select exactly 6 personas from the full roster:

- Read the problem and referenced files first. File contents beat filenames; explicit user framing beats keyword counts.
- Use the canonical symptom map in [references/personas.md](references/personas.md) when the right lens is not obvious from the quick-reference roster.
- Prefer specialists over broad presets. Example: SwiftUI state placement should select `eidhof-swiftui-reviewer`, `ash-cocoa-runtime-reviewer`, and `king-type-reviewer` before generic UX personas, then fill the remaining slots with complementary lenses. CI/oncall rollout risk should select `cicd-build-advisor`, `hebert-resilience-reviewer`, and `tef-deletability-reviewer`, then add the three next most useful risk lenses.
- If fewer than 6 personas are obviously relevant, fill the remaining slots with complementary risk lenses or bias-correction personas most likely to change the recommendation.
- If more than 6 personas seem relevant, do not escalate to `all` unless the user asked for breadth. Pick the 6 most likely to change the recommendation and mention the omitted coverage in synthesis.
- Include at least one bias-correction persona (`antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, or `watson-a11y-reviewer`) unless the request is a narrow specialist audit.
- Avoid duplicate lenses. If two personas would make the same objection, keep the one with the sharper domain fit.
- Announce the selection before spawning: `Auto-selected <persona list> because <specific evidence>.`

Useful auto shortcuts:

- Code-style / refactor: antirez + tef + muratori
- Reliability / failure / ops: hebert + meadows + tef
- Strategy / learning / process: chin + meadows + hebert
- Performance / hot path (single-process): muratori + tef + antirez
- Architecture / system design: hebert + meadows + tef + muratori
- Type system / data validation / parsing: king + tef + antirez
- Test design / coverage strategy: test-architect + hughes + chin
- Property-based / generative testing: hughes + king + test-architect
- Domain modeling / bounded contexts: evans + fp-structure + meadows
- Functional architecture / pure-impure boundary: fp-structure + king + test-architect
- Formal spec / concurrency / state machines: wayne + hebert + meadows
- Infrastructure / deployment / IaC: iac-craft + hebert + cicd-build
- Systems performance at scale (fleet / Linux / JVM): gregg + muratori + hebert
- AI / LLM features / prompt design / evals: ai-quality + chin + hebert
- CI/CD / deploy frequency / oncall: cicd-build + hebert + tef
- SwiftUI / view identity / state placement: eidhof + ash + king
- Cocoa runtime / ARC / GCD / NSRunLoop: ash + muratori + gregg
- macOS app craft / lifecycle / "feels like a Mac app": simmons + siracusa + tognazzini
- Interaction design / affordances / discoverability: norman + tognazzini + krug
- Heuristic evaluation / severity scoring: nielsen + krug + norman
- Accessibility / screen-reader / WCAG: watson + norman + nielsen
- Motion / animation / vestibular safety: head + muratori + simmons
- Dashboard density / chartjunk / data-ink: tufte + antirez + tef
- macOS platform conventions / HIG: siracusa + tognazzini + simmons
- Recording-first triage / muddle-through: krug + chin + watson

If several shortcuts match, merge them, dedupe personas, and trim or fill to exactly 6 by asking: "which persona would change the final recommendation?"

### Core profile auto-detect

Use this only when the user explicitly invokes `core`.

Score the problem text (file contents + framing) against two cue sets:

**UX cues:** `ui`, `ux`, `view`, `screen`, `sidebar`, `toolbar`, `button`, `menu`, `window`, `sheet`, `tab`, `dashboard`, `chart`, `layout`, `typography`, `color`, `contrast`, `animation`, `motion`, `transition`, `easing`, `swiftui`, `appkit`, `cocoa`, `accessibility`, `a11y`, `voiceover`, `screen reader`, `wcag`, `aria`, `focus`, `keyboard navigation`, `affordance`, `usability`, `recording`, `figma`, `mockup`, `interaction`, `tooltip`, `hover`, `drag`, `gesture`.

**Engineering cues:** `refactor`, `architecture`, `module`, `crate`, `package`, `function`, `class`, `struct`, `actor`, `protocol` (in code-design sense), `api`, `endpoint`, `schema`, `migration`, `database`, `sql`, `query`, `cache`, `lock`, `thread`, `concurrency`, `async`, `await`, `goroutine`, `tokio`, `performance` (in CPU/memory/throughput sense), `latency` (system), `throughput`, `pipeline`, `ci`, `cd`, `deploy`, `kubernetes`, `terraform`, `helm`, `oncall`, `incident`, `dependency`, `lint`, `test` (unit/integration), `mock`, `fuzz`, `tla+`.

Apply file path hints first - they're the strongest signal. `*.swift`, `*.css`, `*.html`, and UI source paths (e.g. `apps/<name>/Sources/...`) bias toward UX; `*.rs`, `*.go`, `Cargo.toml`, `Dockerfile`, `*.tf` bias toward engineering. Treat each path hint as adding 2 to the matching side's score so it can outweigh stray cue keywords in framing prose.

Then resolve in this order - check each rule in turn and stop on the first match:

1. **Two-surface framing wins.** If the problem text explicitly names two halves of the work - phrases like `both halves`, `backend + UI`, `code and UI`, `crate and SwiftUI`, `API and view`, `frontend and backend`, `server and client` - pick `core-mix`. The user is telling you the surface is dual; respect that intent over keyword arithmetic.
2. **Both halves have real signal.** If UX score >= 2 AND engineering score >= 2 (after path hints), pick `core-mix`. Two cues on each side means the problem genuinely touches both lenses; mix forces both into the review without paying for `all`.
3. **Single side dominates.** If UX score > engineering score, pick `core-ux`. If engineering score > UX score, pick `core-eng`.
4. **No signal at all.** If both scores are 0, pick `core-mix` and tell the user the auto-detect found nothing concrete so it's hedging.

Why this order: the explicit framing rule (#1) catches the case where the user has already done the classification work in their prose - silently overriding that with keyword counts is hostile. The threshold rule (#2) catches the case where prose doesn't say "both halves" but the cues do. The strict-comparison rule (#3) only fires when one side is clearly thin or absent. The all-zero fallback (#4) is the last resort and must be transparent so the user knows nothing matched.

Never silently fall back to `core-eng` - that hides the choice from the user. Bare invocations use `core` profile auto-detect; explicit `auto` uses the 6-person best-fit roster.

## Roster

Located in [agents/](../../agents/). Each persona is a self-contained subagent with its own system prompt, voice, philosophy, and review questions. The canonical registry (with full person/lens/dossier mapping and the "what each persona is good at catching" symptom map) lives in [references/personas.md](references/personas.md); the tables below are a quick-reference convenience for selection.

### Core (engineering) (6) - compatibility preset for code/architecture

| Persona | Lens |
|---------|------|
| [antirez-simplicity-reviewer](../../agents/antirez-simplicity-reviewer.md) | Code as artifact, design sacrifices, comments-pro, lazy-evaluation, hack value |
| [tef-deletability-reviewer](../../agents/tef-deletability-reviewer.md) | Easy to delete > easy to extend, anti-naive-DRY, protocol over topology |
| [muratori-perf-reviewer](../../agents/muratori-perf-reviewer.md) | Semantic compression, performance from day one, anti-Clean-Code-orthodoxy |
| [hebert-resilience-reviewer](../../agents/hebert-resilience-reviewer.md) | Operability, supervision trees, complexity has to live somewhere, sociotechnical resilience |
| [meadows-systems-advisor](../../agents/meadows-systems-advisor.md) | 12 leverage points, stocks/flows/loops, intervene at the right level |
| [chin-strategy-advisor](../../agents/chin-strategy-advisor.md) | Tacit knowledge, NDM, anti-framework-cult, close the loop |

### Core (UI/UX) (6) - compatibility preset for interaction/layout/a11y

| Persona | Lens |
|---------|------|
| [norman-affordance-reviewer](../../agents/norman-affordance-reviewer.md) | Affordances vs signifiers, mappings, mental models, seven stages of action, error mode design |
| [nielsen-heuristics-reviewer](../../agents/nielsen-heuristics-reviewer.md) | 10 Usability Heuristics, severity rating 0-4, discount usability, 5-users finding |
| [krug-usability-reviewer](../../agents/krug-usability-reviewer.md) | Don't make me think, muddling through, three laws, trunk test, recording-as-usability-test |
| [watson-a11y-reviewer](../../agents/watson-a11y-reviewer.md) | Lived screen-reader experience, semantic HTML over ARIA, accessible-name computation, focus order |
| [tognazzini-fpid-reviewer](../../agents/tognazzini-fpid-reviewer.md) | First Principles of Interaction Design, Fitts's law, anticipation, latency, autonomy, protect user's work |
| [tufte-density-reviewer](../../agents/tufte-density-reviewer.md) | Data-ink ratio, chartjunk, sparklines, small multiples, "above all else show the data" |

### Core (mixed) (6) - 3 engineering + 3 UX compatibility preset

| Persona | Lens |
|---------|------|
| [antirez-simplicity-reviewer](../../agents/antirez-simplicity-reviewer.md) | Engineering simplicity / design sacrifices |
| [tef-deletability-reviewer](../../agents/tef-deletability-reviewer.md) | Deletability / anti-DRY / protocol over topology |
| [hebert-resilience-reviewer](../../agents/hebert-resilience-reviewer.md) | Operability / failure modes / sociotechnical resilience |
| [norman-affordance-reviewer](../../agents/norman-affordance-reviewer.md) | Affordances / mental models / error mode design |
| [nielsen-heuristics-reviewer](../../agents/nielsen-heuristics-reviewer.md) | 10 Usability Heuristics / severity rating |
| [watson-a11y-reviewer](../../agents/watson-a11y-reviewer.md) | Lived a11y / semantic structure / focus order |

The mixed core is opinionated about the split. It picks the three engineering personas that most reliably catch product-level over-engineering (antirez, tef, hebert) and the three UX personas that most reliably catch product-level usability and a11y debt (norman, nielsen, watson). For deeper UI surface review use `core-ux`; for deeper code review use `core-eng`; for both at full strength use `all`.

### Extended Domain (10) - domain-specific lenses for `all` mode and `debate` selection

| Persona | Lens |
|---------|------|
| [king-type-reviewer](../../agents/king-type-reviewer.md) | Parse-don't-validate, totality, make illegal states unrepresentable, types as axioms |
| [hughes-pbt-advisor](../../agents/hughes-pbt-advisor.md) | Property-based testing, generators not examples, shrinking is the value, stateful PBT |
| [evans-ddd-reviewer](../../agents/evans-ddd-reviewer.md) | Ubiquitous language, bounded contexts, strategic design, distill the core domain |
| [fp-structure-reviewer](../../agents/fp-structure-reviewer.md) | Impureim sandwich, dependency rejection, railway-oriented programming, code that fits in your head |
| [wayne-spec-advisor](../../agents/wayne-spec-advisor.md) | Formal methods, TLA+, model-check the protocol, the spec is the design |
| [iac-craft-reviewer](../../agents/iac-craft-reviewer.md) | Immutable infrastructure, drift detection, pipeline IS the change-management process, phoenix not snowflake |
| [test-architect](../../agents/test-architect.md) | Functional core/imperative shell, values not objects, boundaries, tests as design pressure |
| [gregg-perf-reviewer](../../agents/gregg-perf-reviewer.md) | USE method, methodology over tools, profile in production, off-CPU and BPF observability |
| [ai-quality-advisor](../../agents/ai-quality-advisor.md) | Prompt injection, eval-driven LLM development, lethal trifecta, sandboxed tool use |
| [cicd-build-advisor](../../agents/cicd-build-advisor.md) | Test in production, observability over monitoring, deploy small deploy often, oncall as cultural force |

### Extended UX/Platform (11) - UI craft, accessibility, motion, macOS conventions, dashboard density

| Persona | Lens |
|---------|------|
| [eidhof-swiftui-reviewer](../../agents/eidhof-swiftui-reviewer.md) | SwiftUI declarative discipline, view identity, state ownership, environment over singletons, value semantics |
| [ash-cocoa-runtime-reviewer](../../agents/ash-cocoa-runtime-reviewer.md) | Cocoa runtime mechanics, ARC retain/release, GCD edge cases, NSRunLoop, blocks, Swift bridging cost |
| [simmons-mac-craft-reviewer](../../agents/simmons-mac-craft-reviewer.md) | Mac app craft, "feels like a real Mac app", lifecycle finesse, multi-window, sandbox vs HIG, ship-it-small |
| [norman-affordance-reviewer](../../agents/norman-affordance-reviewer.md) | Affordances vs signifiers, mappings, mental models, seven stages of action, error mode design |
| [tognazzini-fpid-reviewer](../../agents/tognazzini-fpid-reviewer.md) | First Principles of Interaction Design, Fitts's law, anticipation, latency, autonomy, protect user's work |
| [krug-usability-reviewer](../../agents/krug-usability-reviewer.md) | Don't make me think, muddling through, three laws, trunk test, recording-as-usability-test, three-users-a-month |
| [nielsen-heuristics-reviewer](../../agents/nielsen-heuristics-reviewer.md) | 10 Usability Heuristics, severity rating 0-4, discount usability, 5-users finding, thinking-aloud protocol |
| [watson-a11y-reviewer](../../agents/watson-a11y-reviewer.md) | Lived screen-reader experience, semantic HTML over ARIA, accessible-name computation, focus order, four rules of ARIA |
| [head-motion-reviewer](../../agents/head-motion-reviewer.md) | Motion has purpose, easing curves, timing budgets 200-500ms, vestibular safety, prefers-reduced-motion |
| [siracusa-mac-critic](../../agents/siracusa-mac-critic.md) | Mac platform critique, AppKit/Cocoa appreciation, backwards compatibility, "this is not how a Mac app does X" |
| [tufte-density-reviewer](../../agents/tufte-density-reviewer.md) | Data-ink ratio, chartjunk, sparklines, small multiples, "above all else show the data", lie factor |

## Workflow

### Auto / Core / All mode

1. **Resolve `mode` and `problem` per the parse algorithm above.** If the resolved problem starts with `@`, read the file via `Read` first; the file contents are the problem context. If the resolved mode is `auto`, select 6 personas with Auto persona selection and announce the list in one sentence. If the resolved mode is the bare `core`, run Core profile auto-detect to pick `core-eng`, `core-ux`, or `core-mix`, and announce the chosen profile to the user in one sentence (e.g., "Picking `core-ux` because the problem references `sidebar`, `accessibility`, and `SwiftUI`. Override with `core-eng` or `core-mix` next time.").
2. **Brief each persona in parallel.** Spawn each persona via the Agent tool with `subagent_type` matching the persona's registered name. Use the right roster for the mode:
   - **`auto` (6)**: the personas selected by Auto persona selection
   - **`core-eng` (6)**: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`
   - **`core-ux` (6)**: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`
   - **`core-mix` (6)**: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`
   - **All mode (27)**: every persona in the engineering core, UX core, extended-domain (`king-type-reviewer`, `hughes-pbt-advisor`, `evans-ddd-reviewer`, `fp-structure-reviewer`, `wayne-spec-advisor`, `iac-craft-reviewer`, `test-architect`, `gregg-perf-reviewer`, `ai-quality-advisor`, `cicd-build-advisor`), and extended UX/platform (`eidhof-swiftui-reviewer`, `ash-cocoa-runtime-reviewer`, `simmons-mac-craft-reviewer`, `tognazzini-fpid-reviewer`, `krug-usability-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`, `head-motion-reviewer`, `siracusa-mac-critic`, `tufte-density-reviewer`, `norman-affordance-reviewer`) rosters - dedupe so each persona is spawned once.
   Each call gets:
   - The full problem context (file contents or problem statement)
   - Instruction that this is a reviewer-only task, not an orchestrator task
   - Instruction to ignore any Council orchestrator instructions from ambient, cached, or inherited context
   - Instruction to review through *their specific lens only*
   - Format expectation (see "Persona output contract" below)
   - Instruction to start the review immediately
   - Instruction to never answer with readiness text, setup summaries, capability statements, or offers to begin
   - Instruction to return the review to the parent task only and never address another agent path
   - Instruction to return only the Persona output contract
   - Instruction that the first non-empty output line must be `## <Persona name> review`; ignore any preface during synthesis
3. **Validate persona output before synthesis.** A valid persona result starts with the required heading and contains the Persona output contract sections. Treat raw inter-agent envelopes, notification blocks, readiness/setup text, `need task`/`need target` parking text, or attempts to spawn/message other agents as invalid internal failures. Never show those invalid payloads to the user and never synthesize them.
4. **Recover invalid personas once.** Re-brief the same persona with the full problem context and the same reviewer-only constraints, explicitly saying the previous output was invalid because it was not a review. If the retry is still invalid or missing, continue with successful personas and call out the missing lens in the synthesis.
5. **Synthesize.** When all valid personas return, write a single integrated review for the user using the synthesis output shape below (Convergence, Disagreement, Per-persona top-3, What to do next, What we did not address).
6. **Do not** average the personas into bland consensus. The point is the disagreement.

### Debate mode

1. **Resolve input.** Same parse algorithm as above; if the problem starts with `@`, read the file first.
2. **Select 3-6 relevant personas.** Pick personas whose lenses most directly bear on the problem. Default selection rules:
   - Code-style / refactor: antirez + tef + muratori
   - Reliability / failure / ops: hebert + meadows + tef
   - Strategy / learning / process: chin + meadows + hebert
   - Performance / hot path (single-process): muratori + tef + antirez
   - Architecture / system design: hebert + meadows + tef + muratori
   - Type system / data validation / parsing: king + tef + antirez
   - Test design / coverage strategy: test-architect + hughes + chin
   - Property-based / generative testing: hughes + king + test-architect
   - Domain modeling / bounded contexts: evans + fp-structure + meadows
   - Functional architecture / pure-impure boundary: fp-structure + king + test-architect
   - Formal spec / concurrency / state machines: wayne + hebert + meadows
   - Infrastructure / deployment / IaC: iac-craft + hebert + cicd-build
   - Systems performance at scale (fleet / Linux / JVM): gregg + muratori + hebert
   - AI / LLM features / prompt design / evals: ai-quality + chin + hebert
   - CI/CD / deploy frequency / oncall: cicd-build + hebert + tef
   - SwiftUI / view identity / state placement: eidhof + ash + king
   - Cocoa runtime / ARC / GCD / NSRunLoop: ash + muratori + gregg
   - macOS app craft / lifecycle / "feels like a Mac app": simmons + siracusa + tognazzini
   - Interaction design / affordances / discoverability: norman + tognazzini + krug
   - Heuristic evaluation / severity scoring: nielsen + krug + norman
   - Accessibility / screen-reader / WCAG: watson + norman + nielsen
   - Motion / animation / vestibular safety: head + muratori + simmons
   - Dashboard density / chartjunk / data-ink: tufte + antirez + tef
   - macOS platform conventions / HIG: siracusa + tognazzini + simmons
   - Recording-first triage / muddle-through: krug + chin + watson
   - When in doubt, ask the user via AskUserQuestion which 3-6 to summon.
3. **Round 1 - opening positions.** Each selected persona gives their independent first read. Brief each Agent with the same immediate-output constraints from Auto / Core / All mode: start the review immediately, never return readiness/setup/capability text, and make the first non-empty line `## <Persona name> review`.
4. **Round 2 - responses.** Pass each persona's Round 1 output to the others. Each responds: where do they agree, where do they disagree with which named persona, what evidence shifts the picture.
5. **Round 3 - synthesis.** A short final pass per persona: what's their final position now that they've heard the others. Then you (the orchestrator) summarize: where the council converged, where it remained split, and the user-facing decision.
6. **Apply the same validation and retry rule to every debate round.** Invalid readiness text, parking text, notification envelopes, inter-agent messages, or attempts to orchestrate other agents are internal failures; re-brief once and never show invalid payloads to the user.

## Persona output contract

When briefing a persona, instruct them to return a structured response:

```
## <Persona name> review

### What I see
<2-4 sentences naming what the proposal/code is, in their voice>

### What concerns me
<3-6 bullets, each grounded in their actual philosophy, with the specific
phrase or concept from their canon they're invoking>

### What I'd ask before approving
<3-5 questions, drawn from their canonical question list>

### Concrete next move
<1 sentence: the single change they'd push for>

### Where I'd be wrong
<1-2 sentences: their honest blind spot - every persona must include this>
```

The "Where I'd be wrong" section is required. Without it the personas drift toward dogma. With it they stay honest to their own published nuance.

## Constraints on personas

When you brief a persona, include these constraints in the briefing:

- **Stay in character.** Use their phrases, their canon, their named questions. Don't drift to generic AI review voice.
- **Cite their own work** when invoking a concept ("as I wrote in *Leverage Points*…", "this is what I called *integration discontinuity*…").
- **Disagree with the others when honest.** No false consensus. If antirez praises duplication and tef praises duplication, that's convergence - say so. If muratori wants intrusive performance changes and hebert pushes back on premature optimization in a critical-path region, name the disagreement.
- **One- to two-page max per persona.** The synthesis is where the user gets value; persona output is the raw material.

## Privacy / scope

The persona dossiers in [references/](references/) are derived from each thinker's public writing for personal review use. They quote directly with citations to the original sources, often 200+ lines of verbatim quotation per persona.

Constraints:

- **Do not republish dossiers wholesale.** They are private review aids, not redistributable content.
- **Do not use the personas to misrepresent the writer's published positions to third parties.** A council review is a tool for *you* to think with - not a synthesised public statement attributable to the named thinker.
- **Keep persona output internal-facing.** If a council review's content leaves the team (issue comments, blog posts, public PR descriptions), strip the persona framing and re-state the underlying argument in your own voice.
- **Treat the dossiers as living source material, not finished work.** They drift as the writer publishes more; a quote from 2019 may have been refined or retracted since.

## Synthesis output shape

Use this shape when integrating persona returns. The point is to make the disagreement legible, not to flatten it.

```
# Council review: <topic>

## Convergence (high-confidence signals)

<2-5 bullets. Each bullet names the shared finding and lists the personas
who arrived at it independently. Format: `- [finding] — [persona1, persona2,
persona3]`. Convergence across opposed lenses is the strongest signal in the
review; surface it first.>

## Disagreement (real tradeoffs the user must decide)

<2-4 bullets. Each bullet names the axis of disagreement and the personas on
each side, with a one-line summary of each position. Format:
`- [axis] — [persona A] argues X / [persona B] argues Y. Decision is yours
because <constraint that breaks the tie>.`>

## Per-persona top-3

<For each persona that returned, three bullets in their voice. Quote phrases
from their dossier; do not paraphrase into AI-review tone. Name the concrete
file/line/decision they're objecting to. Keep each bullet under 30 words.>

### antirez
- ...
- ...
- ...

### tef
- ...

(repeat per persona)

## What to do next

<3-7 numbered concrete actions, smallest first, each tied back to which
persona(s) called for it. Separate "before merging this PR" from "before
shipping the next iteration" if both timescales are in play.>

## What we did not address

<1-3 bullets naming gaps the council does not cover for this problem
(see "What no persona is good at catching" in references/personas.md).
Explicit gaps prevent the user mistaking the review for full coverage.>
```

## Examples

<example>
Explicit auto review of a refactoring plan:
```
/council auto @docs/plans/refactor-auth-module.md
```
Auto selection reads the file, sees `refactor`, `module`, and code-shaped content, then picks the 6 personas most likely to change the recommendation and returns an integrated review using the synthesis shape above.
</example>

<example>
Compatibility core review of a refactoring plan (auto-detect picks `core-eng`):
```
/council core @docs/plans/refactor-auth-module.md
```
Core auto-detect sees `refactor`, `module`, code-shaped file path, picks `core-eng`, then spawns all 6 engineering core personas in parallel.
</example>

<example>
Pinned UX review of a sidebar redesign:
```
/council core-ux @apps/desktop-app/Sources/Sidebar.swift
```
Skips auto-detect, spawns the 6 UX core personas (norman, nielsen, krug, watson, tognazzini, tufte). Use `ux` as a shorter alias.
</example>

<example>
Mixed review of a feature touching code and UI:
```
/council mix @docs/plans/sessions-window-redesign.md
```
Resolves `mix` -> `core-mix`, spawns 3 engineering + 3 UX personas (antirez, tef, hebert, norman, nielsen, watson). Use this when the design has both backend and frontend implications and you want both lenses without paying for `all`.
</example>

<example>
Full coverage on a substantial design touching multiple lenses:
```
/council all @docs/plans/llm-feature-rollout.md
```
Spawns all 27 personas. Use when the design touches type design, deployment, observability, AI quality, perf at scale, UX, accessibility, macOS-platform craft, and dashboard density in one piece. Roughly 4.5x the token cost of `core`.
</example>

<example>
Debate mode for a hard tradeoff:
```
/council debate Should we move sessions from in-memory to Redis to support horizontal scaling? See @src/session.rs and @docs/scaling-rationale.md
```
Selects relevant personas (likely hebert + tef + muratori + meadows), runs three rounds.
</example>

<example>
Quick free-form question (defaults to core profile auto-detect):
```
/council Are we using too many feature flags?
```
Likely selects a compact mix such as `tef-deletability-reviewer`, `hebert-resilience-reviewer`, and `meadows-systems-advisor` unless the problem text points elsewhere.
</example>

## Adding a persona

[references/personas.md](references/personas.md) is the canonical persona registry. The tables in this file are a quick-reference convenience for selection - keep them in sync with `personas.md` when you add or rename a persona.

1. Add a research dossier in [references/](references/) (markdown). Match the structure of existing dossiers - identity & canon with primary URLs, core philosophy with verbatim quotes, signature phrases, what they reject and praise, review voice & technique, common questions, edge cases, anti-patterns when impersonating.
2. Add a subagent file in [agents/](../../agents/) following the existing personas as a template - frontmatter with `name`, `description`, `tools`, `permissionMode`; voice rules (don't-bullets); core lens (numbered principles with sourced quotes); required output format including the mandatory "Where I'd be wrong" section; debate-mode named-agreement and named-disagreement scaffolding; honest skew.
3. Add a row to the canonical table in [references/personas.md](references/personas.md) and to the matching quick-reference table in this file.
4. Decide whether the persona belongs in a compatibility `core-*` preset or only in `auto` / `all` / `debate` selection (domain-specific lens).
