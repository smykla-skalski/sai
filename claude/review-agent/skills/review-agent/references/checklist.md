# Agent Quality Checklist

Binary checklist for evaluating Claude Code subagent definitions. Each check is pass/fail.

## Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)
- [Section Order](#section-order)
- [Anti-Patterns](#anti-patterns)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements for a functional subagent definition.

| ID  | Check                                                           | Source                         |
|:----|:----------------------------------------------------------------|:-------------------------------|
| C1  | Description has trigger keyword and lists 2-3 trigger scenarios | Agent Template, Best Practices |
| C2  | Description states value proposition                            | Agent Template, Best Practices |
| C3  | Constraints section exists and is non-empty                     | Agent Template                 |
| C4  | Workflow has numbered steps (3-7) with verification             | Agent Template                 |
| C5  | AskUserQuestion NOT in tools list                               | Subagent Architecture          |
| C6  | Role statement is first line, specific, action-oriented         | Agent Template, Best Practices |

### How to evaluate

Read the frontmatter `description` field. Confirm it contains at least one trigger phrase (e.g., "Use when...", "PROACTIVELY", "MUST BE USED", "immediately after") and lists 2-3 concrete scenarios. Verify it includes a clear value statement (what the user gains). Check that a Constraints section exists with at least one constraint. Count Workflow steps and confirm they are numbered (3-7 range) with at least one verification/validation step. Confirm `AskUserQuestion` does not appear in the `tools` frontmatter field. Verify the first line after frontmatter is a specific, action-oriented role statement — not a generic "helpful assistant" phrase.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect agent quality.

| ID  | Check                                                           | Source                         |
|:----|:----------------------------------------------------------------|:-------------------------------|
| I1  | name is lowercase, kebab-case, descriptive                      | Agent Template                 |
| I2  | tools is minimal set (least privilege)                          | Best Practices                 |
| I3  | model appropriate for complexity (haiku/sonnet/opus)            | Best Practices                 |
| I4  | Constraints uses bold+em-dash format with NEVER/ALWAYS keywords | Agent Template                 |
| I5  | Constraints includes uncertainty handling (STATUS: NEEDS_INPUT) | Agent Template                 |
| I6  | Edge Cases covers standard scenarios                            | Agent Template                 |
| I7  | Output Format uses concrete structure, not prose                | Agent Template, Best Practices |
| I8  | Examples include good and bad with proper tags                  | Agent Template                 |
| I9  | Done When has 4-6 measurable criteria with checkboxes           | Agent Template                 |
| I10 | Sections appear in correct order                                | Agent Template                 |

### How to evaluate

Confirm the `name` field is lowercase kebab-case and descriptive of the agent's function. Compare the `tools` list against actual tool usage in the body — flag tools listed but never used. Check `model` matches complexity (haiku for simple tasks, sonnet for moderate, opus for complex reasoning). Scan Constraints for `**BOLD** — em dash — explanation` format and NEVER/ALWAYS/ZERO/MAXIMUM keywords. Verify Constraints include an uncertainty handling pattern (`STATUS: NEEDS_INPUT` or equivalent). Check Edge Cases covers: empty input, partial completion, multiple items, uncertainty. Verify Output Format has concrete structure with placeholders, not prose descriptions like "output a good document." Look for `<example type="good">` and `<example type="bad">` with `<why_bad>` and `<correct>` tags. Count Done When criteria (expect 4-6) and confirm each is measurable with checkbox format. Verify sections follow the order in the Section Order reference below.

---

## Polish Checks

Informational findings. These do not affect the pass/fail verdict.

| ID  | Check                                           | Source         |
|:----|:------------------------------------------------|:---------------|
| P1  | Expertise section has 3-5 concrete capabilities | Agent Template |
| P2  | Density Rules table present                     | Best Practices |
| P3  | Modes of Operation when applicable              | Agent Template |
| P4  | Decision Tree when applicable                   | Agent Template |
| P5  | No negative-only framing                        | Best Practices |

### How to evaluate

Check the Expertise section lists 3-5 concrete, specific capabilities (not vague generalities). Look for a Density Rules table if the agent produces text output. If the agent has 2+ distinct operational modes, verify a Modes of Operation section exists. If the workflow has complex conditional logic, verify a Decision Tree section exists. Scan for "don't X" patterns without a corresponding "do Y instead" alternative.

---

## Section Order

Sections MUST appear in this order (omit sections that don't apply):

1. Frontmatter (`---`)
2. Role Statement (first line)
3. Expertise
4. Modes of Operation
5. Constraints
6. Workflow
7. Decision Tree
8. Edge Cases
9. Output Format
10. Examples
11. Density Rules
12. Done When
13. Output (STATUS blocks)

---

## Anti-Patterns

| Anti-Pattern                | Detection                                                  | Severity  |
|:----------------------------|:-----------------------------------------------------------|:----------|
| Vague role                  | "helpful assistant", "AI that helps", generic descriptions | Critical  |
| Missing constraints         | No Constraints section or empty                            | Critical  |
| AskUserQuestion in tools    | Tool listed in frontmatter (filtered from subagents)       | Critical  |
| Single-scenario description | Only one trigger scenario                                  | Critical  |
| Value-less description      | No benefit/value proposition stated                        | Critical  |
| Implicit assumptions        | Instructions that assume context not provided              | Important |
| Placeholder text            | `{something}` patterns in final agent output               | Important |
| Negative-only framing       | "don't X" without "do Y instead"                           | Important |
| Prose output format         | "Output a good document" instead of concrete structure     | Important |
| Unmeasurable Done When      | "Task is complete" instead of specific criteria            | Important |
