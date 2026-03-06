# Review Examples

Good vs bad patterns for skill evaluation.

## Contents

- [Descriptions](#descriptions)
- [Progressive Disclosure](#progressive-disclosure)
- [Imperative Form](#imperative-form)
- [Read Directives](#read-directives)
- [Script Invocation](#script-invocation)
- [Degrees of Freedom](#degrees-of-freedom)
- [Secrets and credentials](#secrets-and-credentials)
- [Useless echo in code blocks](#useless-echo-in-code-blocks)
- [Duplicated code blocks](#duplicated-code-blocks)
- [Phase numbering consistency](#phase-numbering-consistency)
- [Grading Style](#grading-style)

---

## Descriptions

**Good** — includes what + when:
> Aggregate daily AI news from research papers, tech blogs, and newsletters into a structured digest. Use when running a daily or weekly AI news roundup.

**Bad** — vague, no triggers:
> Helps with AI news stuff.

**Good** — third-person with trigger:
> Review and fix Claude Code skill definitions using a tiered binary checklist. Use when auditing, improving, or validating any skill before publishing.

**Bad** — second-person, no trigger:
> You can use this to check your skills.

---

## Progressive Disclosure

**Good** — core workflow in SKILL.md (~30 lines), details in references/:

```text
## Workflow
### Phase 3: Research
Read references/sources.md in full before starting this phase.
For each source category, run the search queries listed...
```

**Bad** — everything embedded inline in a 400-line SKILL.md:

```text
## Workflow
### Phase 3: Research
Search for "site:arxiv.org transformer attention 2025"
Search for "site:openai.com blog 2025"
... (50 more lines of queries)
```

---

## Imperative Form

**Good**:
> Parse the `--format` flag. Default to markdown.

**Bad**:
> You should check if the user passed a `--format` flag and then you should default to markdown if they didn't.

---

## Read Directives

**Good** — explicit instruction:
> Read `references/sources.md` in full before starting Phase 3.

**Bad** — passive pointer the agent may skip:
> Search patterns are available in `references/sources.md`.

---

## Script Invocation

**Good** — direct execution with `$SKILL_DIR` prefix and executable bit set:

```bash
"$SKILL_DIR/scripts/validate.sh" "$TARGET"
```

**Bad** — `bash` prefix (scripts must have executable bit, no `bash` needed):

```bash
bash "$SKILL_DIR/scripts/validate.sh" "$TARGET"
```

**Bad** — bare path without `$SKILL_DIR`:

```bash
./scripts/validate.sh "$TARGET"
```

---

## Degrees of Freedom

**Good** — one default + escape hatch:
> Output as markdown. Pass `--format json` for machine-readable output.

**Bad** — menu of choices:
> Output as markdown, JSON, YAML, HTML, or plain text. Choose whichever format best suits your needs.

---

## Secrets and credentials

**Good** — uses environment variables:

```text
## Authentication
Use the API key from the OPENAI_API_KEY environment variable.
```

**Bad** — hardcoded secret:

```text
## Authentication
Use API key: sk-1234567890abcdef1234567890abcdef
```

---

## Useless echo in code blocks

**Good** — direct variable assignment:

```bash
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sai/my-plugin"
```

**Bad** — unnecessary subshell via echo (ShellCheck SC2116):

```bash
DATA_DIR="$(echo "${XDG_DATA_HOME:-$HOME/.local/share}/sai/my-plugin")"
```

---

## Duplicated code blocks

**Good** — SKILL.md has the code, reference cross-references it:

```text
## In SKILL.md Phase 2:
"$SKILL_DIR/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1

## In references/workflow.md Phase 2:
Use the cluster-lifecycle.sh invocation from SKILL.md Phase 2.
```

**Bad** — same code block copied to both files:

```text
## In SKILL.md Phase 2:
"$SKILL_DIR/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1

## In references/workflow.md Phase 2:
"$SKILL_DIR/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1
```

---

## Phase numbering consistency

**Good** — same phase numbers in SKILL.md and references:

```text
## SKILL.md:
### Phase 0: Setup
### Phase 1: Execute
### Phase 2: Report

## references/workflow.md:
## Phase 0 - setup
## Phase 1 - execute
## Phase 2 - report
```

**Bad** — different numbering for the same workflow:

```text
## SKILL.md:
### Phase 0: Environment
### Phase 1: Initialize
### Phase 2: Execute

## references/workflow.md:
## Phase 0 - initialize (combines SKILL.md 0+1)
## Phase 1 - execute (off by one from SKILL.md)
```

---

## Grading Style

**Good** — imperative workflow with concrete actions:

```text
### Phase 2: Analyze
Check each function for:
1. Missing error handling on external calls
2. Hardcoded credentials or secrets
3. SQL queries built from string concatenation

List each issue with file path, line number, and suggested fix.
```

**Bad** — scoring rubric with points and grades:

```text
### Evaluation Criteria
| Criterion   | Weight | Score Range |
|:------------|:-------|:------------|
| Readability | 30%    | 1-5         |
| Performance | 25%    | 1-5         |

Grade A (90-100%): Excellent code quality.
Grade B (80-89%): Good with minor issues.
```
