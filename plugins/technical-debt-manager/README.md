# technical-debt-manager

Audits a repository for technical debt, researches best practices for the detected language and framework versions, and files the results as GitHub issues: one ☂️ umbrella tracker plus one sub-issue per finding. Every finding is rated on impact, effort, contagion and business alignment and carries a concrete fix.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Re-runs are incremental: when an open umbrella already exists, the skill reuses it, dedupes new findings against its sub-issues (open and closed), files only new debt, and reports regressions instead of reopening issues.

## Requirements

- `git` and the [GitHub CLI](https://cli.github.com) (`gh`), authenticated for the target repo
- gh 2.94 or newer: the skill links sub-issues with `gh issue create --parent` and reads them with `gh issue view --json subIssues`. On older gh it falls back to the GraphQL `addSubIssue` mutation, so no helper script is needed
- Web search and fetch tools for the best-practice research phase (optional; without them the audit runs on the codebase alone and says so in the tracker)

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install technical-debt-manager@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add technical-debt-manager@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/technical-debt-manager/` directly:

```bash
ln -s /path/to/sai/plugins/technical-debt-manager/skills/technical-debt-manager ~/.config/opencode/skills/technical-debt-manager
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/technical-debt-manager/`

## Usage

In Claude Code and Copilot CLI use `/technical-debt-manager`, in Codex `$technical-debt-manager`, or ask in plain words ("audit this repo for tech debt"). Run it from inside the repository to audit.

```
/technical-debt-manager
/technical-debt-manager --focus dependencies
/technical-debt-manager --label debt
```

| Flag      | Default     | Purpose                                                                                                  |
|:----------|:------------|:---------------------------------------------------------------------------------------------------------|
| `--focus` | full scan   | Limit the analysis to one area: `error-handling`, `tests`, `dependencies`, `architecture`, and so on      |
| `--label` | `tech-debt` | Label for the umbrella and sub-issues; also scopes umbrella detection and dedup on re-runs                |

The skill creates GitHub issues in the current repository. Try it on a throwaway repository first.

In Claude Code the skill runs in a forked general-purpose subagent (`context: fork`) so the long exploration stays out of your main conversation. Other agents run it in the main loop with the same result.

## Output

- **Fresh run:** `☂️ Tech Debt Audit: {repo} ({date})` umbrella with the tracker, research context, summary table, recommended order and measurement section, plus one conventional-commit-titled sub-issue per finding
- **Re-run:** new sub-issues linked to the existing umbrella, merged into its tracker without touching existing entries or checkbox states
- **No GitHub remote:** a markdown report at `${XDG_DATA_HOME:-$HOME/.local/share}/sai/technical-debt-manager/debt-report-{date}.md`

## License

MIT
