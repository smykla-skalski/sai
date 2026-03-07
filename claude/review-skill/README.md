# Review Skill

Review and fix Claude Code skill definitions using tiered binary checklist.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install review-skill@smykla-skalski-sai
```

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/review-skill
```

## Usage

```
/review-skill [path/to/skill] [--score-only] [--fix] [--verbose] [--thorough]
```

| Flag           | Default | Purpose                                       |
|:---------------|:--------|:----------------------------------------------|
| (positional)   | cwd     | Path to skill directory containing SKILL.md   |
| `--score-only` | off     | Report verdict without fixing                 |
| `--fix`        | on      | Fix all failing checks (default behavior)     |
| `--verbose`    | off     | Show reasoning for each check                 |
| `--thorough`   | off     | Include Polish tier in the report             |

## Dependencies

- python3 (required for I20-I23 automated checks)
- shellcheck (optional, improves I20 script analysis for .sh files)
- ruff (optional, improves I20 script analysis for .py files)

## Development

Test the plugin locally:

```bash
claude --plugin-dir claude/review-skill/
```

Bump the version in `plugin.json` for any functional change. Skip only for pure doc changes (README, comments, typos).

## License

MIT - See [../../LICENSE](../../LICENSE)
