---
name: plan-critic
description: Critique an implementation plan before approving execution. Runs three persona reviewers (Skeptic, Architect, Verifier) against the codebase, in parallel on Claude Code and one at a time on other agents, and returns an Approve/Reject/Refine verdict with concrete refinements. Use when a plan has been generated (Plan Mode output, ExitPlanMode, pasted plan text, or plan file path) and needs review before code is written. Triggers on "critique this plan", "review this plan", "is this plan good", "poke holes in this plan", "should I approve this plan", or sharing a plan for evaluation.
license: MIT
compatibility: Works in Claude Code, Codex, opencode and Copilot CLI. Needs read access to the codebase the plan targets; no scripts or network access.
argument-hint: "[plan file path | paste plan inline | --from-conversation]"
allowed-tools: Agent AskUserQuestion Bash Glob Grep Read
user-invocable: true
metadata:
  short-description: Critique implementation plans before coding starts
---

# Plan Critic

Critique a Claude implementation plan **before** any code is written. The cost of revising a plan is near-zero; the cost of revising executed code is hours of rework. This skill applies the plan-then-execute discipline rigorously: nothing gets approved until three independent personas have inspected it.

**Core principle:** A plan that names files generically has not been read. A plan that references `verify_jwt_token` at `auth/middleware.go:42` has been read. The job of this skill is to tell those apart and force the second.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the plan path, pasted plan, or `--from-conversation` from the user's request |
| AskUserQuestion | Ask the same question in plain text with the same options and wait for the answer |
| Explore subagent (Phase 2) | Build the Grounding Brief inline with grep/read. Do this on Codex, opencode and Copilot CLI, and in Claude Code whenever the Explore agent is unavailable |
| Named agents `plan-critic:skeptic-reviewer` / `architect-reviewer` / `verifier-reviewer` | Claude Code and Copilot CLI register them from the plugin's `agents/` directory. Codex and opencode do not; there, or whenever the type is unknown, use a generic subagent with the matching mandate from `references/` prepended (see [Spawning persona reviewers](#spawning-persona-reviewers)) |
| Parallel subagents (Agent) | Claude Code: all three personas in parallel. Copilot CLI, opencode, Codex: one persona at a time, Skeptic, then Architect, then Verifier. With no subagent tool, adopt each persona inline in the same order |
| `context: fork` | Not used |

## Arguments

Parse from `$ARGUMENTS`:

| Argument | Type | Description |
| :-- | :-- | :-- |
| `[plan file path]` | positional | Path to a markdown file containing the plan. Read it. |
| `[paste plan inline]` | positional | Plan text pasted directly in the user's message. Use as-is. |
| `--from-conversation` | flag | Use the plan most recently produced in the current conversation (e.g., from ExitPlanMode or a planning response). |

If input is ambiguous (multiple candidates, unclear which plan), use AskUserQuestion to disambiguate before proceeding. Present these options:

- **File path** — the user types a path to a plan markdown file
- **Paste inline** — the user pastes the plan text in the next message
- **Use `--from-conversation`** — adopt the most recent plan produced in this conversation

If no plan is resolvable, ask which plan to review; never invent one.

## Workflow

### Phase 1: Triage (fast, <1 min)

Resolve the plan input first: read the file if a path was given, use the inline text if pasted, or fetch the most recent plan from the conversation if `--from-conversation` was passed. Then do a fast scope check. This phase never delegates:

1. **Is this actually a plan?** It should describe *what* will change and *where*, not just narrative discussion. If it has no concrete file/function/step list, ask the user to convert it into a plan first.
2. **Plan size scan:**
   - Count files mentioned
   - Count distinct steps/phases
   - Note whether line numbers or function names appear
3. **Trivial-change escape hatch:** If the plan describes a change that fits in one sentence (typo, single-line fix, rename in one file), tell the user planning overhead isn't warranted — recommend skipping plan review and just executing. Do not spawn subagents for trivial plans.
4. **Scope warning:** If the plan touches **7 or more files**, surface this immediately as a concern because context window degrades plan quality past this threshold and reviewers begin missing cross-file interactions. Recommend the user split it into sub-plans before review continues, so each sub-plan stays small enough to verify deeply, or proceed with explicit acknowledgment.

