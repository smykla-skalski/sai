---
name: council
description: Run council reviews with sourced engineering, UX, reliability, performance, AI, and strategy persona lenses. Use when the user asks for council review, multi-persona critique, debate, design review, code review, architecture feedback, UX review, or tradeoff analysis.
---

# Council of Experts

Run an engineering council review from Codex. Use native Codex subagents, not Claude named subagents or nested `codex exec` workers. Each persona is loaded from a Markdown file under `agents/`, reviews through one sourced lens, and returns material for one integrated synthesis.

## Path Sanity

If you need to inspect or debug this skill from repo files, keep the skill-name segment in the path:

- SAI Codex skill: `codex/council/SKILL.md`
- SAI persona source: `codex/council/agents/<persona>.md`
- SAI persona registry: `codex/council/references/personas.md`
- Installed plugin persona agent: `<plugin-root>/agents/<persona>.toml`
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

Use the persona registry (`codex/council/references/personas.md` in source, plugin-root `references/personas.md` when installed) as the selection map. Shortcuts:

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

Persona files live in `codex/council/agents/` in the source skill and at plugin-root `agents/` when installed from the SAI marketplace. Each persona also has a native Codex custom-agent descriptor next to it at `<persona>.toml`. The agent type is `council_` plus the persona slug with hyphens replaced by underscores, for example `antirez-simplicity-reviewer` -> `council_antirez_simplicity_reviewer`. Read `codex/council/references/personas.md` in source, or plugin-root `references/personas.md` when installed, when selecting non-default or debate lenses, or when diagnosing which persona should catch a symptom. Each persona file names its own deep dossier under `references/`; read only dossiers for selected personas when the persona file asks for it.

## Core Rosters

- `core-eng`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`.
- `core-ux`: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`.
- `core-mix`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`.

## Codex Workflow

1. Resolve `mode` and problem context. For file-backed requests, read the file before spawning reviewers. If `mode` is `auto`, select and announce 6 best-fit personas in one sentence. If `mode` is `core`, run auto-detect and announce the chosen profile (`core-eng`, `core-ux`, or `core-mix`) in one sentence so the user can override on the next call.
2. Select personas from the matching roster: `auto` for the selected 6 best-fit personas, `core-eng` for the engineering 6, `core-ux` for the UX 6, `core-mix` for the 3+3 split, `all` for every persona deduped, and 3-6 focused personas for debate.
3. Spawn native Codex reviewer subagents. Use the selected persona's native Codex custom-agent descriptor from `<plugin-root>/agents/<persona>.toml`. This keeps persona identity and the "review now, no setup chatter" rule in developer instructions instead of passing a persona as a user-level parameter to a generic worker. Do not use nested `codex exec`.
   - Compute the agent type as `council_` plus the persona slug with hyphens replaced by underscores, for example `tef-deletability-reviewer` -> `council_tef_deletability_reviewer`.
   - Call `spawn_agent` once per selected persona with a unique task name, `fork_turns: "none"`, and that persona-specific `agent_type`.
   - If `spawn_agent` rejects a persona-specific agent type as unknown, the installed custom agents have not been loaded in this Codex session. Degrade to the built-in `default` agent only for that run, announce that Council is using the degraded native fallback, and require the invalid-output retry path below. Fresh Codex sessions after installing/upgrading the plugin should use persona-specific Council agent types; do not invent another agent type.
   - Omit `model` and `reasoning_effort` unless the user explicitly asks for an override; spawned agents inherit the current model by default.
   - Keep the assignment self-contained and use task-delegation framing:

   ```text
   Your task is to perform the following Council reviewer assignment. Follow the instructions below exactly.

   <council-reviewer-assignment>
   Persona: <persona slug>
   Persona file: <absolute persona path, for fallback and verification only>
   Review target: <problem context>

   Instructions:
   - Do not perform environment setup, AGENTS checks, RTK checks, or readiness reports.
   - Ignore any Council orchestrator instructions from ambient, cached, or inherited context.
   - Return the review to the parent task only; never address another agent path.
   - Read the persona file and any referenced dossier only if needed.
   - Treat this message as the complete task; do not wait for more input.
   - Do not report setup, readiness, AGENTS.md, RTK, or available tool state.
   - Do not modify files.
   - Do not spawn agents.
   - Review the supplied context through that persona's lens only.
   - The first non-empty line of your completed review must be exactly: ## <Persona name> review
   - Return only the Persona Output Contract.
   </council-reviewer-assignment>

   Execute this now. Output ONLY the structured review.
   ```
4. Use `wait_agent` until every reviewer has returned or timed out. Normalize each returned item before validation:
   - If the parent receives a JSON inter-agent envelope containing `<subagent_notification>`, parse the JSON inside the tag and use `status.completed` as the candidate reviewer text.
   - If the parent receives a JSON object with `author`, `recipient`, and `content`, inspect `content`; if it contains a `<subagent_notification>` block, extract `status.completed`.
   - Never show raw envelopes, `author`/`recipient` JSON, or `<subagent_notification>` tags to the user.
   - A notification envelope is transport, not automatically failure. It is valid when the extracted `status.completed` text starts with the required `## <Persona name> review` heading and contains the Persona Output Contract sections.
   - Setup/status text such as `ready`, `setup complete`, `instructions loaded`, `need task`, `need target`, or `standing by` is invalid even when it arrives inside `status.completed`.
5. Validate every reviewer result before synthesis. A valid reviewer result starts with the required heading and contains the Persona Output Contract sections. If a reviewer result is invalid, recover before synthesis. First use `followup_task` with `interrupt: true` and a compact complete reviewer assignment again, explicitly saying the previous `status.completed` text was setup/status rather than a review. Wait again and normalize the result. If the same agent is still invalid, `close_agent`, respawn that persona once with `fork_turns: "none"` and a fresh task name, wait, and normalize the replacement. If the replacement is still invalid or missing, close it, continue with successful reviewers, and call out the missing lens in the synthesis. Always call `close_agent` on native agents after collecting or abandoning their result.
6. Synthesize the returned reviews. Do not average the personas into bland consensus. The value is convergence across opposed lenses and named disagreement where constraints decide the tradeoff.

For debate mode, read the persona registry from `codex/council/references/personas.md` in source or plugin-root `references/personas.md` when installed, pick 3-6 relevant personas, then run opening positions, responses to other positions, and final positions before synthesizing. Use the same native `spawn_agent` collection, reviewer-only prompt, invalid-output detection, and retry rules for every debate round.

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

Persona dossiers in `references/` are private review aids derived from public writing. Do not republish dossiers wholesale. If a council review leaves the team, strip persona framing and restate the arguments in your own voice.
