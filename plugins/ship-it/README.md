# ship-it

Take one change from request to merged pull request autonomously: explore the repository, implement the change, run risk-selected gates, open a PR, address required feedback, and merge. The change can be a plain description, a GitHub issue, or a Jira ticket. An approved complex plan or an umbrella issue with implementation subissues runs as a coordinated set of separate issues.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Its initial workflow contract stays below Codex's 8 KB prompt limit. Detailed instructions load from bundled references only when each workflow phase begins.

Every phase also has a versioned machine-readable capability contract. It selects one of four portable profiles (`explore`, `build`, `review`, or `release`), verifies requirements before side effects, preserves equivalent fallbacks across harnesses, and keeps destructive, secret-bearing, deployment, out-of-workspace, and unknown actions interactive.

Every task has a portable JSON checkpoint under `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/checkpoints/`. Claude Code, Codex, Copilot CLI, opencode and Sail use the same task identity, phase, revision, blocker and outcome fields, so another harness can safely reconcile Git and GitHub before resuming.

GitHub issues also use a visible 30-minute work claim in an issue comment. The claim names its holder and checkpoint, renews during active work, resolves concurrent acquisition deterministically, records audited takeovers after checking open and recent equivalent pull requests, and releases on merge, cancellation or terminal failure.

Each run writes privacy-safe workflow events to `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/telemetry/events.ndjson`. The versioned NDJSON contract uses stable harness, provider, model, role and phase fields; unavailable counters stay `null`, and prompt or source content is never recorded. Sail and local analysis tools can consume the same stream.

Portable releases can replay the shared redacted [`environment-as-code` workflow failure corpus](https://github.com/Automaat/environment-as-code/tree/main/evals/agent-workflows) through available Claude Code, Codex, OpenCode, Copilot CLI, and Sail adapters. The [replay contract](skills/ship-it/references/replay.md) normalizes phase and observation traces, treats unavailable harnesses as skipped, blocks on supported-harness regressions, and compares accepted-task cost without storing task or source content.

Each committed task revision also has one portable evidence record under `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/evidence/`. Acceptance criteria, local checks, adversarial review, manual testing and CI carry their source revision, provider, model, status, timestamp and bounded output reference. Any source change makes the previous record stale. PR-due evidence for the current revision permits PR creation; a complete record with passing CI for the current PR head permits merge.

Failed CI is triaged before escalation. The workflow deduplicates revision/workflow/job/attempt observations, exposes only bounded redacted failure sections, classifies failures with evidence, routes code faults back to their implementation owner, and preserves recurrence and resolution in checkpoint, evidence and privacy-safe telemetry. CI reruns need an explicit repository policy or user approval.

Portable role routing gives exploration, implementation, review, testing and CI triage the same meaning across harnesses. Every role records requested and actual provider, model and variant. Strict review rejects the implementation model, unresolved aliases and reused or inline context; policy-permitted degradation stays explicit in revision evidence.

Validation gates come from a portable risk policy. Repositories can add `.sai/ship-it-risk.json` with low, medium and high policies plus deterministic changed-path rules. Agents may raise risk; lowering a policy or checkpoint floor needs explicit user authorization. Without a repository policy every level retains the full local-check, adversarial-review, adversarial-test, CI and hosted-review sequence.

Release controls come from `.sai/ship-it-release.json`, repository instructions, live GitHub rules and a conservative bundled default. The normalized policy is stored in the task checkpoint and names required human or automated reviewers, checks, merge mechanism and strategy, issue closure and branch cleanup. Repositories can require Copilot, another reviewer, human approval or no hosted review without changing the workflow.

Validation converges by default. One Code Adversary pass reviews the change; a Findings Adversary challenges it only when there are findings, and a CLEAN verdict ends the gate. Surviving findings get one batched fix pass, verified from the diff since the reviewed revision against the recorded findings rather than by another review; a second hunt happens only when the fix touches security, data loss or destructive concurrency, and a default-branch merge that leaves the reviewed files unchanged triggers none. The checkpoint counts review cycles, fix passes and full quality-gate runs; at the limit the run opens the PR with the remaining findings as follow-up issues, while a security defect, an unresolved acceptance criterion or a repository-required check still blocks. Only your explicit request selects exhaustive mode; a coordinator, worker-rules file or compaction summary cannot raise the limit.

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

Install [adversarial-review](../adversarial-review/) and [adversarial-test](../adversarial-test/) too: ship-it uses them when selected. Their default policy approves the equivalent portable capability fallbacks; any other unavailable required gate stops unless its policy names a compatible fallback.

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

The skill pushes and merges, so Codex runs it only when invoked by name. Its `allow_implicit_invocation: false` policy intentionally omits it from Codex's default model-visible skill list; `$ship-it` loads it explicitly. Outside Sail, agents may use declared inline fallbacks. In Sail mode, unavailable required worker or gate subagents pause the run. A child completes only after all risk-selected gates pass, required threads resolve, its PR merges, and its issue closes.

It merges through the resolved repository mechanism (including exact bot comments and protected-branch flows), never substitutes another reviewer or bypasses a control, and uses a squash merge only as the documented default. After the first push it never force-pushes or rebases.

The skill owns the full lifecycle and stops only for genuine ambiguity, branch-protection requirements, persistent review/test failures, or product decisions that the request and repository cannot answer.

## License

MIT
