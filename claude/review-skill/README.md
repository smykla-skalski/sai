# Review Skill

Review and fix Claude Code skill definitions using a tiered binary checklist based on the Agent Skills specification, Anthropic best practices, and community guidelines.

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
/review-skill [path/to/skill] [--dry-run] [--verbose] [--thorough] [--json-report] [--strict]
```

| Flag | Default | Purpose |
| :-- | :-- | :-- |
| (positional) | cwd | Path to skill directory containing SKILL.md |
| `--dry-run` | off | Report verdict without fixing (read-only) |
| `--verbose` | off | Show reasoning for each check |
| `--thorough` | off | Include Polish tier in the report |
| `--json-report` | off | Output report as JSON instead of markdown |
| `--strict` | off | Treat any Important failure as FAIL |

## Checklist tiers

| Tier | Range | Verdict rule |
| :-- | :-- | :-- |
| Critical | C1-C8 | Any failure = FAIL |
| Important | I1-I31 | 3+ failures = NEEDS WORK |
| Polish | P1-P22 | Informational, shown with `--thorough` |

## Automated checks

The orchestrator (`validate.py`) runs 14 companion scripts covering 77+ automated checks:

| Script | Checks | Purpose |
| :-- | :-- | :-- |
| `check-security.py` | C8 | Security vulnerabilities (shell=True, eval, unsafe deserialization) |
| `check-file-refs.py` | C3, I15, P3, P6 | File reference resolution and format |
| `check-scripts-dir.py` | I6, I12, I30, I31, P16, P18 | Script invocation, permissions, help output, deps |
| `check-references.py` | C2, I14, I24, P1, P8, P15 | Body metrics and reference structure |
| `check-config.py` | I11, I16, I17, P19 | Tool usage, XDG state, side-effect guard, MCP format |
| `check-content.py` | C6, C7, I13, P22 | Secrets, echo, grading style, unversioned commands |
| `check-best-practices.py` | I26, I27, I29, P11-P14, P17, P20-P21 | Examples, emphasis, rationale, best-practice signals |
| `check-fork-candidate.py` | P9 | Fork candidate analysis |
| `check-preprocessing.py` | I18 | Preprocessing directive hygiene |
| `check-read-gates.py` | I19 | Reference read gate analysis |
| `check-lint.py` | I20 | Script static analysis, interactive prompt detection |
| `check-ask-user.py` | I21 | AskUserQuestion usage validation |
| `check-flag-coverage.py` | I22, I28 | Flag documentation consistency |
| `check-hooks.py` | I23, P10 | Hooks configuration validation |

## Dependencies

- python3 (required - orchestrator and all checks are Python)
- shellcheck (optional, improves I20 script analysis for .sh files)
- ruff (optional, improves I20 script analysis for .py files)

## Development

Test the plugin locally:

```bash
claude --plugin-dir claude/review-skill/
```

Run tests and linters:

```bash
mise run check    # all tests + ruff + mypy
mise run test     # all tests only
mise run lint     # ruff + mypy only
```

Bump the version in `plugin.json` for any functional change. Skip only for pure doc changes (README, comments, typos).

## License

MIT - See [../../LICENSE](../../LICENSE)
