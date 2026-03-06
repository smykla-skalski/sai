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

**Good** — explicit gate with purpose (RG-GATE + RG-PURPOSE):
> Read [references/sources.md](references/sources.md) in full before starting Phase 3.

**Bad** — passive pointer the agent may skip (RG-PASSIVE):
> Search patterns are available in [references/sources.md](references/sources.md).

**Bad** — gate without purpose (RG-PURPOSE):
> Read [references/sources.md](references/sources.md).

**Bad** — use before gate (RG-ORDER):

```text
## Pattern categories
Full pattern descriptions are in [references/patterns.md](references/patterns.md).
...
## Workflow
### Phase 2: Pattern scan
Read [references/patterns.md](references/patterns.md) in full before scanning.
```

The passive mention at "Pattern categories" comes before the gate at Phase 2. Move the gate above or remove the early mention.

**Bad** — multi-flow missing gate (RG-FLOW):

```text
## Workflow - generate mode
Read [references/suite-structure.md](references/suite-structure.md) for the format spec.
...
## Workflow - wizard mode
Show the group structure from [references/suite-structure.md](references/suite-structure.md).
```

The reference is gated in generate mode but only passively mentioned in wizard mode. Each flow needs its own gate.

---

## Script Invocation

**Good** — direct execution with `${CLAUDE_SKILL_DIR}` prefix and executable bit set:

```bash
"${CLAUDE_SKILL_DIR}/scripts/validate.sh" "$TARGET"
```

**Bad** — `bash` prefix (scripts must have executable bit, no `bash` needed):

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/validate.sh" "$TARGET"
```

**Bad** — bare path without `${CLAUDE_SKILL_DIR}`:

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

Only flag `$(echo ...)` wrapping literal strings. Do NOT flag `$(echo "${VAR}")` because
in a skills context the agent interprets code blocks as intent descriptions and the
subshell wrapper can affect agent behavior ([GitHub #23813](https://github.com/anthropics/claude-code/issues/23813)).

**Good** — direct literal assignment:

```bash
DATA_DIR="/opt/sai/my-plugin"
```

**Bad** — useless echo wrapping a literal (SC2116):

```bash
DATA_DIR="$(echo "/opt/sai/my-plugin")"
```

**OK** — echo wrapping a variable expansion (acceptable in skills):

```bash
DATA_DIR="$(echo "${XDG_DATA_HOME:-$HOME/.local/share}/sai/my-plugin")"
```

---

## Duplicated code blocks

Progressive disclosure means reference files are loaded independently from SKILL.md
([Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)).
Each file should be self-contained — duplicating low-freedom operational code blocks is
often correct because the agent needs them wherever it looks. Cross-references like
"Use the X from SKILL.md Phase N" are fragile because the agent may not follow them.

**Good** — both files have the code block (self-contained):

```text
## In SKILL.md Phase 2:
"${CLAUDE_SKILL_DIR}/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1

## In references/workflow.md Phase 2:
"${CLAUDE_SKILL_DIR}/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1
```

**Bad** — cross-reference the agent might not follow:

```text
## In SKILL.md Phase 2:
"${CLAUDE_SKILL_DIR}/scripts/cluster-lifecycle.sh" --repo-root "${REPO_ROOT}" single-up kuma-1

## In references/workflow.md Phase 2:
Use the cluster-lifecycle.sh invocation from SKILL.md Phase 2.
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

## Fork candidate (context: fork)

**Good** — self-contained multi-phase skill with structured output, isolation benefits:

```yaml
---
name: ai-daily-digest
context: fork
agent: Explore
allowed-tools: WebSearch, WebFetch, Read, Write, Bash
---
```

Signals: 5+ phases, structured output template, WebSearch data gathering, self-contained $ARGUMENTS input.

**Not a candidate** — conversation-dependent skill:

```yaml
---
name: promptgen
# No context: fork — skill reads conversation history
allowed-tools: Read, Write, Task
---
```

Blocked: body references "conversation history" — fork subagents have no conversation history.

**Not a candidate** — side-effect git tool:

```yaml
---
name: stage-hunk
disable-model-invocation: true
# No context: fork — user needs real-time visibility during staging
allowed-tools: Bash, AskUserQuestion
---
```

Counter-signal N1 reduces effective score below threshold. Side-effect skills need real-time user control.

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
