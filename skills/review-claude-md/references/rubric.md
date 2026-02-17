# Review Rubric — Tiered Binary Checklist

## Contents

- [Critical Checks](#critical-checks)
- [Important Checks](#important-checks)
- [Polish Checks](#polish-checks)
- [Verdict Logic](#verdict-logic)

---

## Critical Checks

**Rule: Must pass ALL — any single fail = FAIL verdict.**

| ID  | Check                                                             | Source                                  |
|:----|:------------------------------------------------------------------|:----------------------------------------|
| C1  | Build, test, and lint commands present and correct                | Builder.io, Official Best Practices     |
| C2  | Root CLAUDE.md under 150 lines                                    | HumanLayer, Community Meta-analysis     |
| C3  | No generic advice Claude already knows (e.g., "write clean code") | Official Best Practices                 |
| C4  | No README content duplication                                     | Official Best Practices, Anthropic Blog |

**How to evaluate:** Run each command listed to verify correctness. Count lines with `wc -l`. For C3 and C4, read every line and ask: "Would Claude behave differently without this?" If not, it fails C3. Compare against README section by section for C4.

---

## Important Checks

**Rule: 3 or more fails = NEEDS WORK verdict.**

| ID  | Check                                                            | Source                            |
|:----|:-----------------------------------------------------------------|:----------------------------------|
| I1  | Architecture describes component relationships (not just a tree) | HumanLayer                        |
| I2  | Domain terminology mapped to code concepts                       | HumanLayer                        |
| I3  | At least 2 project-specific, non-obvious gotchas                 | Arize                             |
| I4  | Test framework and conventions documented                        | Builder.io                        |
| I5  | Pre-commit workflow documented                                   | Builder.io                        |
| I6  | Bullets over paragraphs throughout                               | Official Best Practices, Maxitect |
| I7  | Pointers over copies (file:line refs, not embedded code blocks)  | HumanLayer                        |
| I8  | Style rules only where they differ from language defaults        | Official Best Practices           |
| I9  | Modularized with `.claude/rules/` if root file is complex        | Official Memory Docs              |

**How to evaluate:** For I1, check that the architecture section explains how components interact, not just where files live. For I3, gotchas must be specific to this project — "always run migrations before tests" qualifies, "handle errors gracefully" does not. For I7, flag any embedded code block over 5 lines that could be replaced with a file reference.

---

## Polish Checks

**Rule: Informational only. Reported when `--thorough` is passed. Do not affect verdict.**

| ID  | Check                                                             | Source             |
|:----|:------------------------------------------------------------------|:-------------------|
| P1  | Single-test / focused-test command available                      | Builder.io         |
| P2  | Mock strategy documented (hand-written vs generated, location)    | Community practice |
| P3  | Integration test requirements documented (Docker, env vars, etc.) | Community practice |
| P4  | Cross-system dependencies documented (IPC contracts, schemas)     | Community practice |
| P5  | Commit message format with examples                               | Community practice |

**How to evaluate:** These are quality-of-life improvements. Report each as `[INFO]` with a concrete suggestion. Do not let polish items influence the overall verdict.

---

## Verdict Logic

| Condition                                      | Verdict        |
|:-----------------------------------------------|:---------------|
| Any Critical check fails                       | **FAIL**       |
| 3+ Important checks fail                       | **NEEDS WORK** |
| All Critical pass, fewer than 3 Important fail | **PASS**       |
