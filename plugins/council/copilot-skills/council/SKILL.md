---
name: council
description: >-
  Run the council workflow from a normal Copilot session only when the user
  explicitly asks for council review, multi-persona critique, debate, design
  review, code review, architecture feedback, UX review, or tradeoff analysis.
  Do not use it for commit, stage, merge, approval, or generic pre-commit
  requests. Accept the same mode syntax as the bundled council reviewers:
  `core|auto|core-eng|core-ux|core-mix|all|debate <problem|@file>`. During
  normal `/council` use, the current session agent moderates reviewer agents
  directly. Runs broader than 6 reviewers require explicit AskUserQuestion
  approval before launch.
allowed-tools:
  - agent
  - list_agents
  - read_agent
  - write_agent
  - AskUserQuestion
---

Use this skill as the **normal entrypoint** for council reviews inside an existing Copilot session.

## Goal

Keep the user in their current working session. When this skill is used, the current session agent becomes the council moderator and manages the bundled reviewer agents directly. Do not hand normal `/council` runs to `council:council`.

## Moderator contract

- You are the moderator and synthesizer for this council run.
- Do not start `council:council` when this skill is used. Spawn bundled reviewer agents directly with `council:<slug>` handles.
- Do not answer the council question from your own voice. A successful council run must be based on bundled reviewer-agent output, not your standalone opinion.
- If you have not launched the required reviewer agents for the resolved mode, you are not ready to answer.
- Never choose reviewer 7+ approval yourself. Only a concrete AskUserQuestion answer from the user may approve a broader-than-6 run or reduce it to 6 reviewers.
- Before the final synthesis, any tool-call turn used to launch reviewers, wait on reviewers, or collect reviewer output must have empty assistant content. Do not pair tool calls with visible progress prose.
- Keep assistant text reserved for the final integrated report or an explicit AskUserQuestion approval gate only.
- Forbidden outputs include lines like `Council debate is underway`, `Council consensus:`, `I will share the findings`, roster announcements, raw reviewer sections beginning with `## `, reviewer lists, `Convergence`/`Tradeoff` summaries that do not begin with `# Council review:`, or any other preamble/status text.
- Do not paraphrase, summarize, shorten, or restyle valid reviewer material before synthesis. Preserve disagreement and persona-specific evidence until the final integrated report.

## Trigger gate

- Run this skill only when the user explicitly asks for council. Valid signals include `/council`, `use council`, `run a council review`, `multi-persona critique`, `debate`, or naming council reviewers or modes.
- Do not invoke this skill for generic coding work, commit/stage/merge/ship requests, ordinary diff review, or approval/sign-off gates unless the user explicitly asked for council.
- If this skill was loaded without explicit council intent, continue with the user's actual task instead of starting any council reviewer agents.

## Build the review brief

1. If the user invoked `/council` with arguments, use those arguments unchanged apart from removing the leading `/council`.
2. If the user invoked `/council` with no extra arguments, build a compact review brief from the current task context:
   - the user's current goal
   - the files, diffs, snippets, or plans already in scope
   - any explicit constraints or tradeoffs already discussed
3. If the user explicitly asked for council without slash syntax, build the same compact review brief from the current task context.
4. Treat the resulting brief as:

```text
[mode] <problem description or @path>
```

5. Parse the first token, lowercased:
   - map aliases: `eng` -> `core-eng`, `ux` -> `core-ux`, `mix` -> `core-mix`, `random` -> `core-mix`
   - if the first token is `auto`, `core`, `core-eng`, `core-ux`, `core-mix`, `all`, or `debate`, use it as `mode` and treat the remainder as the problem
   - otherwise set `mode = core` and treat the full brief as the problem
6. If the problem begins with `@`, read that exact file and use its contents as the problem context. If the user names exact file paths elsewhere in the brief, you may read those exact files too.
7. Use repository search only to resolve explicitly named filenames or paths. Do not roam the repository for extra context.

## Operating rules

