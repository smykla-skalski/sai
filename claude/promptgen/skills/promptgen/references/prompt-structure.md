# Prompt structure templates

Three template variants the skill fills in during generation. Choose based on `--for` flag.

# Contents

- [Claude variant (XML tags)](#claude-variant-xml-tags)
- [GPT variant (final reminders)](#gpt-variant-final-reminders)
- [Codex variant (coding agent)](#codex-variant-coding-agent)
- [Generic variant (Markdown-only)](#generic-variant-markdown-only)
- [Prompt-type inserts](#prompt-type-inserts)
- [Skeleton rules (all variants)](#skeleton-rules-all-variants)

## Claude variant (XML tags)

```xml
You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

<constraints>
[Non-negotiable rules, stated positively]
</constraints>

<instructions>
[Specific, actionable instructions organized by priority]
[Numbered steps only when order matters]
</instructions>

<output>
[Format specification]
[Example of desired output shape if helpful]
</output>

<examples>
[Only if --examples flag is set]
<example>
<input>[Representative input]</input>
<response>[Desired output matching all constraints]</response>
</example>
</examples>
```

Notes for Claude:
- XML tags are native and well-supported for data boundaries
- Markdown headers work for section organization within tags
- Put longform data at the top, queries at the end
- Don't use anti-laziness prompts or aggressive emphasis
- Soften tool-use language: "Use [tool] when it would help" not "You must use [tool]"
- For Claude 4.6+, prefer adaptive thinking and effort controls over manual thinking budgets or prefilled assistant responses

## GPT variant (final reminders)

```markdown
# Role and objective

You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

# Outcome contract

[Expected result]
[Success criteria]
[Allowed side effects and evidence rules]

# Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps only when order matters]

## [Sub-category if needed]

[Detailed instructions for specific areas]

# Output format

[Format specification]
[Example of desired output shape if helpful]

# Examples

[Only if --examples flag is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]

# Important reminders

[Repeat the 1-2 most critical constraints here - exploits recency effect]
[GPT-4.1+ follows instructions closer to the end more closely]
```

Notes for GPT:
- Markdown headers (H1-H4) for sections
- Place 1-2 final reminders at the end only when they carry real priority
- GPT-5.5-style reasoning models need outcome-first prompts: goal, constraints, output contract, and verification; avoid rigid process scripts unless the path matters
- Put stable prompt text before dynamic variables for caching when this is a production prompt
- Use API structured outputs instead of long prompt-written schemas when available

## Codex variant (coding agent)

```markdown
You are [Name], a coding agent working in the user's repository.
[1-sentence scope/purpose].

# Outcome contract

[Expected result]
[Acceptance criteria]
[Allowed side effects: files, commands, commits, network, external systems]
[Evidence required before final response]

# Operating rules

- Inspect relevant files before making claims about code.
- Follow existing project conventions and reuse local helpers before adding new ones.
- Make focused edits that cover the root cause or requested behavior.
- Continue through implementation and verification unless blocked by safety, missing access, or a real ambiguity.
- Ask for help only when a reasonable assumption would risk data loss, security, or incorrect external action.

# Tool policy

- Use search/read tools to gather context before editing.
- Parallelize independent reads when the runtime supports it.
- Prefer dedicated tools over shell commands when a dedicated tool exists.
- Confirm before destructive, irreversible, or production-impacting actions unless explicitly authorized.

# Verification

[Narrow test/lint/build command or validation method]
[Manual inspection or acceptance check]

# Final response

[Concise summary shape: changed files, validation, remaining risk]
```

Notes for Codex:
- Best for coding-agent task prompts and durable coding-agent system prompts
- Include autonomy and persistence, but keep side-effect and stop rules explicit
- Avoid mandatory upfront plans, routine preambles, or hard-coded tool-call order unless the workflow requires them
- Put tool-specific behavior in tool descriptions when building an API harness; keep the prompt focused on policy, safety, and done criteria

## Generic variant (Markdown-only)

```markdown
You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

## Constraints

[Non-negotiable rules, stated positively]

## Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps only when order matters]

## Output

[Format specification]
[Example of desired output shape if helpful]

## Examples

[Only if --examples flag is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]
```

Notes for generic:
- Works across model families
- No XML tags (less reliable on non-Claude models)
- No recency-effect reminders (model-specific optimization)
- Markdown is the safest cross-model format choice

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
Name: [tool_name]
Purpose: [what the tool does]
Use when: [specific conditions]
Do not use when: [specific exclusions]
Inputs: [parameters, formats, caveats]
Returns: [fields and missing-value behavior]
Side effects: [none/read/write/external action]
Retry safety: [safe/idempotent/unsafe]
Common errors: [what they mean]
```

### Eval grader

```markdown
# Grading task

[What artifact or trace to judge]

# Allowed evidence

[Inputs the grader may use]

# Labels

- `pass`: [observable criteria]
- `fail`: [observable criteria]
- `insufficient_evidence`: [when evidence is missing]

# Output

[Fixed JSON or label-only format]
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
Return the revised prompt and a short change log tied to failure modes.
```

## Skeleton rules (all variants)

1. Identity section is exactly 2 lines: name + scope
2. Outcome contract appears before procedural instructions for agentic prompts
3. Constraints come before instructions
4. Instructions are specific and actionable, not generic quality statements
5. Output section defines format clearly
6. Examples section only appears with `--examples`
7. Token budget: task prompts under 500, system prompts under 1500
8. No adjective stacking, no motivational language, no tipping
9. Positive framing: "Write in prose" not "Don't use markdown"
10. Avoid rigid process guidance when a goal, constraints, and verification contract are enough
