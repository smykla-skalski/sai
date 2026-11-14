# Optional T3 Code integration

Load this reference only when the connected tools expose T3 Code's `delegate_task` and `orchestrator_capabilities` (under any MCP server prefix). Runtime notes, a task name or a transcript that mentions T3 Code do not establish the connection.

T3 Code changes only how gate executions are routed. Phases, gates, verdicts, convergence budgets, checkpoints and evidence stay as the phase references define them.

## Cross-provider gates

Review, testing and CI-triage executions run on a different model provider than implementation, so a gate does not share the implementer's blind spots. Exploration and implementation keep the current execution.

1. Call `orchestrator_capabilities` once per run before the first gate dispatch, and again only after a delegate error. The implementation provider is `inheritedProviderInstanceId`; for an issue worker it is the worker's own provider.
2. Choose the gate provider: a provider with `canRunChildTask: true`, `canRunCrossProviderChildTask: true`, no `constraints` and at least one listed model, whose `driverKind` differs from the implementation provider's. Prefer `codex` when implementation runs on `claudeAgent`, and `claudeAgent` when it runs on `codex`; otherwise take the first eligible provider in the listed order.
3. Choose the model: an explicit user or repository selector when given, otherwise the provider's first listed model. Choose the variant: `high` for the model's reasoning option (`reasoningEffort` on Codex, `effort` on Claude) when that value is listed, otherwise leave the option out and the provider default applies.
4. Record the requested selector as `provider: cross-provider` with the chosen model and variant, and resolve `actual` from the delegate's returned provider instance and model. Use mechanism `native-subagent`.
5. An explicit user or repository selector overrides the cross-provider default and follows [roles.md](roles.md): never substitute it silently.
6. When no eligible different provider exists, or its launch fails, append a `routeDiagnostics` entry with the rejected cross-provider selector and reason `unavailable-mechanism`, then route the gate to a fresh same-provider execution: `delegate_task` without `target`, else the harness's native subagent. Record that route with `requested.provider: default`, `independence: degraded` and `degradationReasons: ["cross-provider-unavailable"]`, and list the fallback in the PR body. A missing fresh execution still blocks the gate.

## Dispatch

Start one `delegate_task` per gate execution: each Code Adversary pass, each Findings Adversary pass, each tester attempt, each reproduction rerun and each CI triage. Never reuse a finished child with `t3_thread_send`; that reuses its context and does not satisfy the gate.

- `role`: `review` for Code and Findings Adversaries, `test` for testers and reproduction reruns, `research` for CI triage.
- `isolation: "worktree"`: the child gets its own checkout of the parent's current commit. Commit every gated change before dispatch; uncommitted edits stay out.
- `target`: the chosen `providerInstanceId`, `model` and `options`. Leave `runtimeMode` unset.
- `title`: the gate and dispatch ID, for example `ship-it review code-adversary <dispatch ID>`.
- `task`: the role mandate inline, then repository, branch, base ref, gated head SHA, PR URL, changed files, checkpoint path, dispatch ID, pinned `bundle` and `skillRoot`, and the exact verdict line the phase reference requires. Use the body of the matching installed persona (`adversarial-review` `references/code-adversary.md` or `references/findings-adversary.md`, `adversarial-test` `references/test-adversary.md`) as the mandate when it is readable, else the generic mandate from the phase reference. Never include secrets, coordinator reasoning or the Code Adversary's reasoning for the Findings Adversary.
- Tell the child: first verify `git rev-parse HEAD` equals the gated head and report a `Gate failure:` line otherwise; never edit tracked files, commit, push, comment on the PR or merge; do not delegate further.

Persist the dispatch ID and register worker recovery under [worker-events.md](worker-events.md) before the call, then bind the returned `taskId` as the execution identity. Use `mode: "async"` and follow the returned `next` for the single event waiter; never poll with `task_status`, sleeps or watchers. Within one review, start the Findings Adversary only after the Code Adversary's verdict is accepted. Cancel a child that is no longer needed with `task_cancel`; release its owner only after T3 Code reports it completed or cancelled. Each delegated child occupies one slot of the shared capacity budget in [orchestration.md](orchestration.md). T3 Code owns the children's worktrees and their cleanup.

An issue worker without T3 Code tools sends its gate request to the coordinator, which dispatches the gate under this reference and returns the verdict; implementation ownership stays with the worker.

## Evidence

Record the actual producer in enabled evidence or checkpoint `gateVerdicts`: provider `codex` for a Codex child, `claude-code` for a Claude child, and the child's concrete model. A child whose actual provider or model differs from the requested selector is a post-dispatch `routeDiagnostics` entry, and its verdict does not satisfy the gate.
