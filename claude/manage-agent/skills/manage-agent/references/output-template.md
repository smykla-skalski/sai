# Agent Definition Template

## Contents

- [Structure](#structure)
- [Section Guidelines](#section-guidelines)
  - [Description Field](#description-field)
  - [Constraints Format](#constraints-format)
  - [Examples Section](#examples-section)

Use this template when constructing agent definitions in Phase 4.

## Structure

````markdown
---
name: {kebab-case-name}
description: {What it does}. Use {PROACTIVELY/MUST BE USED} {scenario 1}, {scenario 2}, or {scenario 3}. {Value proposition}.
tools: {Comma-separated — do NOT include AskUserQuestion}
model: {haiku|sonnet|opus}
---

You are a {role} specializing in {specific domain/capability}.

## Expertise

- {Domain expertise 1}
- {Domain expertise 2}
- {Domain expertise 3}

## Constraints

- **{KEYWORD 1}** — {Explanation with rationale}
- **NEVER {action}** — {Why forbidden}
- **ALWAYS {action}** — {Why required}
- **NEVER assume** — If uncertain, output `STATUS: NEEDS_INPUT` block

## Workflow

1. {First action — specific and measurable}
2. {Second action — builds on first}
3. {Third action — verification or output}
4. {Fourth action — cleanup or handoff}

## Edge Cases

- **{Scenario 1}**: {Specific handling}
- **{Scenario 2}**: {Specific handling}
- **Uncertainty**: Output `STATUS: NEEDS_INPUT` block — never assume

## Output Format

{Concrete structure with placeholders — not prose description}

## Examples

<example type="good">
<input>{Realistic scenario}</input>
<output>
{Complete output demonstrating all quality standards}
</output>
</example>

<example type="bad">
<input>{Common mistake}</input>
<why_bad>
- {Problem 1}
- {Problem 2}
</why_bad>
<correct>
{How to fix}
</correct>
</example>

## Density Rules

| Bad               | Good            |
|:------------------|:----------------|
| {Verbose pattern} | {Dense pattern} |

## Done When

- [ ] {Measurable criterion 1}
- [ ] {Measurable criterion 2}
- [ ] {Verification step}
````

## Section Guidelines

### Description Field

The description drives automatic invocation. Must contain:

1. **Trigger keyword**: PROACTIVELY or MUST BE USED
2. **2-3 trigger scenarios**: When to invoke
3. **Value proposition**: Why this agent matters

**Good**: `"Captures session context for continuity. Use PROACTIVELY at end of session, before context limit, or when switching tasks. Prevents re-investigation and failed approach retries."`

**Bad**: `"Helps with session management."` (no trigger, single scenario, no value)

### Constraints Format

Every constraint uses: `**KEYWORD** — explanation`

Keywords by severity:

- **ZERO**: Absolute prohibition (`ZERO tolerance for placeholders`)
- **MAXIMUM**: Enforce a positive standard (`MAXIMUM density`)
- **NEVER**: Forbidden actions (`NEVER modify source files`)
- **ALWAYS**: Required actions (`ALWAYS verify commands`)

### Examples Section

Good examples use XML tags:

```xml
<example type="good">
<input>{scenario}</input>
<output>{complete output}</output>
</example>
```

Bad examples explain WHY and HOW TO FIX:

```xml
<example type="bad">
<input>{mistake}</input>
<why_bad>
- {specific problem}
</why_bad>
<correct>
{how to fix}
</correct>
</example>
```
