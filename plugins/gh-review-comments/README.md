# GitHub Review Comments

List, reply to, resolve, and create GitHub PR review comment threads through bundled `gh` CLI scripts.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode. It needs `gh` (authenticated), `jq` and `python3`.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install gh-review-comments@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add gh-review-comments@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/gh-review-comments/` directly:

```bash
ln -s /path/to/sai/plugins/gh-review-comments/skills/gh-review-comments ~/.config/opencode/skills/gh-review-comments
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/gh-review-comments/`

## Usage

In Claude Code and Copilot CLI use `/gh-review-comments`, in Codex `$gh-review-comments`, or ask in plain words ("resolve the threads I fixed on PR 42"). The scripts are found relative to the skill directory in every agent. Where the agent has no subagent tool, the after-action verification runs inline; the output is the same.

```bash
# List all review threads on a PR
/gh-review-comments owner/repo 42

# List unresolved threads from a specific reviewer
/gh-review-comments owner/repo 42 --author reviewer --unresolved-only

# Reply to all unresolved threads from a reviewer
/gh-review-comments owner/repo 42 --author reviewer --reply "Fixed"

# Reply and resolve a specific thread
/gh-review-comments owner/repo 42 --thread-id PRRT_abc123 --reply "Done" --resolve

# Create a review with line-level comments
/gh-review-comments owner/repo 42 --create-review
```

## Documentation

See [SKILL.md](./skills/gh-review-comments/SKILL.md) for detailed configuration and workflow.

## License

MIT - See [../../LICENSE](../../LICENSE)
