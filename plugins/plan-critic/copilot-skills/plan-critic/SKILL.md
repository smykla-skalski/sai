---
name: plan-critic
description: >-
  Critique an implementation plan from a normal Copilot session when the user
  shares a plan (Plan Mode output, pasted plan text, or a plan file path) and wants
  it stress-tested before any code is written. Triages the plan, grounds it against
  the codebase, delegates to three native persona reviewers (Skeptic, Architect,
  Verifier), and returns an Approve/Reject/Refine verdict with concrete refinements.
  Not for executing the plan, reviewing an already-written diff, or a quick lint pass.
allowed-tools:
  - agent
  - list_agents
  - read_agent
  - write_agent
  - read
---

# Plan Critic (Copilot)

Critique an implementation plan **before** any code is written. The cost of revising a plan is near-zero; the cost of revising executed code is hours of rework. This skill keeps orchestration in-session: the current Copilot agent triages the plan, builds one Grounding Brief from the codebase, delegates to three native persona reviewer agents, and synthesizes a single verdict. Nothing is approved until three independent personas have inspected the plan against ground truth.

**Core principle:** A plan that names files generically has not been read. A plan that references `verify_jwt_token` at `auth/middleware.go:42` has been read. The job of this skill is to tell those apart and force the second.

## The reviewers (3 native agents)

Bundled as custom agents under `agents/` (namespaced, e.g. `plan-critic:skeptic-reviewer`). Their exact instruction blocks live in [references/personas.md](references/personas.md) - read it before Phase 3 so you brief each reviewer faithfully.

| Reviewer agent | Lens |
|---|---|
| `skeptic-reviewer` | What's missing - hidden assumptions, edge cases, failure modes, rollback gaps, missing verification criteria |
| `architect-reviewer` | Is it built right - file selection, execution order, convention fit, scope, backward compatibility, system impact |
| `verifier-reviewer` | Did the author actually read the code, or skim file names - symbol specificity, cross-check vs the Grounding Brief, architectural awareness |

Keep this reviewer framing internal (see Privacy / scope).

## Parsing the request

The user's text (or an attached file / pasted block) is the plan to review. Resolve it first: read the file if a path was given, use the inline text if pasted, or adopt the most recent plan produced in this conversation. If no plan is resolvable, ask which plan to review - do not invent one.

## Workflow

### Phase 1 - Triage (fast, do not delegate)

Resolve the plan input, then run a fast scope check. **This phase never delegates** - if it finds a fundamental issue, report it and stop.

1. **Is this actually a plan?** It must describe *what* will change and *where*, not just narrative discussion. If it has no concrete file/function/step list, ask the user to convert it into a plan first, then stop.
2. **Plan size scan.** Count files mentioned, count distinct steps/phases, and note whether line numbers or symbol names appear.
3. **Trivial-change escape hatch.** If the plan describes a change that fits in one sentence (typo, single-line fix, rename in one file), tell the user planning overhead is not warranted - recommend executing directly - and stop. Do not delegate to reviewers for trivial plans.
4. **Scope warning.** If the plan touches **7 or more files**, surface this immediately: context degrades plan quality past this threshold and reviewers begin missing cross-file interactions. Recommend splitting into sub-plans before review, or proceeding only with explicit acknowledgment.

If triage finds a fundamental issue (not a plan, trivial, or oversized), report and stop here.

### Phase 2 - Grounding Brief (build INLINE, do not delegate)

Build the **Grounding Brief yourself in the orchestrator** by grep/read over the codebase. All three reviewers share this one brief - do not delegate this phase and do not let each persona re-explore.

Produce, against the real code:

1. **File verification** - for every file the plan names, confirm it exists; list missing/misnamed paths.
2. **Symbol verification** - for every function/type/symbol the plan names, locate it (`path:line`) and flag any that do not exist or are misnamed (e.g. plan says `UserStore.Save`, code has `UserRepository.Persist` at `store/user.go:118`).
3. **Caller blast radius** - for functions the plan modifies, count callers and list 3-5 locations.
4. **Existing patterns** - find 2-3 existing examples of the kind of change proposed (e.g. existing handlers a new handler should mirror).
5. **Related tests** - find tests covering the modules being changed, and note coverage gaps.

