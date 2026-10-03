# AI Daily Digest

Daily AI news digest covering technical advances, business news, and engineering impact. Research runs per topic from dated, verified sources, stories already covered on earlier days are dropped, and the digest goes to Notion, an Obsidian vault, or a local archive.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode. It runs only when invoked by name: Claude Code and Copilot CLI read `disable-model-invocation`, Codex reads `allow_implicit_invocation: false`. In Copilot CLI that means `/ai-daily-digest` in an interactive session; plain requests and `copilot -p` prompts no longer load it, unlike the old Copilot-only bundle.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ai-daily-digest@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add ai-daily-digest@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/ai-daily-digest/` directly:

```bash
ln -s /path/to/sai/plugins/ai-daily-digest/skills/ai-daily-digest ~/.config/opencode/skills/ai-daily-digest
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/ai-daily-digest/` (or `copilot --plugin-dir ...`)

## Usage

In Claude Code and Copilot CLI use `/ai-daily-digest`, in Codex `$ai-daily-digest`.

```text
/ai-daily-digest [--focus technical|business|engineering|leadership|all] [--notion-page-id ID] [--no-notion] [--obsidian-vault PATH]
```

Publishing target: `--notion-page-id` or `NOTION_PARENT_PAGE_ID` for Notion; otherwise `--obsidian-vault`, `OBSIDIAN_VAULT_PATH`, or an auto-detected vault; otherwise archive only. State (`.last-run`, `.covered-stories`) and archive copies live in `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ai-daily-digest/`.

## Research subagent per agent

| Agent | Subagent |
| :-- | :-- |
| Claude Code | Named agent `ai-daily-digest:digest-research-agent` from `agents/`, Phases 2-5 in parallel; `general-purpose` with the mandate prepended as fallback |
| Copilot CLI | Same named agent, one phase at a time by default to save AI credits |
| Codex | Inline and sequential by default; optional `spawn_agent` fan-out of at most 5 when asked |
| opencode | `task` tool with the built-in `general` subagent and the mandate prepended, or inline |

## Files

- `agents/digest-research-agent.md` - Claude Code and Copilot CLI research agent
- `plugin.json` - root manifest for Codex and Copilot CLI. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/ai-daily-digest/references/digest-research-agent.md` - the same mandate for the generic-subagent and inline paths. The agent body and the reference file must stay identical; `tests/test_ai_daily_digest_mandate.py` enforces it
- `skills/ai-daily-digest/SKILL.md` - workflow; see it for configuration details

## License

MIT - See [../../LICENSE](../../LICENSE)
