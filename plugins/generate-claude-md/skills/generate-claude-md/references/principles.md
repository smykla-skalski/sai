# CLAUDE.md Generation Principles

The rules a generated CLAUDE.md must follow, with the evidence behind each.
Apply every rule during synthesis. These mirror what the `review-claude-md`
plugin audits against, so a file built to these principles passes that audit.

## Contents

- [The one test that governs everything](#the-one-test-that-governs-everything)
- [What goes in (priority order)](#what-goes-in-priority-order)
- [What stays out](#what-stays-out)
- [How to write each line](#how-to-write-each-line)
- [Length budget](#length-budget)
- [Sources](#sources)

---

## The one test that governs everything

For every candidate line, ask: **"Would removing this cause Claude to make a
mistake?"** If no, cut it. This is the official pruning test and the single most
important rule — bloat causes Claude to ignore the instructions that matter.
(Anthropic Best Practices)

A CLAUDE.md is **AI-operational context, not human onboarding docs**. It exists
to encode the deltas a model cannot infer from the code: exact commands, hidden
constraints, enforced boundaries, domain mappings. Everything else is noise.

---

## What goes in (priority order)

Order matters — models follow early instructions more reliably than mid-file
ones ("lost in the middle"). Put the highest-value, most-violated rules first.

1. **One-line project identity** — only if not obvious from the name. Often skip.
2. **Commands** (highest value): exact build / test / lint / run / single-test
   invocations with real flags. These are what Claude cannot guess and what it
   needs every session. (Builder.io, Anthropic) Empirically the most common and
   most useful section (Build/Run ~62–77% of real files; Santos et al., Agent
   READMEs study).
3. **Architecture map**: how components relate and what boundaries are enforced
   — not a directory tree. "Services never import handlers." Data flow in one
   line. Point to the one entry point that matters with `file:line`. (HumanLayer)
4. **Code-style deltas**: only conventions that differ from the language default,
   and point at the config file rather than restating its rules. (Anthropic)
5. **Testing**: framework, how to run one test, what to mock, fixtures/teardown
   requirements. (Builder.io)
6. **Repo etiquette**: branch/PR/commit conventions the project actually enforces.
7. **Gotchas**: project-specific traps with `file:line` — test ordering, required
   migrations, eventual consistency, env vars that must be set. (Arize)
8. **Security / file boundaries**: paths never to touch, generated files, secrets
   handling — only if real for this repo.

A section earns its place only if it has real, project-specific content. Omit any
section you would have to fill with generic filler.

---

## What stays out

The official exclude-list (Anthropic Best Practices), plus empirically-confirmed
anti-patterns:

- **Anything Claude can read from the code.** No file-by-file descriptions.
- **No directory tree / file enumeration** — provides no measured navigation
  benefit and burns the attention budget. Give a map, not a listing.
- **No README duplication.** LLM-generated files that duplicate README content
  measurably *lower* task success (~−2%) and raise cost (~+23%). (AGENTS.md
  efficiency study; Augment Code) Reference the README, don't restate it.
- **No standard language conventions** Claude already knows (PEP 8, gofmt, etc.).
- **No self-evident advice** ("write clean code", "handle errors gracefully",
  "make sure tests pass"). Claude already knows this; it only adds noise.
- **No embedded code snippets** that will rot — use `file:line` pointers instead.
- **No detailed API docs, tutorials, or long prose** — link out instead.
- **No secrets, credentials, connection strings, or vulnerability details.**
- **No frequently-changing facts** (version numbers that churn, in-flight TODOs).
- **No linter's job.** Don't tell Claude to format code; a Stop hook running the
  formatter is deterministic where a CLAUDE.md line is only advisory. (HumanLayer)

---

## How to write each line

- **Pointers over copies.** Reference `path/file.ext:line`, never paste code that
  drifts out of date. (HumanLayer)
- **Positive phrasing.** "Use Y" beats "don't use X" — flipping negative rules to
  positive roughly halves violations. Reserve a negative only to name a genuinely
  banned pattern ("Use functional components; class components are not allowed").
- **Bullets over paragraphs.** Terse, scannable, one fact per bullet.
- **Exact commands.** Copy-pasteable with flags, not "run the tests".
- **Emphasis discipline.** IMPORTANT / YOU MUST raise adherence but only if rare —
  "if everything is IMPORTANT, nothing is." Use on at most a couple of lines.
- **No contradictions.** Conflicting rules without a priority order degrade
  behavior sharply (resolve rates dropped ~49% → 28% in one study). If two rules
  could conflict, state which wins.

---

## Length budget

- **Binding target: under 150 lines** for the root file. The official ceiling is
  200 (Anthropic Memory docs), but the `review-claude-md` audit fails any root over
  150 (its C2 check), so 150 is the limit to build to — and staying under it is what
  makes generated output pass that audit. Aim well below it.
- Strong real-world root files run 50–100 lines; HumanLayer's is under 60.
- The rationale: frontier models follow ~150–200 instructions consistently, and
  Claude Code's own system prompt already spends ~50 of that budget. Every line
  competes for a fixed attention budget. (HumanLayer)
- If content genuinely exceeds the budget, **modularize** — keep the root under 150
  and move topic detail into `.claude/rules/*.md`. See the modularization guide.

---

## Sources

Last verified 2026-06. Re-verify quarterly or when a link fails.

- Anthropic Best Practices: https://code.claude.com/docs/en/best-practices
- Anthropic Memory: https://code.claude.com/docs/en/memory
- Anthropic blog — Using CLAUDE.md: https://claude.com/blog/using-claude-md-files
- Builder.io: https://www.builder.io/blog/claude-md-guide
- HumanLayer: https://www.humanlayer.dev/blog/writing-a-good-claude-md
- Arize (prompt-learning, +5–11% accuracy from instruction tuning):
  https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/
- Santos et al. (253 files):  https://arxiv.org/html/2509.14744v1
- Agent READMEs (2,303 files): https://arxiv.org/html/2511.12884v1
- AGENTS.md efficiency study (124 PRs, −20% tokens with a context file):
  https://arxiv.org/html/2601.20404v1
- Augment Code — AGENTS.md guide: https://www.augmentcode.com/guides/how-to-build-agents-md

Note on provenance: the developer-written > LLM-generated, no-directory-tree, and
README-redundancy findings are sourced here to Santos et al., the Agent READMEs
study, the AGENTS.md efficiency study, and Augment Code (all cited above). Use
these primary sources when citing those findings.
