# Agent Quality Checklist

Binary checklist for evaluating agent definitions. Each check is pass/fail.

## Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements for agent definitions.

| ID  | Check                                                                          | Source                 |
|:----|:-------------------------------------------------------------------------------|:-----------------------|
| C1  | `name` is lowercase, kebab-case, descriptive                                   | Agent definition spec  |
| C2  | `description` has trigger keyword (PROACTIVELY/MUST BE USED/immediately after) | Agent definition spec  |
| C3  | `description` lists 2-3 trigger scenarios                                      | Agent definition spec  |
| C4  | `description` states value proposition                                         | Agent definition spec  |
| C5  | `tools` does NOT include `AskUserQuestion` (filtered from subagents)           | Agent definition spec  |
| C6  | Role statement is first line, specific domain, action-oriented                 | Output template        |
| C7  | Constraints section has NEVER and ALWAYS rules                                 | Output template        |
| C8  | Constraints includes uncertainty handling (`STATUS: NEEDS_INPUT`)              | Output template        |
| C9  | Output format is concrete structure with placeholders, not prose               | Output template        |
| C10 | Sections appear in required order (see Section Order below)                    | Output template        |
| C11 | No anti-patterns present (see Anti-Patterns below)                             | Quality best practices |

### How to evaluate

Read frontmatter first. Confirm `name` is kebab-case and `description` contains a trigger phrase plus scenarios. Verify `AskUserQuestion` is not in `tools`. Check the body for a role statement as the first line, constraints with NEVER/ALWAYS rules and uncertainty handling, and a concrete output format. Verify section ordering. Scan for anti-patterns listed below.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect agent quality.

| ID  | Check                                                              | Source                |
|:----|:-------------------------------------------------------------------|:----------------------|
| I1  | `tools` is minimal set for task (least privilege)                  | Agent definition spec |
| I2  | `model` is appropriate for complexity (haiku/sonnet/opus)          | Tool selection guide  |
| I3  | Expertise lists 3-5 concrete capabilities                          | Output template       |
| I4  | Constraints uses `**BOLD** --- em dash --- explanation` format     | Output template       |
| I5  | Workflow has numbered steps (3-7) with verification                | Output template       |
| I6  | Edge Cases covers: empty input, partial completion, multiple items | Output template       |
| I7  | Edge Cases has `STATUS: NEEDS_INPUT` pattern for uncertainty       | Output template       |
| I8  | Good example with `<example type="good">` and realistic I/O        | Output template       |
| I9  | Bad example with `<why_bad>` and `<correct>` tags                  | Output template       |
| I10 | Density Rules table showing bad vs good patterns                   | Output template       |
| I11 | Done When has 4-6 measurable criteria with checkboxes              | Output template       |

### How to evaluate

Check `tools` against actual agent capabilities — flag over-broad sets. Verify `model` matches complexity. Scan body sections for expertise depth, constraint formatting, workflow steps, edge case coverage, example quality, density rules, and measurable done-when criteria.

---

## Polish Checks

Informational findings. These do not affect the pass/fail verdict.

| ID  | Check                                               | Source            |
|:----|:----------------------------------------------------|:------------------|
| P1  | Description uses third-person form                  | Best practices    |
| P2  | Consistent terminology throughout                   | Best practices    |
| P3  | No placeholder text (`{something}`) in final output | Quality standards |

### How to evaluate

Confirm description uses third-person ("Analyzes code...") not second-person ("Helps you analyze..."). Check that the same concept uses the same term throughout. Scan for unresolved placeholder patterns.

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

## Anti-Patterns

| Anti-Pattern                | Detection                                                  |
|:----------------------------|:-----------------------------------------------------------|
| Vague role                  | "helpful assistant", "AI that helps", generic descriptions |
| Missing constraints         | No Constraints section or empty                            |
| Implicit assumptions        | Instructions that assume context not provided              |
| Placeholder text            | `{something}` patterns in final agent output               |
| Negative-only framing       | "don't X" without "do Y instead"                           |
| `AskUserQuestion` in tools  | Tool listed in frontmatter (filtered from subagents)       |
| Single-scenario description | Only one trigger scenario                                  |
| Value-less description      | No benefit/value proposition stated                        |
| Prose output format         | "Output a good document" instead of concrete structure     |
| Unmeasurable Done When      | "Task is complete" instead of specific criteria            |

## Verdict Logic

Any Critical fails              → FAIL
3+ Important fails              → NEEDS WORK
All Critical pass, ≤2 Important → PASS
Polish checks                   → informational only
