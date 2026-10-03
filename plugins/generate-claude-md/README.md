# Generate CLAUDE.md

Generate a lean, high-signal CLAUDE.md for a repository from codebase analysis.

The generator counterpart to [`review-claude-md`](../review-claude-md/): it targets
the same best-practices rubric the reviewer audits against. A bundled validator
enforces review-claude-md's Critical checks (commands present, under 150 lines, no
README duplication, no generic advice) plus bullets and pointer style, so a
generated file is built to pass that audit; the workflow applies the remaining
quality (architecture relationships, domain mapping, real gotchas). It produces
short, project-specific files and deliberately avoids what naive `/init` output
tends to include: README duplication, directory trees, and generic advice Claude
already knows.

## Installation

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one
[Agent Skill](https://agentskills.io), so the same package works in Claude Code,
Codex, Copilot CLI and opencode.

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install generate-claude-md@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add generate-claude-md@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/generate-claude-md/` directly:

```bash
ln -s /path/to/sai/plugins/generate-claude-md/skills/generate-claude-md ~/.config/opencode/skills/generate-claude-md
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/generate-claude-md/`

## Usage

In Claude Code and Copilot CLI use `/generate-claude-md`, in Codex
`$generate-claude-md`, or ask in plain words ("write a CLAUDE.md for this repo").
Where the agent has no subagent tool, the codebase scan runs inline instead of in
a subagent; the output is the same.

```
/generate-claude-md [path/to/repo] [--output PATH] [--update] [--force] [--rules] [--dry-run]
```

| Flag         | Default | Purpose                                                        |
|:-------------|:--------|:---------------------------------------------------------------|
| (positional) | cwd     | Repo root to analyze                                           |
| `--output`   | CLAUDE.md | Write to a specific path                                     |
| `--update`   | off     | Merge into an existing file, preserving custom sections        |
| `--force`    | off     | Overwrite an existing CLAUDE.md (explicit, destructive opt-in) |
| `--rules`    | off     | Split topic detail into `.claude/rules/*.md`                   |
| `--dry-run`  | off     | Print the result without writing                               |

## Write safety

Never overwrites silently. If `CLAUDE.md` already exists and neither `--update`
nor `--force` is passed, the skill writes `CLAUDE.generated.md` next to it and
tells you to diff and choose — so an existing file is never lost.

## How it works

1. Scans manifests, task runners, CI, and lint/test config (read-only subagent)
2. Verifies build/test/lint commands are real before listing them
3. Synthesizes only project-specific, non-obvious content, applying the deletion
   test to every line
4. Splits into `.claude/rules/` when over the length budget
5. Validates the result with a bundled checker (line count, README de-duplication,
   no directory tree, no generic advice, bullet ratio, commands present) and
   iterates until it passes

After generating, audit anytime with `/review-claude-md`.

## License

MIT - See [../../LICENSE](../../LICENSE)
