# Prompt structure templates

Three template variants the skill fills in during generation. Choose based on `--for` flag.

# Contents

- [Claude variant (XML tags)](#claude-variant-xml-tags)
- [GPT variant (final reminders)](#gpt-variant-final-reminders)
- [Generic variant (Markdown-only)](#generic-variant-markdown-only)
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
[Numbered steps for multi-step workflows]
</instructions>

<output>
[Format specification]
[Example of desired output shape if helpful]
</output>

<examples>
[Only if --with-examples flag is set]
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

## GPT variant (final reminders)

```markdown
# Role and objective

You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

# Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps for multi-step workflows]

## [Sub-category if needed]

[Detailed instructions for specific areas]

# Output format

[Format specification]
[Example of desired output shape if helpful]

# Examples

[Only if --with-examples flag is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]

# Important reminders

[Repeat the 1-2 most critical constraints here - exploits recency effect]
[GPT-4.1+ follows instructions closer to the end more closely]
```

Notes for GPT:
- Markdown headers (H1-H4) for sections
- Place final instructions at the end for recency effect
- GPT-5+ needs less scaffolding - keep instructions shorter
- Contradictory instructions impair GPT-5 reasoning more than prior models
- Follows instructions more literally than predecessors

## Generic variant (Markdown-only)

```markdown
You are [Name], [1-sentence factual description].
[1-sentence scope/purpose].

## Constraints

[Non-negotiable rules, stated positively]

## Instructions

[Specific, actionable instructions organized by priority]
[Numbered steps for multi-step workflows]

## Output

[Format specification]
[Example of desired output shape if helpful]

## Examples

[Only if --with-examples flag is set]

**Input:** [Representative input]
**Output:** [Desired output matching all constraints]
```

Notes for generic:
- Works across model families
- No XML tags (less reliable on non-Claude models)
- No recency-effect reminders (model-specific optimization)
- Markdown is the safest cross-model format choice

## Skeleton rules (all variants)

1. Identity section is exactly 2 lines: name + scope
2. Constraints come before instructions (models attend to earlier content more)
3. Instructions are specific and actionable, not generic quality statements
4. Output section defines format clearly
5. Examples section only appears with `--with-examples`
6. Token budget: task prompts under 500, system prompts under 1500
7. No adjective stacking, no motivational language, no tipping
8. Positive framing: "Write in prose" not "Don't use markdown"
