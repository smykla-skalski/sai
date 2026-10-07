# ship-it

Take one change from request to merged pull request autonomously: explore the repository, implement the change, run risk-selected gates, open a PR, address required feedback, and merge. The change can be a plain description, a GitHub issue, or a Jira ticket. An approved complex plan or an umbrella issue with implementation subissues runs as a coordinated set of separate issues.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Its initial workflow contract stays below Codex's 8 KB prompt limit. Detailed instructions load from bundled references only when each workflow phase begins.

Every phase also has a versioned machine-readable capability contract. It selects one of four portable profiles (`explore`, `build`, `review`, or `release`), verifies requirements before side effects, preserves equivalent fallbacks across harnesses, and keeps destructive, secret-bearing, deployment, out-of-workspace, and unknown actions interactive.

Every task has a portable JSON checkpoint under `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/checkpoints/`. Claude Code, Codex, Copilot CLI, opencode and Sail use the same task identity, phase, revision, blocker and outcome fields, so another harness can safely reconcile Git and GitHub before resuming.

Each run writes privacy-safe workflow events to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/telemetry/events.ndjson`. The versioned NDJSON contract uses stable harness, provider, model, role and phase fields; unavailable counters stay `null`, and prompt or source content is never recorded. Sail and local analysis tools can consume the same stream.

Each committed task revision also has one portable evidence record under `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/evidence/`. Acceptance criteria, local checks, adversarial review, manual testing and CI carry their source revision, provider, model, status, timestamp and bounded output reference. Any source change makes the previous record stale. PR-due evidence for the current revision permits PR creation; a complete record with passing CI for the current PR head permits merge.

Validation gates come from a portable risk policy. Repositories can add `.sai/ship-it-risk.json` with low, medium and high policies plus deterministic changed-path rules. Agents may raise risk; lowering a policy or checkpoint floor needs explicit user authorization. Without a repository policy every level retains the full existing local-check, adversarial-review, adversarial-test, CI and Copilot sequence.

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

Install [adversarial-review](../adversarial-review/) and [adversarial-test](../adversarial-test/) too: ship-it uses them when selected. When unavailable, it uses only a policy-approved fallback or stops.

## Usage

In Claude Code and Copilot CLI use `/ship-it`, in Codex `$ship-it`:

```text
/ship-it <task description>
/ship-it --risk high <task description>
/ship-it --issue <task description>
/ship-it https://github.com/owner/repo/issues/123
/ship-it https://your-site.atlassian.net/browse/KEY-123
```

| Input | What happens |
| :-- | :-- |
| Task description | Implements it and opens a PR. No issue is created |
| `--issue` + description | Creates a GitHub issue first, then ships it and closes it on merge |
| `--risk low\|medium\|high` + any source | Sets an explicit minimum risk; repository rules may raise it |
| GitHub issue URL | Ships the issue; the PR body has `Closes #N`, so merging closes it |
| Jira URL | Reads the ticket through Atlassian MCP tools, `acli`, or the `jira` CLI, whichever is available, and asks you to paste it when none is. The Jira key goes in the PR title or body. The ticket is never transitioned, commented on, or edited unless you ask |
| Approved complex plan or umbrella issue | Reuses or creates a ☂️ umbrella and independent subissues, then dispatches up to three eligible workers. Dependencies wait for prerequisite PRs to merge. The parent only coordinates |

Input it cannot recognize or read stops with a message before any code changes.

The skill pushes and merges, so Codex runs it only when invoked by name. Outside Sail, agents may use declared inline fallbacks. In Sail mode, unavailable required worker or gate subagents pause the run. A child completes only after all risk-selected gates pass, required threads resolve, its PR merges, and its issue closes.

It merges the way the repository documents (for example a `squash` PR comment where a bot merges), otherwise with a squash merge. After the first push it never force-pushes or rebases.

The skill owns the full lifecycle and stops only for genuine ambiguity, branch-protection requirements, persistent review/test failures, or product decisions that the request and repository cannot answer.

## License

MIT