Grounding Brief shape:

```
## Grounding Brief
### File verification
### Symbol verification
### Callers (blast radius)
### Existing patterns
### Related tests
```

The Brief is load-bearing - pass it verbatim to every reviewer. Trust the Brief over the plan's claims: when the plan says `X exists` and the Brief says `X not found`, the Brief wins.

### Phase 3 - Reviewer delegation (sequential by default)

Read [references/personas.md](references/personas.md), then delegate each reviewer through the `agent` tool, giving each one: the **full plan text**, the **Grounding Brief** from Phase 2, that persona's mandate, and the instruction that its first response line must be `## <Persona> review`. Delegate the Skeptic, then the Architect, then the Verifier.

Default to sequential reviewer delegation - one agent at a time. Copilot parallel fan-out over-parallelizes and burns AI credits and offers no reliability guarantee; sequential is the reliable path. Only fan out in parallel if the user explicitly asks, then supervise with list_agents/read_agent and confirm each returned a payload before synthesizing.

Validate each reviewer result: it must start with `## <Persona> review` and contain the persona's contract sections. If a result is malformed or empty, re-delegate that reviewer once with the same plan + Brief; if still malformed, continue and note the missing lens in the synthesis. Never surface raw reviewer envelopes or readiness text.

### Phase 4 - Synthesis and verdict

Recall the Phase 1 scope flags and the Phase 2 Grounding Brief before reading reviewer output, so the verdict stays anchored to verified evidence rather than persona assertion. Then **merge** the three reviews into one verdict - do not concatenate them:

1. **Deduplicate** - if two reviewers flagged the same missing file or symbol, merge into one finding.
2. **Separate blockers from improvements** - blocking issues first, then refinements, then nits.
3. **Surface disagreement, don't flatten it** - if one reviewer leans APPROVE and another REJECT, present the conflict explicitly and let the user adjudicate; trust the more conservative reviewer when forced to pick.
4. **Cross-cutting insight** - call out findings that emerge only from combining perspectives (e.g. Verifier says a file was not read + Architect says the plan ignores its 20 callers + Skeptic says no test covers the new behavior = one strong blocker).
5. **Pick one verdict:**
   - **APPROVE** - strategy sound, depth adequate, no critical gaps. Safe to execute.
   - **REFINE** - on the right track but needs specific, concrete additions/corrections first. Provide an ordered refinement list (if it grows past ~5 items, switch to REJECT).
   - **REJECT** - fundamental issues (wrong approach, missed key files, hallucinated symbols, surface reading). Must be re-planned after the author reads more code.

Return findings only - do not rewrite the plan yourself; evaluation and authorship are different jobs.

## Synthesis output shape

```
# Plan Review

## Verdict: [APPROVE | REFINE | REJECT]
**One-line summary:** <why, in one sentence>
**Plan stats:** <N files, M steps, depth: Deep/Surface/Shallow>

## Triage notes
<scope/size flags from Phase 1; skip if clean>

## Grounding Brief
<the Phase 2 brief>

## Findings
<merged, deduplicated findings ranked blockers -> refinements -> nits>

## Disagreement
<where the reviewers diverged; skip if they converged>

## Refinement list
<only if REFINE: concrete, ordered changes to make before approval>

## Rejection rationale
<only if REJECT: what is fundamentally wrong and what to read before re-planning>

## Next action
<"Approved - proceed with execution." | "Refine using the list above, then re-submit."
 | "Reject - read <files> and re-plan from scratch.">
```

## Privacy / scope

The reviewer personas are internal review aids. Keep reviewer framing internal - present one synthesized verdict to the user, not three raw envelopes; if a finding leaves the team, restate it in your own voice. This skill reviews a *plan*, before code exists - it does not execute the plan, and it is not a substitute for reviewing an already-written diff (use a staff-level or language-specific code review for that).
