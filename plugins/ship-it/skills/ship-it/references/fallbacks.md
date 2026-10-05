# ship-it fallbacks for other agents

ship-it is written for Claude Code. On Codex, opencode or Copilot CLI, or when a Claude feature is missing, use these fallbacks. In Sail mode, the inline review/test fallback below is forbidden: pause if a required worker or gate subagent cannot launch.

## Agent compatibility

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | Claude Code appends the arguments to the skill. If none are appended, take the description, URL and flags from the user's request |
| ToolSearch (Jira via Atlassian MCP) | Codex, Copilot CLI, opencode: use Atlassian MCP tools only when the session already lists them. No MCP tools: use the `acli` or `jira` CLI |
| Skill tool (review and test gates) | Codex: invoke `$adversarial-review` and `$adversarial-test` (plugins `adversarial-review@sai`, `adversarial-test@sai`) with the same arguments. Copilot CLI: `/adversarial-review`, `/adversarial-test`. opencode: load the skill of the same name. Not installed: run the passes in "Review and test mandates" below yourself |
| Named agents `adversarial-review:code-adversary`, `adversarial-review:findings-adversary`, `adversarial-test:test-adversary` | Registered only where their plugin is installed in Claude Code or Copilot CLI. Codex and opencode do not register them; there, or whenever the type is unknown, spawn a generic subagent (`general-purpose`) with the mandate below |
| Subagent tool (Agent) | Codex: `spawn_agent`, waited on and closed before the next pass. opencode: the `task` tool. Copilot CLI: its agent tool. Within each review, the Findings Adversary starts only after the Code Adversary returns. Outside Sail, no subagent tool means running each pass inline in order and rereading the source for refutation. In Sail, pause instead |
| AskUserQuestion | Not used; a hard-stop question or a request to paste a Jira ticket goes to the user as plain text, then end the turn |
| `context: fork` | Not used |
| Explicit invocation | ship-it pushes, merges and closes issues, so it runs only when the user invokes it by name. Codex enforces this through `agents/openai.yaml` (`allow_implicit_invocation: false`). On other agents, start only when the user asked to ship a change or invoked `/ship-it` or `$ship-it` |

## Sandboxed agents

On agents with a command sandbox (Codex), the user's request to ship the change authorizes normal branch, commit, push, PR, review-reply, merge and issue-close actions in the target repository. If a networked `git`, `gh`, `acli` or `jira` command fails because of the sandbox, rerun it with escalation and a one-line justification. After each state-changing step, inspect the git or GitHub state before continuing.

## Sail worker and gate availability

An explicit Sail-managed worktree or worker assignment establishes Sail mode. An orchestration parent must use actual Sail worker sessions and their assigned worktrees. A single-issue Sail worker stays on its assigned branch. Before dispatch or gate execution, confirm the required native subagent capability is available. A failed launch pauses the affected work with the missing capability named; never run implementation in the parent or either review/test gate inline. Independent workers may be concurrent; the Code and Findings Adversaries within one review remain sequential.

## Review and test mandates

Use these when the `adversarial-review` or `adversarial-test` skill is not installed. Inputs for every subagent: the repository path, the diff command (`git diff origin/<default>...HEAD`), the changed files, and the task context file.

### Code review (two passes, in order)

1. Code Adversary: spawn `adversarial-review:code-adversary`, or a generic subagent told to assume the change is broken, hunt concrete failures including unmet acceptance criteria, and prove each finding with a failing input, `file:line`, and a fix. Findings are labeled `blocking:`, `issue:` or `question:`.
2. Findings Adversary: spawn a **new** `adversarial-review:findings-adversary`, or a new generic subagent told to refute each finding against the source. Give it the same inputs plus only the numbered findings, never the first agent's reasoning.

The verdict is `NEEDS_FIXES` when any `blocking:` or `issue:` survives the refutation, otherwise `CLEAN`.

### Manual test

Spawn `adversarial-test:test-adversary`, or a generic subagent told to prove the change does not satisfy the task by running the real changed product surface (service + probe, real CLI, sandbox) in isolated temp state, attacking happy paths, boundaries, malformed input, repeated or concurrent use, and adjacent flows, and to report self-contained reproductions. Automated tests, lint, build and grep count only as supporting evidence. Rerun each reproduction yourself before acting on it to drop false failures.

The verdict is `FAIL` when a reproduction survives the rerun, `BLOCKED` when testing needs a human action (name it), otherwise `PASS`.
