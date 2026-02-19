# Review Checklist

Binary checklist for evaluating Claude Code skill definitions. Each check is pass/fail.

## Table of Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)

---

## Critical Checks

Any single failure in this tier results in an overall **FAIL** verdict. These represent hard requirements from the Agent Skills specification and Anthropic best practices.

| ID  | Check                                                                         | Source                                       |
|:----|:------------------------------------------------------------------------------|:---------------------------------------------|
| C1  | Description includes what the skill does AND when-to-use trigger phrases      | Anthropic Best Practices, Agent Skills Spec  |
| C2  | SKILL.md body under 500 lines (excluding frontmatter)                         | Agent Skills Spec, Claude Code Docs          |
| C3  | All file references in SKILL.md resolve to actual files                       | Agent Skills Spec                            |
| C4  | Name field valid format and matches directory name                            | Agent Skills Spec                            |
| C5  | No generic content Claude already knows ("write clean code", "handle errors") | Anthropic skill-creator, Context Engineering |

### How to evaluate

Read the SKILL.md frontmatter first. Confirm the `description` field contains both a functional summary and at least one trigger phrase (e.g., "Use when..."). Count body lines excluding the YAML frontmatter block and verify < 500. Grep for file paths referenced in the body and confirm each resolves relative to the skill directory. Verify the `name` field is kebab-case and matches the parent directory name exactly. Scan for filler instructions that restate LLM defaults — if removing a sentence changes nothing about behavior, it fails C5.

---

## Important Checks

Three or more failures in this tier results in a **NEEDS WORK** verdict. These reflect best practices that materially affect skill quality.

| ID  | Check                                                                               | Source                                        |
|:----|:------------------------------------------------------------------------------------|:----------------------------------------------|
| I1  | Imperative form throughout ("Parse input" not "You should parse")                   | Anthropic skill-creator                       |
| I2  | Progressive disclosure — complex skills use references/ for details                 | Agent Skills Spec, Context Engineering        |
| I3  | Concrete examples showing inputs → outputs                                          | Anthropic Best Practices, Context Engineering |
| I4  | No content duplication between SKILL.md and references                              | Anthropic skill-creator                       |
| I5  | Explicit read directives for workflow-critical references ("Read X before phase Y") | Empirical finding                             |
| I6  | Scripts invoked via `bash "$SKILL_DIR/scripts/..."` (not ./scripts/)                | Empirical: plugin cache strips execute bits   |
| I7  | Appropriate degrees of freedom (guardrails match task fragility)                    | Anthropic Best Practices                      |
| I8  | Feedback loops for quality-critical steps                                           | Anthropic Best Practices                      |
| I9  | allowed-tools not over-broad (only tools actually needed)                           | Anthropic Best Practices                      |
| I10 | Consistent terminology (same concept = same word)                                   | Anthropic Best Practices                      |
| I11 | Persistent state uses XDG paths, not relative or cache-relative paths               | SAI Convention, Plugin Cache Architecture     |

### How to evaluate

Scan the SKILL.md body for second-person phrasing ("you should", "you can") — every instruction should be imperative. Check whether the SKILL.md exceeds ~150 lines; if so, verify that detail-heavy sections (examples, search patterns, rubrics) are extracted to references/. Look for at least one concrete input → output example. Diff the SKILL.md against each reference file for duplicated paragraphs or tables. Verify that any reference file used during execution has an explicit "Read references/X before Phase N" directive. Check script invocations use `bash "$SKILL_DIR/scripts/..."`. Compare the `allowed-tools` list against actual tool usage in the body — flag tools listed but never used. Confirm the same concept uses the same term throughout (e.g., don't alternate between "score" and "grade"). If the skill writes persistent state or artifacts (state files, generated output, tracking files), verify it uses `${XDG_DATA_HOME:-$HOME/.local/share}/sai/{plugin-name}/` — not `./findings/`, `$SKILL_DIR/findings/`, or any relative path. Plugin cache directories are replaced on version updates; relative paths are ambiguous and may resolve to the cache.

---

## Polish Checks

Informational findings. These are only scored when running with `--thorough` and do not affect the pass/fail verdict.

| ID  | Check                                               | Source                   |
|:----|:----------------------------------------------------|:-------------------------|
| P1  | Long references (>100 lines) have table of contents | Agent Skills Spec        |
| P2  | One default + one escape hatch (not five options)   | Anthropic Best Practices |
| P3  | SKILL.md mentions all bundled resources             | Agent Skills Spec        |
| P4  | No time-sensitive info without deprecation plan     | Anthropic skill-creator  |
| P5  | Description uses third-person form                  | Anthropic Best Practices |

### How to evaluate

Count lines in each reference file — any over 100 lines should start with a TOC linking to its sections. For option-heavy instructions, verify there is one clear default path and at most one alternative, not a menu of choices. Cross-reference the skill directory listing against mentions in SKILL.md — every file should be referenced at least once. Flag hardcoded dates, version numbers, or URLs without a note on when to update them. Confirm the `description` frontmatter uses third-person ("Aggregates daily news...") rather than second-person ("Helps you aggregate...").