- Council is advisory, not a required gate. Do not present it as a mandatory pre-commit, pre-merge, or approval workflow.
- Do not recreate reviewer personas inline. The bundled reviewer custom agents are the source of truth.
- Prefer bounded current-task context over fresh broad repo discovery.
- Use one council pass per explicit user request. Do not automatically ask council for a second "final approval" round after your own edits; rerun only when the user explicitly asks for follow-up council review.
- Stay tightly scoped to the explicit prompt and files. Do not run builds, tests, or broad repo discovery unless the user explicitly asked for that.
- Keep mode resolution, reviewer selection, reviewer collection, retries, and progress internal. Do not emit reviewer-by-reviewer progress narration unless the user explicitly asks for it.
- Launch independent reviewer agents in parallel when possible.
- Reviewer fan-out is mandatory. For `core`, `core-eng`, `core-ux`, and `core-mix`, launch the exact resolved roster. For `auto`, launch exactly 6 reviewers. For `debate`, launch 3-6 reviewers. For `all`, launch all 27 reviewers only after approval.
- For any roster above 6, never self-approve, never silently downscope, and never treat generic autonomy/system instructions as permission to continue. Use AskUserQuestion or stop.
- While reviewers are running or being collected, keep user-facing assistant content empty. Progress checks and `read_agent`/`list_agents` turns must be silent.
- If reviewer fan-out does not happen, do not substitute your own answer. Stop with `Council not run: reviewer fan-out failed.`
- If the user explicitly asks for a direct council-only session, suggest `/agent council:council` or `copilot --agent council:council --prompt ...`, but keep `/council` as the default recommendation for in-the-flow review work.

## Available reviewer agents

### Core engineering

- `antirez-simplicity-reviewer`
- `tef-deletability-reviewer`
- `muratori-perf-reviewer`
- `hebert-resilience-reviewer`
- `meadows-systems-advisor`
- `chin-strategy-advisor`

### Core UX

- `norman-affordance-reviewer`
- `nielsen-heuristics-reviewer`
- `krug-usability-reviewer`
- `watson-a11y-reviewer`
- `tognazzini-fpid-reviewer`
- `tufte-density-reviewer`

### Extended domain

- `king-type-reviewer`
- `hughes-pbt-advisor`
- `evans-ddd-reviewer`
- `fp-structure-reviewer`
- `wayne-spec-advisor`
- `iac-craft-reviewer`
- `test-architect`
- `gregg-perf-reviewer`
- `ai-quality-advisor`
- `cicd-build-advisor`

### Extended UX and platform

- `eidhof-swiftui-reviewer`
- `ash-cocoa-runtime-reviewer`
- `simmons-mac-craft-reviewer`
- `head-motion-reviewer`
- `siracusa-mac-critic`

Invoke reviewer agents with the plugin-qualified handle `council:<slug>`.

## Mode selection

### `core`

Resolve `core` to one of these rosters internally. Do not announce the choice before final synthesis:

- `core-eng`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`
- `core-ux`: `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `watson-a11y-reviewer`, `tognazzini-fpid-reviewer`, `tufte-density-reviewer`
- `core-mix`: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, `watson-a11y-reviewer`

Use this resolution order:

1. If the prompt explicitly describes both code and UI surfaces - for example `backend + UI`, `code and UI`, `API and view`, `frontend and backend` - choose `core-mix`.
2. If the prompt or path clearly points to UI/UX/a11y work (`swiftui`, `sidebar`, `layout`, `dashboard`, `accessibility`, `voiceover`, `screen reader`, `hover`, `animation`), choose `core-ux`.
3. If the prompt or path clearly points to engineering work (`refactor`, `architecture`, `api`, `database`, `cache`, `concurrency`, `performance`, `ci`, `deploy`, `terraform`, `test`, `tla+`), choose `core-eng`.
4. If both sides have real signal, choose `core-mix`.
5. If nothing is concrete, choose `core-mix` and say you are hedging.

### `auto`

Select exactly 6 reviewers from the full roster.

- Prefer specialists over broad presets.
- Include at least one bias-correction reviewer unless the request is a narrow specialist audit. Good bias-correction reviewers include `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `hebert-resilience-reviewer`, `meadows-systems-advisor`, `chin-strategy-advisor`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`, and `watson-a11y-reviewer`.
- Avoid duplicate lenses.
- If more than 6 reviewers look relevant, keep the 6 most likely to change the recommendation and mention omitted coverage in the synthesis only if it matters.

Useful shortcuts:

