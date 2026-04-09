# plan-critic

Critique a Claude implementation plan **before** any code is written. Spawns parallel persona subagents (Skeptic, Architect, Verifier) to evaluate the plan against the codebase and return an Approve/Refine/Reject verdict with concrete refinements.

## Features

- **Triage** — fast scope check, trivial-change escape hatch, 7+ files scope warning
- **Grounding Brief** — single Explore agent verifies every file/symbol the plan names against the actual codebase, lists callers, surfaces existing patterns
- **Three parallel personas** — Verifier (did Claude read the code?), Architect (is the structure sound?), Skeptic (what's missing?)
- **Three-Response Framework** — Approve / Refine / Reject verdict with refinement list or rejection rationale
- **Calibration guardrails** — don't reject for preference, don't refine into oblivion, trust the Grounding Brief over plan claims

## Usage

Triggers on: "critique this plan", "review this plan", "is this plan good", "poke holes in this plan", "should I approve this plan", or sharing a plan for evaluation.

Also user-invocable:

```text
/plan-critic <plan file path>
/plan-critic <paste plan inline>
/plan-critic --from-conversation
```

## Reference Material

- `skills/plan-critic/references/personas.md` — full prompts for the Verifier, Architect, and Skeptic persona subagents
