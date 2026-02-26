# Review Skill

Review and fix Claude Code skill definitions using tiered binary checklist.

## Installation

```bash
claude --plugin-dir /path/to/sai/review-skill
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

## License

MIT - See [../LICENSE](../LICENSE)
