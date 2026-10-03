# adversarial-review

Fast two-pass adversarial code review. It answers one question - is this change correct? - with two opposed subagents, each in a clean context:

1. **Code Adversary** assumes the change is broken and hunts the concrete bug. Every finding needs a failing input or sequence.
2. **Findings Adversary** is spawned fresh, gets only the numbered findings (never the first agent's reasoning), and tries to refute each one against the source: removes false positives, right-sizes severity, fixes bad locations, merges duplicates.

Output leads with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`, so callers such as `ship-issue` can gate on the first line.

For architecture, conventions, and cross-team impact, use `staff-code-review` instead.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install adversarial-review@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add adversarial-review@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/adversarial-review/` directly:

```bash
ln -s /path/to/sai/plugins/adversarial-review/skills/adversarial-review ~/.config/opencode/skills/adversarial-review
```

Optional read-only named subagents for opencode: create `~/.config/opencode/agents/code-adversary.md` and `findings-adversary.md` with frontmatter `description`, `mode: subagent` and `permission: { edit: deny }`, followed by the body of the matching file in `skills/adversarial-review/references/`.

Local checkout: `claude --plugin-dir /path/to/sai/plugins/adversarial-review/`

## Usage

In Claude Code and Copilot CLI use `/adversarial-review`, in Codex `$adversarial-review`, or ask in plain words ("adversarially review this branch").

```text
/adversarial-review                                   # working tree vs merge-base with origin/<default>
/adversarial-review --base origin/release-1.4
/adversarial-review https://github.com/owner/repo/pull/123
/adversarial-review <patch-file>
/adversarial-review --context <issue-file|text>       # acceptance criteria for the Code Adversary
```

## Subagents per agent

| Agent | Subagents |
| :-- | :-- |
| Claude Code | Named agents `adversarial-review:code-adversary` and `adversarial-review:findings-adversary` (also used by `ship-issue`); `general-purpose` with the mandate prepended when they are not registered |
| Codex | `spawn_agent` with the mandate prepended, sequential, closed after each pass |
| opencode | `task` tool with the installed named agents or the built-in `general` subagent |
| Copilot CLI | The same named agents through its subagent tool; a generic subagent with the mandate prepended otherwise |

Every agent falls back to two labelled inline passes when no subagent tool is available.

## Files

- `agents/code-adversary.md`, `agents/findings-adversary.md` - Claude Code agent definitions
- `plugin.json` - Agent Plugins manifest for Codex. It has no `$schema` key on purpose: with `$schema` present, Copilot CLI stops registering the plugin's `agents/` directory
- `skills/adversarial-review/references/code-adversary.md`, `findings-adversary.md` - the same mandates without frontmatter, for generic subagents and inline passes on every agent. Agent bodies and reference files must stay identical; edit both together

## License

MIT
