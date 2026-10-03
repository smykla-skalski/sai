# git-clean-gone

Clean up local branches with deleted remote tracking and their worktrees. Detects gone branches, squash-merged PRs (via `gh`), and rebased branches (via `git cherry`).

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install git-clean-gone@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add git-clean-gone@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/git-clean-gone/` directly:

```bash
ln -s /path/to/sai/plugins/git-clean-gone/skills/git-clean-gone ~/.config/opencode/skills/git-clean-gone
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/git-clean-gone/`

## Usage

The skill deletes branches and worktrees, so it never runs on its own: in Claude Code and Copilot CLI invoke `/git-clean-gone`, in Codex `$git-clean-gone` (implicit invocation is disabled). On agents other than Claude Code, any request that does not name the skill gets a `--dry-run` preview first and deletes only after you confirm the whole list. The real run fetches again, so anything it deletes beyond the preview is called out in the summary.

```
/git-clean-gone
/git-clean-gone --dry-run
/git-clean-gone --no-worktrees
```

| Flag             | Purpose                              |
|:-----------------|:-------------------------------------|
| `--dry-run`      | Preview only, no changes             |
| `--no-worktrees` | Branches only, skip worktree removal |

## License

MIT
