# Optional Sail integration

Load this reference only when the connected tools expose Sail integration. A task name, repository path, historical transcript or mention of Sail does not establish that connection. Without connected tools, use the portable workflow without loading this reference or probing Sail.

## Assigned workers and gates

- An orchestration parent launches actual Sail worker sessions in distinct assigned worktrees. A child verifies its assigned branch and worktree and never changes the host assignment.
- Resolve provider, model and variant through the connected worker capabilities. Route review and manual testing to fresh gate workers with independent contexts; the Code and Findings Adversaries remain sequential within one review.
- Check required worker and gate capabilities before dispatch. A missing capability or failed launch pauses the affected issue with the exact unavailable capability and next action recorded. Never implement a child in the parent, run review or testing inline, or substitute automated tests for manual testing.
- Share the host capacity budget with descendants and release a lease only when the host confirms its execution no longer consumes capacity.

## Checkpoint mirroring and claims

- The portable JSON checkpoint remains authoritative. Mirror its phase, status, branch, revision, PR URL, gated head, blocker and next action into Sail's connected task/session state after each successful durable transition.
- Use the connected tool's documented schema; never invent tool names or rewrite checkpoint JSON through Sail. Report a mirror failure separately and retain the durable checkpoint for retry.
- Preserve original user authorization and consumed allowances through worker handoffs. Sail state cannot widen permission or reset validation budgets.
- Claims follow the resolved portable bookkeeping policy. With claims disabled, create no claim. With claims enabled, use the stable Sail worker identity as the session component and reconcile the authoritative GitHub claim before writes. A Sail assignment alone is no lease.

## Progress and merge handoff

- Send task progress through connected Sail task/session tools when available: phase transitions, accepted worker events, capacity requests/releases, blockers and terminal outcome. Follow the portable event contract; do not add foreground polling or periodic status reads.
- Publish the draft and retain its exact head in both durable and mirrored state. Resolve selected local gates, required hosted checks and existing review comments before ready or merge.
- When the connected host owns merging, hand off the PR URL, gated head, gate results, unresolved-thread count and requested repository merge action. Record a handoff as pending delivery; it is never proof of merge.
- Otherwise follow repository merge policy directly. Verify the authoritative merged PR and source issue state before completion, then mirror the merge commit and terminal result. Leave assigned worktree cleanup to Sail.

## File delivery

A host that delivers references and helpers individually follows [helper-loading.md](helper-loading.md). Preserve relative paths and retrieve transitive imports and policy resources before invoking Python. Do not assume an entire plugin directory was installed.
