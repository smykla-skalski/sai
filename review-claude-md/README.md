# Review CLAUDE.md

Audit and fix CLAUDE.md files using tiered binary checklist.

## Installation

```bash
claude --plugin-dir /path/to/sai/review-claude-md
```

## Usage

```
/review-claude-md [path/to/repo] [--score-only] [--fix] [--verbose] [--thorough]
```

| Flag           | Default | Purpose                                       |
|:---------------|:--------|:----------------------------------------------|
| (positional)   | cwd     | Path to repo root containing CLAUDE.md        |
| `--score-only` | off     | Report verdict without fixing                 |
| `--fix`        | on      | Fix all failing checks (default behavior)     |
| `--verbose`    | off     | Show reasoning for each check                 |
| `--thorough`   | off     | Include Polish tier in the report             |

## License

MIT - See [../LICENSE](../LICENSE)