If triage finds fundamental issues (not a plan, trivial, oversized), report and stop. Do not spawn subagents.

<example>
Input: User pastes a one-line plan: "Fix typo in README.md line 42."
Triage result: Trivial single-line change. Report "Planning overhead isn't warranted — execute directly." Skip Phase 2-5.
</example>

<example>
Input: A plan touching 14 files across 4 packages with no symbol-level references.
Triage result: Scope warning (7+ files) AND surface-level reading risk. Recommend splitting into sub-plans before review continues.
</example>

### Phase 2: Codebase Grounding (one Grounding Brief, 30-60s)

Build a **Grounding Brief**. All three review personas share this brief — no redundant exploration.

- **Claude Code:** spawn one `Agent` (subagent_type: `Explore`, thoroughness: `medium`) with the tasks below.
- **Other agents** (and Claude Code without the Explore agent): build the brief yourself with grep/read. Do not delegate it, and do not let each persona re-explore.

The brief must cover:

1. For every file the plan names, verify the file exists. List any missing/misnamed paths.
2. For every function, type, or symbol the plan names, grep for it and report the actual location (`path:line`). Flag symbols the plan names that do not exist in the codebase.
3. Identify the top callers of any function the plan proposes to modify (count + 3-5 caller locations).
4. Find existing patterns/conventions for the kind of change the plan proposes (e.g., if the plan adds a new HTTP handler, find 2-3 existing handlers it should mirror).
5. Find related tests for the modules being changed.

**Grounding Brief output format:**

```markdown
## Grounding Brief

### File Verification
- `path/to/a.go` ✓ exists
- `path/to/b.go` ✗ NOT FOUND (plan references it as "the user service")

### Symbol Verification
- `verify_jwt_token` → `auth/middleware.go:42` ✓
- `UserStore.Save` → not found; closest match is `UserRepository.Persist` at `store/user.go:118`

### Callers (blast radius)
- `parseRequest()` — 23 callers (top: handler/api.go:55, handler/admin.go:88, ...)
- `newHelper()` — 0 callers (proposed but never used elsewhere)

### Existing Patterns
- HTTP handlers in `handler/` use `respondJSON()` helper — plan should match
- Error wrapping via `errors.Wrapf` is the convention — plan uses bare `fmt.Errorf`

### Related Tests
- `handler/api_test.go` covers happy path; no error-path tests
- No tests exist for the package the plan modifies most heavily
```

### Phase 3: Persona Review

Three personas, each with its own mandate file. Read the mandate of every persona you brief or adopt before Phase 3 starts:

| Persona | Named agent | Mandate | Lens |
| :-- | :-- | :-- | :-- |
| **Verifier** | `plan-critic:verifier-reviewer` | [references/verifier-reviewer.md](references/verifier-reviewer.md) | Did the author actually read the code, or skim file names? |
| **Architect** | `plan-critic:architect-reviewer` | [references/architect-reviewer.md](references/architect-reviewer.md) | Is the structure sound? File selection, order, conventions, scope, compatibility |
| **Skeptic** | `plan-critic:skeptic-reviewer` | [references/skeptic-reviewer.md](references/skeptic-reviewer.md) | What's missing? Edge cases, failure modes, rollback, verification criteria |

Each persona receives the full plan text **and** the Grounding Brief from Phase 2 verbatim, plus the user's original request quoted verbatim when you have it (the Skeptic checks the plan against it), and nothing else.

#### Spawning persona reviewers

**Claude Code.** Spawn all three **in parallel** (single message, three Agent tool calls) using the named agent types above; their mandate is already the agent's system prompt. Parallelize because the personas are independent perspectives on the same inputs, so sequential spawning wastes wall time without improving quality. If a named type is unknown (plugin loaded without agent registration), retry with `subagent_type: "general-purpose"` and the mandate file prepended.

