# adversarial-review

Fast two-pass adversarial code review. It answers one question - is this change correct? - with two opposed subagents, each in a clean context:

1. **Code Adversary** assumes the change is broken and hunts the concrete bug. Every finding needs a failing input or sequence, and a `blocking:` finding needs an executed reproduction (the command and its output) or an explicit interleaving trace; anything less is an `issue:` or a `question:`, so an unverifiable race comes back as a question.
2. **Findings Adversary** runs only when the first pass found a `blocking:` or `issue:` - never to refute a clean result. It is spawned fresh, gets only the numbered findings (never the first agent's reasoning), and tries to refute each one against the source: removes false positives, strips `blocking:` from findings without proof, right-sizes severity, fixes bad locations, merges duplicates.

Each adversary starts in a fresh context, is closed after its verdict and is never reused for a fix or another change. The skill checks every verdict line against the documented format: a malformed reply gets one retry with a fresh subagent, then the gate fails.

Output leads with `Review Verdict: CLEAN`, `Review Verdict: NEEDS_FIXES` or `Review Verdict: FAILED` (a pass returned a malformed verdict twice), so callers such as `ship-it` can gate on the first line. Only `CLEAN` passes.

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
| Claude Code | Named agents `adversarial-review:code-adversary` and `adversarial-review:findings-adversary` (also used by `ship-it`); `general-purpose` with the mandate prepended when they are not registered |
| Codex | `spawn_agent` with the mandate prepended, sequential, closed after each pass |
| opencode | `task` tool with the installed named agents or the built-in `general` subagent |
| Copilot CLI | The same named agents through its subagent tool; a generic subagent with the mandate prepended otherwise |

Every agent falls back to two labelled inline passes when no subagent tool is available. A malformed verdict is never rescued inline: it fails the gate after one retry.

## Files

- `agents/code-adversary.md`, `agents/findings-adversary.md` - Claude Code agent definitions
- `plugin.json` - Agent Plugins manifest for Codex. It has no `$schema` key on purpose: with `$schema` present, Copilot CLI stops registering the plugin's `agents/` directory
- `skills/adversarial-review/references/code-adversary.md`, `findings-adversary.md` - the same mandates without frontmatter, for generic subagents and inline passes on every agent. Agent bodies and reference files must stay identical; edit both together

## License

MIT
