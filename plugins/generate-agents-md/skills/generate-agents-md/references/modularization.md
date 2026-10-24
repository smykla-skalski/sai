# Modularization, Hierarchy & Cross-Tool Bridging

How to keep the root file lean when there is genuinely more to say, and how to
fit into the CLAUDE.md hierarchy and the AGENTS.md ecosystem.

## Contents

- [When to split](#when-to-split)
- [.claude/rules/ with path scoping](#clauderules-with-path-scoping)
- [@imports vs rules](#imports-vs-rules)
- [The load hierarchy](#the-load-hierarchy)
- [Monorepos: nested CLAUDE.md](#monorepos-nested-claudemd)
- [Bridging AGENTS.md](#bridging-agentsmd)

---

## When to split

Default to a single root `CLAUDE.md`. Split only when content is genuinely
valuable AND the root would exceed ~150 lines, or when a topic applies only to a
subset of files. Splitting trades one always-loaded file for lazy-loaded topic
files — useful, but each split adds indirection, so don't over-modularize a small
project.

Keep in the root: commands, the architecture map, top gotchas, repo etiquette.
Move to a rule file: long topic detail (test infrastructure, a subsystem's
conventions, a release runbook) that is not needed every session.

## .claude/rules/ with path scoping

`.claude/rules/*.md` are topic files. The key feature: **`paths:` frontmatter
scopes a rule to globs**, so it loads only when Claude touches matching files —
saving context the rest of the time.

```markdown
---
paths:
  - "src/payments/**"
---
- Payment intents are idempotent on `idempotency_key`; never retry without it
- Webhook signatures verified in `src/payments/webhook.ts:18` — never bypass
```

A rule file **without** `paths:` loads at launch with the same priority as the
root file — use that only for rules that truly apply everywhere. When you move
content into a rule, link it from the root with a one-line description so a reader
(and Claude) knows it exists:

```markdown
- Payments conventions: see `.claude/rules/payments.md` (loads when editing `src/payments/`)
```

## @imports vs rules

`@path` imports pull another file in **at launch, in full** — they organize but do
**not** save context (max depth 4 hops). Use imports for "always-on" shared content
(e.g. bridging AGENTS.md); use path-scoped rules for "load only when relevant".
To mention a path without importing it, wrap it in backticks (`` `@README` ``).

## The load hierarchy

Files are concatenated, broadest → most specific; later wins on conflict:

1. Managed policy (org-wide, cannot be excluded by the user)
2. User `~/.claude/CLAUDE.md` (personal, all projects)
3. Project `./CLAUDE.md` or `./.claude/CLAUDE.md` (team-shared, git-tracked) ← **the target**
4. `./CLAUDE.local.md` (personal, gitignored)
5. Parent dirs load before child dirs; child dirs load on demand when Claude reads them

Generate the **project** file. Do not restate anything that belongs in the user or
managed layers (personal preferences, org policy). Put personal-only notes in
`CLAUDE.local.md` and keep it gitignored.

## Monorepos: nested CLAUDE.md

For a monorepo, keep a short root CLAUDE.md with cross-cutting facts, and put a
focused CLAUDE.md in each sub-project directory — the nested file loads on demand
when Claude works in that subtree. Don't cram every sub-project's commands into the
root.

## Bridging AGENTS.md

AGENTS.md is the cross-tool standard (read by Codex, Cursor, Aider, Copilot, Gemini
CLI, and more). Claude Code does **not** read AGENTS.md natively. If the repo has
(or should have) an AGENTS.md:

- Put universal, tool-agnostic rules in `AGENTS.md`.
- Make `CLAUDE.md` bridge to it: the **first line** is `@AGENTS.md`, followed by
  Claude-specific additions (plan-mode notes, hooks, imports). Claude loads the
  import then appends the Claude-only content.
- If there are no Claude-specific additions at all, a symlink `CLAUDE.md → AGENTS.md`
  works (but a Windows checkout needs the `@AGENTS.md` import form instead).

```markdown
@AGENTS.md

## Claude-specific
- Use the `git-stage-hunk` skill for partial commits
```

This keeps one source of truth and avoids duplicating shared rules across two files.