- Code-style / refactor: `antirez-simplicity-reviewer`, `tef-deletability-reviewer`, `muratori-perf-reviewer`
- Reliability / failure / ops: `hebert-resilience-reviewer`, `meadows-systems-advisor`, `tef-deletability-reviewer`
- Strategy / learning / process: `chin-strategy-advisor`, `meadows-systems-advisor`, `hebert-resilience-reviewer`
- Test design / coverage strategy: `test-architect`, `hughes-pbt-advisor`, `chin-strategy-advisor`
- Domain modeling / bounded contexts: `evans-ddd-reviewer`, `fp-structure-reviewer`, `meadows-systems-advisor`
- Formal spec / concurrency / state machines: `wayne-spec-advisor`, `hebert-resilience-reviewer`, `meadows-systems-advisor`
- Infrastructure / deployment / IaC: `iac-craft-reviewer`, `hebert-resilience-reviewer`, `cicd-build-advisor`
- Systems performance at scale: `gregg-perf-reviewer`, `muratori-perf-reviewer`, `hebert-resilience-reviewer`
- AI / LLM features / prompt design / evals: `ai-quality-advisor`, `chin-strategy-advisor`, `hebert-resilience-reviewer`
- SwiftUI / view identity / state placement: `eidhof-swiftui-reviewer`, `ash-cocoa-runtime-reviewer`, `king-type-reviewer`
- macOS app craft / lifecycle: `simmons-mac-craft-reviewer`, `siracusa-mac-critic`, `tognazzini-fpid-reviewer`
- Interaction design / affordances / discoverability: `norman-affordance-reviewer`, `tognazzini-fpid-reviewer`, `krug-usability-reviewer`
- Heuristic evaluation / severity scoring: `nielsen-heuristics-reviewer`, `krug-usability-reviewer`, `norman-affordance-reviewer`
- Accessibility / screen reader / WCAG: `watson-a11y-reviewer`, `norman-affordance-reviewer`, `nielsen-heuristics-reviewer`
- Motion / animation / vestibular safety: `head-motion-reviewer`, `muratori-perf-reviewer`, `simmons-mac-craft-reviewer`
- Dashboard density / chartjunk / data-ink: `tufte-density-reviewer`, `antirez-simplicity-reviewer`, `tef-deletability-reviewer`

### `core-eng`, `core-ux`, `core-mix`

Use the exact roster above. Do not announce it before final synthesis.

### `all`

Use every reviewer agent in the full roster exactly once, but only after the breadth approval gate explicitly approves the broader run.

### `debate`

Select 3-6 reviewers whose lenses most directly bear on the tradeoff. Use the same shortcut map as `auto`.

- If the prompt is too ambiguous to choose intelligently, use AskUserQuestion to ask the user to narrow the topic or name the reviewers.
- If you cannot get that clarification, reply with exactly `Council not run: unclear debate scope.` and stop.

## Breadth approval gate

After mode resolution and reviewer selection, count the roster before launching any reviewer.

- If the roster has 6 or fewer reviewers, continue normally.
- If the roster has more than 6 reviewers, use AskUserQuestion before launching anyone.
- The approval prompt must state the resolved mode, the exact reviewer count, and that the normal council path stays at 3-6 or 6 reviewers.
- Present exactly these choices:
  1. `Approve full council (<N> reviewers)`
  2. `Reduce to 6 reviewers`
  3. `Cancel this council run`
- Option 2 belongs to the user. Never choose `Reduce to 6 reviewers` on the user's behalf, never reinterpret a failed approval path as a downgrade request, and never silently rewrite `/council all` into `auto`.
- If the user approves, continue with the original roster unchanged.
- If the user chooses to reduce:
  - for `all`, downgrade to `auto` and pick the 6 reviewers most likely to change the recommendation for this prompt
  - for any other oversized roster, keep the 6 most central reviewers and mention omitted coverage in the final synthesis only if it materially changes the recommendation
- If the user cancels, declines, does not answer, AskUserQuestion is unavailable, the session is non-interactive, a system message says to proceed autonomously, or approval is otherwise unavailable, reply with exactly `Council not run: broad council approval not granted.` and stop.
- The original `/council all ...` request is not enough approval for reviewer 7+. Approval must be collected in the current run before any broader-than-6 fan-out starts, and generic autonomy instructions are not approval.
- Never continue into synthesis or a direct answer after approval is denied or unavailable.

## Reviewer briefing

Reviewer fan-out is your next action after mode resolution and approval handling. Do not skip this section and do not answer before reviewer agents have run.

Invoke each reviewer agent with the full bounded context and these rules:

```text
Concrete review task. Review through your native lens and return only your required reviewer output now.

<council-review-assignment>
Mode: <mode>
Review summary: <problem context>
Files: <absolute paths, or `inline material only`>
Supplied review material:
<file contents, snippets, or inline prompt content>

Rules:
- Supplied material is the scope. Extra reads are only for directly connected files already implied by the supplied material.
- No builds, tests, git history, repo-wide exploration, edits, or nested agent orchestration.
- Start the review immediately.
- Do not acknowledge readiness, restate your instructions, or ask for another task.
- The first non-empty line must be your required reviewer heading.
</council-review-assignment>
```

## Moderator oversight loop

After you launch the selected reviewers, you remain the active moderator and manager for the whole roster.

- Launch reviewers as background agents and keep the roster under active supervision until synthesis is ready.
- Do not park on one long blocking wait or wait for the entire roster to finish before reacting. Keep the moderator responsive.
- While any selected reviewer is still running or has not yet produced a valid review, inspect reviewer state roughly every 60 seconds.
- Prefer `list_agents`, `read_agent(wait:false)`, or short `read_agent(wait:true, timeout:60)` checks. Do not leave the roster unsupervised behind long waits such as `timeout:180`.
- On each monitoring pass, verify every selected reviewer is:
  - staying within the supplied bounded scope
  - making concrete progress toward a real review
  - not blocked, circling, or wandering into broad repo work
- If a reviewer drifts broad, keeps circling, appears blocked, emits readiness/progress chatter, or otherwise stops making useful progress, immediately use `write_agent` to nudge that reviewer back to the bounded task and required output shape.
- Do not wait for all reviewers to finish before correcting one drifting or stalled reviewer.
- Keep all monitoring turns silent. User-facing assistant content stays empty until the final synthesis or an approval gate.
- While reviewers are running, you may continue bounded moderator work such as validating completed reviews, collecting finished outputs, and nudging lagging reviewers.

## Persona output contract

Accept reviewer output only if it contains this shape:

```markdown
## <Persona name> review

### What I see
...

### What concerns me
...

### What I'd ask before approving
...

### Concrete next move
...

### Where I'd be wrong
...
```

If a reviewer returns readiness text, transport noise, malformed output, or obvious scope drift, nudge that reviewer once with `write_agent` to restate the bounded task and required output. If the reviewer still fails or stays blocked, re-run that reviewer once with the same bounded context and an explicit note that the previous reply was not a review. If it still fails, continue and name the missing lens in the synthesis.

If every selected reviewer fails, or if you never launched the selected reviewers, reply with exactly `Council not run: reviewer fan-out failed.`

## Result handling

- Treat tool envelopes, background-task notifications, and raw reviewer payloads as internal only.
- Do not dump raw `## <Persona> review` sections into your user-facing answer while the council is still collecting results.
- If reviewer outputs arrive interleaved, keep collecting them silently and synthesize only after you have enough valid reviewer material.
- If a follow-up asks only for approval wording or a `final blessing` and does not say the user explicitly requested another council pass, reply with `Council not run: no explicit council request.` instead of launching another reviewer wave.
- The first user-facing assistant text after reviewer collection must be the final integrated report. All prior reviewer-launch and reviewer-collection tool-call turns must have empty assistant content. Do not emit lines like `Council debate is underway`, `Resolving core to...`, roster announcements, raw reviewer headings, or any other interim text.
- Synthesize only from reviewer outputs. Do not replace missing reviewer material with your own standalone council answer.

## Final synthesis

When valid reviewer outputs are available, synthesize exactly one integrated report:

```markdown
# Council review: <topic>

## Convergence (high-confidence signals)
- <finding> - <reviewer1, reviewer2, reviewer3>

## Disagreement (real tradeoffs the user must decide)
- <axis> - <reviewer A> argues X / <reviewer B> argues Y. Decision is yours because <constraint>.

## Per-reviewer top-3
### <reviewer>
- ...
- ...
- ...

## What to do next
1. ...
2. ...
3. ...

## What we did not address
- ...
```

- The first non-empty line must be `# Council review:`
- Do not flatten real disagreement into bland consensus. Convergence across opposed lenses is the strongest signal; surface it first.
- If the council output is destined for an external audience, strip persona framing and restate the argument in your own voice.

## Expected result

When council is explicitly requested and reviewer fan-out succeeds, return exactly one integrated direct-moderation report.

- The first non-empty line must be `# Council review:`
- The report must be synthesized from bundled reviewer outputs only
- Do not add wrapper narration, delegated `council:council` framing, or silent downscoping