**Copilot CLI.** Delegate through the `agent` tool to the same named agents (`plan-critic:skeptic-reviewer`, `plan-critic:architect-reviewer`, `plan-critic:verifier-reviewer`), one at a time: Skeptic, then Architect, then Verifier. Copilot parallel fan-out burns AI credits with no reliability gain. Fan out in parallel only if the user explicitly asks, then supervise with `list_agents` / `read_agent` and confirm each returned a payload before synthesizing.

**Codex.** Default to inline: adopt the Skeptic, Architect, and Verifier lenses in turn, each following its mandate file, all grounded in the same brief. Codex subagent fan-out is fragile: the default `agents.max_threads` is 6, completed subagents do not free their slot until closed ([openai/codex#22779](https://github.com/openai/codex/issues/22779)), and subagents can finish without returning a payload ([openai/codex#16051](https://github.com/openai/codex/issues/16051)). Spawn subagents only if the user asks: one `spawn_agent` per persona with the mandate prepended, sequentially, `wait_agent`, then `close_agent` as soon as it returns. Use only the native agent tools; never nested `codex exec` or shell-based orchestration.

**opencode.** Use the `task` tool once per persona, sequentially. Use an installed `skeptic-reviewer` / `architect-reviewer` / `verifier-reviewer` subagent when present (see the plugin README); otherwise the built-in `general` subagent with the mandate prepended.

**No subagent tool.** Adopt each persona inline, in order, as a separate labelled section that follows its mandate's output contract.

**Validate every reply.** It must start with `## <Persona> review` and contain the persona's contract sections. If a reply is empty or malformed, spawn that persona once more with the same inputs; if it fails again, run that persona inline and note `inline` next to its findings.

### Phase 4: Synthesis & Verdict

Recall the Triage scope flags from Phase 1 and the Grounding Brief from Phase 2 before reading persona output, so the verdict stays anchored to verified evidence rather than persona assertions. After all three personas return, synthesize their output rather than concatenate it because raw concatenation hides duplication and obscures cross-cutting signals:

1. **Deduplicate** — If Verifier and Architect both flagged the same missing file, merge into one finding.
2. **Rank by severity** — Blocking issues first, then refinements, then nits.
3. **Cross-cutting insights** — Look for findings that only emerge from seeing all three perspectives. Example: Verifier says Claude didn't read `handler.go`, Architect says the plan ignores 20 callers there, Skeptic says no test covers the new behavior — together, this is a much stronger blocker than any one alone.
4. **Apply the Three-Response Framework** to produce a verdict:
   - **APPROVE** — Strategy is sound, depth is adequate, no critical gaps. Safe to execute.
   - **REFINE** — Plan is fundamentally on the right track but needs specific additions/corrections before execution. Provide a concrete refinement list.
   - **REJECT** — Fundamental issues (wrong approach, missed key files, surface-level reading). Plan needs to be redone from scratch after Claude reads more code.

### Phase 5: Output

Produce the final report in this exact structure. Under each persona heading, put that persona's review without its `## <Persona> review` line:

```markdown
# Plan Review

## Verdict: [APPROVE | REFINE | REJECT]

**One-line summary:** [Why this verdict in one sentence]

**Plan stats:** [N files, M steps, depth: Deep/Surface/Shallow]

## Triage Notes

[Any flags from Phase 1 — scope warnings, size concerns, etc. Skip if clean.]

## Grounding Brief

[Full output from Phase 2 — file/symbol verification, callers, patterns, tests]

## Verifier Findings

[Verifier review]

## Architect Findings

[Architect review]

## Skeptic Findings

[Skeptic review]

## Cross-Cutting Issues

[Findings that emerge only from combining all three persona perspectives. Skip if none.]

## Refinement List

[Only if verdict is REFINE. Concrete, ordered list of changes to the plan before approval:]
1. Read `path/to/file.go` lines X-Y to verify assumption about Z
2. Add step to update the 14 callers of `funcName` listed in the Grounding Brief
3. Specify success criterion for step 4 (e.g., "tests in `foo_test.go` pass")
4. ...

## Rejection Rationale

[Only if verdict is REJECT. What's fundamentally wrong and what Claude must do before re-planning.]

## Next Action

[One of:
- "Approved — proceed with execution."
- "Refine the plan using the list above, then re-submit for review."
- "Reject — Claude should read [specific files] and re-plan from scratch."]
```

<example>
Plan claims to update `UserStore.Save` callers. Grounding Brief reports `UserStore.Save` not found; closest is `UserRepository.Persist`. Verifier flags surface reading. Verdict: **REJECT**. Next action: Claude must read `store/user.go` and re-plan against the real symbol.
</example>

<example>
Plan touches 4 files, names 6 symbols with line numbers, all verified by the Grounding Brief. Architect confirms patterns match existing handlers. Skeptic finds one missing edge case (empty payload). Verdict: **REFINE**. Refinement list: one entry — add empty-payload handling in step 3.
</example>

## Calibration Guidance

These principles prevent common plan-review anti-patterns. Re-read this section before producing the verdict in Phase 4 to keep calibration consistent across reviews:

- **Approve valid approaches even when yours differs.** If the plan's approach is valid and an alternative is also valid, approve, because the Three-Response Framework judges *correctness*, not taste.
- **Reject instead of over-refining.** If the refinement list grows past ~5 items, switch to Reject and request a re-plan, since refining a fundamentally broken plan wastes more tokens than restarting.
- **Block on missing verification criteria.** A plan with no success criteria produces code that "looks right but doesn't work," so treat missing criteria as a refine-or-reject every time.
- **Trust the Grounding Brief over the plan's claims.** When the plan says `X exists` and the Brief says `X not found`, the Brief wins because plans hallucinate and greps don't.
- **Praise specificity.** When a plan references `auth/middleware.go:42` and the Verifier confirms it, call this out so good patterns get reinforced.

## When to Skip Plan Review (limitations and scope boundaries)

This skill is not designed for, and you should avoid using it on:

- One-sentence changes (typo, rename, single-line log) — execute directly instead
- Changes already executed — review the diff with `staff-code-review` instead
- Discussion-only outputs that aren't structured plans — ask the user to formalize the plan first
- Executing the plan itself — this skill only evaluates it

## Troubleshooting

Common failure modes and recovery:

- **Grounding agent times out or returns empty brief.** Re-spawn with a narrower scope (focus on the top 3 files the plan names). If still empty, fall back to running grep directly from the main context for the named symbols and proceed without the full brief — note the degraded confidence in the verdict.
- **Personas disagree (one APPROVE, one REJECT).** Trust the more conservative verdict. Surface the disagreement explicitly in the Cross-Cutting Issues section and let the user adjudicate.
- **Plan input is ambiguous or missing.** Use AskUserQuestion with concrete options (file path, paste inline, use last-conversation plan). Do not guess.
- **Plan references files in a different repo or path the agent can't access.** Stop and ask the user to either provide the files or scope the review to what is reachable.
- **All three personas return identical findings.** This usually means the plan is so vague that any reviewer surfaces the same gaps — flag as REJECT and request specifics before re-review.

## Anti-Patterns to Avoid

Each anti-pattern lists the failure mode followed by the correct alternative:

- **Spawning persona subagents before Phase 2 grounding** → run Phase 2 first, then pass the Grounding Brief to all three personas, because skipping it causes duplicate exploration and ungrounded persona output
- **Spawning personas sequentially in Claude Code** → spawn all three in a single message with parallel Agent calls, since the personas are independent perspectives (other agents run them one at a time, see Phase 3)
- **Approving a plan whose symbols don't exist** → reject and require Claude to re-read the codebase before re-planning, because hallucinated symbols guarantee broken code
- **Approving a plan with no verification criteria** → refine to add concrete success criteria (test passes, command output, endpoint response), so Claude can know whether the change worked
- **Rewriting the plan yourself in the output** → return findings only and let Claude (or the user) revise, because evaluation and authorship are different jobs and conflating them hides plan quality signals
- **Skipping the Grounding Brief because "the plan looks fine"** → always run Phase 2, since plan depth cannot be verified without ground truth from the codebase

## Example invocations

In Codex use `$plan-critic` in place of `/plan-critic`.

```text
/plan-critic docs/plans/add-rate-limiter.md
/plan-critic --from-conversation
/plan-critic <paste plan inline>
```
