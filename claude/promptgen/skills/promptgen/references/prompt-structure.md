# Prompt structure templates

Four template variants the skill fills in during generation. Pick based on `--for` flag.

# Contents

- [Claude variant (XML tags)](#claude-variant-xml-tags)
- [GPT variant (outcome-first Markdown)](#gpt-variant-outcome-first-markdown)
- [Codex variant (coding agent)](#codex-variant-coding-agent)
- [Generic variant (Markdown-only)](#generic-variant-markdown-only)
- [Prompt-type inserts](#prompt-type-inserts)
- [Skeleton rules (all variants)](#skeleton-rules-all-variants)

## Claude variant (XML tags)

```xml
You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

<outcome>
[Desired result]
[Done-when criteria - observable signals the answer is acceptable]
[Allowed side effects and evidence rules]
[Stop rule: when to ask, abstain, or report blocked]
</outcome>

<constraints>
[Non-negotiable rules, stated positively]
[Scope boundary if 4.7-style literal scope-restriction risk applies]
</constraints>

<instructions>
[Specific, actionable instructions organized by priority]
[Numbered steps only when order affects safety, correctness, or side effects]
</instructions>

<output>
[Format specification]
[Example of desired output shape if helpful]
</output>

<examples>
[Only when --examples is set or examples make format/edge cases clearer than prose]
<example>
<input>[Representative input]</input>
<response>[Desired output matching all constraints]</response>
</example>
</examples>
```

Notes for Claude:

- XML tags are native and well-supported for data boundaries. Use descriptive names; nest for hierarchy.
- Markdown headers work for section organization within tags.
- For long-context work, put longform data at the top wrapped in `<document index="n">`, queries at the end.
- Do not use anti-laziness prompts or aggressive emphasis. Soften tool-use language: "Use [tool] when it would help" not "You must use [tool]".
- For Opus 4.7 / Sonnet 4.6, use the `effort` parameter in API config for intelligence/cost. Manual `budget_tokens` and `thinking: {type: "enabled"}` are deprecated on 4.6 and removed on 4.7 - use `thinking: {type: "adaptive"}` paired with `effort` (`low | medium | high | xhigh | max`).
- Prefilled assistant responses are deprecated and rejected on 4.7. Use `<output>` tags or "Respond directly without preamble" instead.
- 4.7 follows scope literally. State explicit coverage ("Apply this to every section, not just the first one"). Avoid "Only X" phrasing that drops everything else - use severity tags or confidence labels for filtering instead.

## GPT variant (outcome-first Markdown)

```markdown
# Role and objective

You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

# Outcome contract

- Result: [expected artifact or behavior]
- Done when: [observable criteria]
- Evidence: [what the response must cite or reference]
- Side effects: [allowed actions and gates]
- Stop rule: [when to ask, abstain, or report blocked]

# Constraints

[Non-negotiable rules, stated positively]
Scope discipline: implement EXACTLY and ONLY what is requested. No extra features, no UX embellishments.

# Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps only when order affects safety, correctness, or side effects]

## [Sub-category if needed]

[Detailed instructions for specific areas]

# Output format

[Format specification]
[Example of desired output shape if helpful]
[Length budget: e.g., "<= 2 sentences" or "1 short paragraph then <= 5 bullets"]

# Examples

[Only when --examples is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]
```

Notes for GPT:

- Markdown headers (H1-H4) for sections.
- Tune `reasoning_effort` (`none | minimal | low | medium | high | xhigh`) and `verbosity` in the API instead of writing prose that approximates them. GPT-5.2 default is `none`; calibrate up only for genuinely complex multi-step work.
- GPT-5.2 follows instructions more literally. Audit for contradictions; they damage reasoning. Use "Do not" exception clauses for narrow exclusions instead of layering positive directives.
- Skip routine "important reminders" at the end - GPT-5.2 instruction adherence makes them redundant. Reserve recency-effect repetition for resolving a specific contradiction or for older models.
- Place stable prompt text before dynamic variables for caching. Use API structured outputs or strict tools instead of long prose schemas when available.
- Calibrate tool-call persistence with budgets ("max 2 search calls before answering"). Provide an escape hatch ("if uncertain after 2 calls, answer with the best available evidence and flag uncertainty").

## Codex variant (coding agent)

```markdown
You are [Name], a coding agent operating in the user's repository.
[1-sentence scope/purpose].

# Outcome contract

- Result: [expected change or artifact]
- Done when: [acceptance criteria - tests passing, build green, behavior verified]
- Evidence: [validation command output, manual checks, screenshots]
- Side effects: [allowed file edits, commands, commits, network, external systems]
- Stop rule: [genuine blocker, missing access, real ambiguity that risks data loss / security / external impact]

# Operating rules

- Inspect relevant files before claims about code.
- Reuse existing helpers, patterns, and tests before adding abstractions.
- Make focused edits that cover the root cause or requested behavior.
- Persist end-to-end within a single turn whenever feasible. Bias to action over clarification.
- Apply scope discipline: implement EXACTLY and ONLY what was requested.
- Continue through implementation and verification unless blocked by safety, missing access, or a real ambiguity.

# Tool policy

- Prefer dedicated tools over shell when a dedicated tool exists.
- Parallelize independent reads when the runtime supports it.
- Avoid hard-coded tool-call order unless the harness contract requires it.
- Confirm before destructive, irreversible, or production-impacting actions unless explicitly authorized.

# Verification

[Narrowest useful test/lint/build command]
[Manual inspection or acceptance check when tests are absent]
[For UI/agent flows, end-to-end check]

# Final response

- Files changed
- Validation run and results
- Residual risk and follow-ups
```

Notes for Codex:

- Best for coding-agent task prompts and durable coding-agent system prompts.
- Allow short preambles every 1-3 logical steps; hard floor every 6 steps or 10 tool calls. Routine progress preambles for non-interactive rollouts are wasteful.
- Avoid mandatory upfront plans, routine preambles, or hard-coded tool-call order unless the workflow requires them.
- Put tool-specific behavior in tool descriptions when building an API harness; keep the prompt focused on policy, safety, and done criteria.
- For long agentic rollouts beyond a single context window, instruct the agent to write a `claude-progress.txt` (or similar) at the end of each session and read it at the start of the next one. State that the file is structured and uses JSON when machine-read.

## Generic variant (Markdown-only)

```markdown
You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

## Outcome

- Result: [expected artifact or behavior]
- Done when: [observable criteria]
- Stop rule: [when to ask, abstain, or report blocked]

## Constraints

[Non-negotiable rules, stated positively]

## Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps only when order affects safety, correctness, or side effects]

## Output

[Format specification]
[Example of desired output shape if helpful]

## Examples

[Only when --examples is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]
```

Notes for generic:

- Works across model families.
- No XML tags (less reliable on non-Claude models).
- No recency-effect reminders (model-specific).
- No `reasoning_effort` / `effort` API guidance (target API may not expose these).
- Markdown is the safest cross-model format choice.

## Prompt-type inserts

Add these only when the prompt brief calls for them.

### Reusable template

```markdown
# Variables

- `{{variable_name}}`: [meaning, trust level, expected format]

# Input boundaries

[State which variables are untrusted data and how to treat missing values]
```

### Tool description

```markdown
Name: [tool_name] (use snake_case; namespace prefix when part of a suite, e.g. `asana_projects_search`)
Purpose: [what the tool does in one sentence]
Use when: [specific conditions]
Do not use when: [specific exclusions]
Inputs: [parameters with specific names like `user_id` not `user`, formats, caveats]
Returns: [fields and missing-value behavior; prefer semantic identifiers like `name` over `uuid`]
Side effects: [none/read/write/external action]
Retry safety: [safe/idempotent/unsafe]
Common errors: [what they mean and how to recover]
Examples: [1-5 calls covering minimal, partial, and full specification]
```

### Eval grader

```markdown
# Grading task

[What artifact or trace to judge]

# Allowed evidence

[Inputs the grader may use; explicitly forbid sources that bias the verdict]

# Labels

- `pass`: [observable criteria]
- `fail`: [observable criteria]
- `insufficient_evidence`: [when evidence is missing - never guess]

# Output

[Fixed JSON or label-only format]
[Confidence field if calibration matters: 0.0-1.0]
```

### Prompt improvement

```markdown
# Inputs

<current_prompt>
{{current_prompt}}
</current_prompt>

<failure_examples>
{{failure_examples}}
</failure_examples>

# Task

Identify the smallest prompt changes that address the failures while preserving variables and product behavior.
Group failures into clusters and patch the cluster, not individual cases.
Re-check that the revision does not create a new failure mode.
Return the revised prompt and a short change log tied to failure modes.
```

### Subagent briefing

```markdown
# Inputs

- Goal: [what the subagent must produce]
- Output format: [structured shape, file paths, line numbers when relevant]
- Tool guidance: [allowed tools, prohibited tools]
- Boundary: [what the subagent must not do]
- Files to read: [absolute paths]
- Errors observed so far: [verbatim]
- Prior decisions: [decisions the parent has already made]

# Task

[Specific scope - one task, not "look around"]

# Stop rule

[Return early when [observable signal]; do not exceed [budget]]
```

Subagent context starts empty - the parent must provide everything. Subagents return structured summaries, not raw transcripts. One-way communication: parent → child → parent. Never child → child.

### Three-agent harness (planner / generator / evaluator)

For multi-hour autonomous work. The evaluator owns a "sprint contract" - acceptance criteria the team agrees on before implementation. End-to-end verification (Playwright, integration tests) checks the contract.

```markdown
# Roles

- Planner: decompose into milestones, write the sprint contract.
- Generator: implement the next milestone end-to-end.
- Evaluator: run the verification, return pass / fail with evidence.

# Loop

- Plan one milestone.
- Generate.
- Evaluate.
- If fail, return to generator with the diff and the failing evidence.
- If pass, mark milestone done in progress file and continue.

# Stop conditions

- All milestones done.
- Real blocker requires human input.
- Budget or permissions prevent safe progress.
- Human pauses or redirects.
```

## Skeleton rules (all variants)

1. Identity section is exactly 2 lines: name + scope.
2. Outcome contract appears before procedural instructions for agentic prompts.
3. Constraints come before instructions.
4. Instructions are specific and actionable, not generic quality statements.
5. Output section defines format clearly.
6. Examples section appears only when needed (`--examples`, ambiguous format, edge cases, policy boundaries).
7. Token budget: task prompts under 500, system prompts under 1500.
8. No adjective stacking, no motivational language, no tipping or threats.
9. Positive framing: "Write in prose" not "Don't use markdown". Use "Do not" exception clauses inside positive directives only when restricting a specific behavior.
10. Avoid rigid process guidance when a goal, constraints, and verification contract are enough.
11. Audit for contradictions before returning - models silently drop conflicts.
12. Identity and the highest-priority constraint sit in the first ~200 tokens; verification and stop rules sit at the end.
