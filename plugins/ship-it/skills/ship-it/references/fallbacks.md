# ship-it fallbacks for other agents

ship-it is written for Claude Code. On Codex, opencode or Copilot CLI, or when a Claude feature is missing, use these fallbacks. Review and testing always require fresh subagent contexts; pause if a required worker or gate subagent cannot launch.

## Agent compatibility

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | Claude Code appends the arguments to the skill. If none are appended, take the description, URL and flags from the user's request |
| ToolSearch (Jira via Atlassian MCP) | Codex, Copilot CLI, opencode: use Atlassian MCP tools only when the session already lists them. No MCP tools: use the `acli` or `jira` CLI |
| Skill tool (review and test gates) | Codex: invoke `$adversarial-review` and `$adversarial-test` (plugins `adversarial-review@sai`, `adversarial-test@sai`) with the same arguments. Copilot CLI: `/adversarial-review`, `/adversarial-test`. opencode: load the skill of the same name. If a skill cannot route fresh subagents, dispatch generic subagents using the phase reference |
| Named agents `adversarial-review:code-adversary`, `adversarial-review:findings-adversary`, `adversarial-test:test-adversary` | Registered only where their plugin is installed in Claude Code or Copilot CLI. Codex and opencode do not register them; there, or whenever the type is unknown, spawn a generic subagent (`general-purpose`) with the mandate loaded for the active phase |
| Subagent tool (Agent) | Codex: `spawn_agent`; launch the complete eligible issue batch before `wait_agent` (or the available native wait). The wait/close ordering is per review, never global across issues. Count descendants in the shared budget. Close finished threads only when a close tool exists; otherwise retain finished threads in the budget if the host counts open threads. Use active-turn accounting only when the host does. opencode: the `subagent` tool (`task` on opencode 1). Copilot CLI: its agent tool. Within each review, the Findings Adversary starts only after the Code Adversary returns and uses a new execution. Review blocks without fresh subagents; inline passes never satisfy the gate |
| Test subagent | Each test attempt uses a fresh tester execution. Testing blocks without a fresh subagent; inline testing never satisfies the gate |
| AskUserQuestion | Not used; a hard-stop question or a request to paste a Jira ticket goes to the user as plain text, then end the turn |
| `context: fork` | Not used |
| Explicit invocation | ship-it pushes, merges and closes issues, so it runs only when the user invokes it by name. Codex enforces this through `agents/openai.yaml` (`allow_implicit_invocation: false`). On other agents, start only when the user asked to ship a change or invoked `/ship-it` or `$ship-it` |
| Durable checkpoint | Every harness reads and writes the same JSON contract under the XDG data directory. Do not translate it into harness session state, conversation memory or a temporary file |
| Scoped authorization | Every harness preserves original user requests and clear approvals of concrete pending requests in checkpoint `authorization.grants`; handoffs retain scope, limits, consumed allowances and status. No special approval wording is required. Internal limits trigger authorized focused acceptance triage under [authorization.md](authorization.md), not renewed permission |
| Convergence budget | Every harness reads `convergence-policy.json` directly and updates the same checkpoint counters. Harness defaults never widen or reset the budget; neither does a coordinator, worker-rules file, spawn prompt or compaction summary |

## Sandboxed agents

On agents with a command sandbox (Codex), the user's request to ship the change authorizes normal branch, commit, push, PR, review-reply, merge and issue-close actions in the target repository. If a networked `git`, `gh`, `acli` or `jira` command fails because of the sandbox, rerun it with escalation and a one-line justification. After each state-changing step, inspect the git or GitHub state before continuing.

## Codex parallel dispatch

An invoked Ship It umbrella explicitly requests parallel issue workers and nested gate delegation. Use fresh context (`fork_turns: "none"` when available), a distinct worktree per issue and the capacity leases in [orchestration.md](orchestration.md). Follow the tools actually exposed: some hosts provide `collaboration.spawn_agent` and `wait_agent`, others expose different native names. Do not implement issues sequentially merely because tool calls must be submitted separately; a spawn returns while its worker runs, so submit the other eligible spawns before waiting. Local Codex configuration cannot override a host-supplied concurrency budget.
