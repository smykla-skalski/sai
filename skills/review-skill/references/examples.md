# Review Examples

Good vs bad patterns for skill evaluation.

## Contents

- [Descriptions](#descriptions)
- [Progressive Disclosure](#progressive-disclosure)
- [Imperative Form](#imperative-form)
- [Read Directives](#read-directives)
- [Script Invocation](#script-invocation)
- [Degrees of Freedom](#degrees-of-freedom)

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

**Good** — uses `bash` (survives plugin cache):

```bash
bash "$SKILL_DIR/scripts/validate.sh" "$TARGET"
```

**Bad** — direct execution (breaks when execute bits are stripped):

```bash
./scripts/validate.sh "$TARGET"
```

---

## Degrees of Freedom

**Good** — one default + escape hatch:
> Output as markdown. Pass `--format json` for machine-readable output.

**Bad** — menu of choices:
> Output as markdown, JSON, YAML, HTML, or plain text. Choose whichever format best suits your needs.
