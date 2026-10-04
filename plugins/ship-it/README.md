# ship-it

Take one change from request to merged pull request autonomously: explore the repository, implement and test the change, red-team it with code review and manual testing, open a PR, address Copilot feedback, wait for green CI, and merge. The change can be a plain description, a GitHub issue, or a Jira ticket.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

`ship-it` replaces `ship-issue`. To upgrade, uninstall `ship-issue@sai` and install `ship-it@sai`.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ship-it@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add ship-it@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/ship-it/` directly:

```bash
ln -s /path/to/sai/plugins/ship-it/skills/ship-it ~/.config/opencode/skills/ship-it
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/ship-it/`

Install [adversarial-review](../adversarial-review/) and [adversarial-test](../adversarial-test/) too: ship-it uses them as its review and testing gates. Without them it runs the same passes itself.

## Usage

In Claude Code and Copilot CLI use `/ship-it`, in Codex `$ship-it`:

```text
/ship-it <task description>
/ship-it --issue <task description>
/ship-it https://github.com/owner/repo/issues/123
/ship-it https://your-site.atlassian.net/browse/KEY-123
```

| Input | What happens |
| :-- | :-- |
| Task description | Implements it and opens a PR. No issue is created |
| `--issue` + description | Creates a GitHub issue first, then ships it and closes it on merge |
| GitHub issue URL | Ships the issue; the PR body has `Closes #N`, so merging closes it |
| Jira URL | Reads the ticket through Atlassian MCP tools, `acli`, or the `jira` CLI, whichever is available, and asks you to paste it when none is. The Jira key goes in the PR title or body. The ticket is never transitioned, commented on, or edited unless you ask |

Input it cannot recognize or read stops with a message before any code changes.

The skill pushes and merges, so Codex runs it only when invoked by name. On agents without a subagent tool, the review and test passes run inline, one after another.

It merges the way the repository documents (for example a `squash` PR comment where a bot merges), otherwise with a squash merge. After the first push it never force-pushes or rebases.

The skill owns the full lifecycle and stops only for genuine ambiguity, branch-protection requirements, persistent review/test failures, or product decisions that the request and repository cannot answer.

## License

MIT
