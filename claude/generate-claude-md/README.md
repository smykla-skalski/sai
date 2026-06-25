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

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install generate-claude-md@smykla-skalski-sai
```

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/generate-claude-md
```

## Usage

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
