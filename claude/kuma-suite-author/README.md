# kuma-suite-author

Generate test suites for kuma-manual-test by reading Kuma source code. Produces ready-to-run suites with manifests, validation steps, and expected outcomes.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install kuma-suite-author@smykla-skalski-sai
```

### Manual

```bash
claude --plugin-dir /path/to/sai/claude/kuma-suite-author
```

## Usage

```
/kuma-suite-author <feature-name> [--repo /path/to/kuma] [--mode generate|wizard] [--from-pr PR_URL] [--from-branch BRANCH]
```

| Flag | Default | Purpose |
|:-----|:--------|:--------|
| (positional) | - | Feature or policy name (e.g., `meshretry`, `meshtrace`) |
| `--repo` | auto-detect cwd | Path to Kuma repo checkout |
| `--mode` | `generate` | `generate` (full AI) or `wizard` (interactive) |
| `--from-pr` | - | GitHub PR URL to scope the feature from |
| `--from-branch` | - | Git branch to diff against master for scope |
| `--suite-name` | derived | Override output filename |

## Documentation

See [SKILL.md](./skills/kuma-suite-author/SKILL.md) for detailed workflow and configuration.

## License

MIT - See [../../LICENSE](../../LICENSE)
