# Review CLAUDE.md

Audit and fix CLAUDE.md files using a tiered binary checklist (Critical / Important / Polish). It scans the repository, runs two bundled validation scripts, reports a PASS / NEEDS WORK / FAIL verdict with evidence, fixes the failing checks, then re-evaluates. Where the agent can spawn subagents (Copilot CLI, Codex, opencode), the re-evaluation runs in a clean-context `claude-md-evaluator` subagent.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install review-claude-md@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add review-claude-md@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/review-claude-md/` directly:

```bash
ln -s /path/to/sai/plugins/review-claude-md/skills/review-claude-md ~/.config/opencode/skills/review-claude-md
```

Optional named opencode subagent: create `~/.config/opencode/agents/claude-md-evaluator.md` with frontmatter `description` and `mode: subagent`, followed by the body of `skills/review-claude-md/references/claude-md-evaluator.md`.

Local checkout: `claude --plugin-dir /path/to/sai/plugins/review-claude-md/` (or `copilot --plugin-dir ...`)

## Usage

In Claude Code and Copilot CLI use `/review-claude-md`, in Codex `$review-claude-md`, or ask in plain words ("audit this CLAUDE.md").

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

## Subagents per agent

| Agent | Repo scan and script run | Post-fix re-evaluation |
| :-- | :-- | :-- |
| Claude Code | Inline: the skill runs forked (`context: fork`), and a forked skill has no subagent tool | Inline in the fork; the named agent `review-claude-md:claude-md-evaluator` only when a subagent tool is available |
| Copilot CLI | Inline | Same named agent `review-claude-md:claude-md-evaluator` |
| Codex | Inline | One `spawn_agent` call with the mandate prepended, closed after the pass |
| opencode | Inline | `task` tool with an installed `claude-md-evaluator` agent or the built-in `general` subagent |

Every agent falls back to an inline re-evaluation when no subagent tool is available.

## Files

- `agents/claude-md-evaluator.md` - evaluator agent definition for Claude Code and Copilot CLI
- `plugin.json` - root manifest for Codex and Copilot CLI. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/review-claude-md/references/claude-md-evaluator.md` - the same mandate without frontmatter, for generic subagents and inline passes. The agent body and this file must stay identical (enforced by `tests/test_review_claude_md_mandate.py`); edit both together
- `skills/review-claude-md/scripts/` - `validate-claudemd.sh` and `validate-commands.sh`, each printing one `{check, pass, detail}` JSON object per line

## License

MIT - See [../../LICENSE](../../LICENSE)
