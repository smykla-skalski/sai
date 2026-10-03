# ship-issue

Take one GitHub issue from URL to merged pull request autonomously: explore the repository, implement and test the change, red-team it with code review and manual testing, open a PR, address Copilot feedback, wait for green CI, merge, and close the issue.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ship-issue@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add ship-issue@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/ship-issue/` directly:

```bash
ln -s /path/to/sai/plugins/ship-issue/skills/ship-issue ~/.config/opencode/skills/ship-issue
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/ship-issue/`

Install [adversarial-review](../adversarial-review/) and [adversarial-test](../adversarial-test/) too: ship-issue uses them as its review and testing gates. Without them it runs the same passes itself.

## Usage

In Claude Code and Copilot CLI use `/ship-issue`, in Codex `$ship-issue`:

```text
/ship-issue https://github.com/owner/repo/issues/123
/ship-issue <task description>
```

The skill pushes, merges and closes issues, so Codex runs it only when invoked by name. On agents without a subagent tool, the review and test passes run inline, one after another.

The skill owns the full ticket lifecycle and stops only for genuine ambiguity, branch-protection requirements, persistent review/test failures, or product decisions that cannot be recovered from the issue and repository.

## License

MIT
