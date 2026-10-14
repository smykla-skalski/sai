# Ship It worker rules

- Own one child issue and its assigned worktree through merge and closure.
- Read the ship-it entry once and each selected phase reference once. After compaction, read only the checkpoint and current phase reference.
- Never fork coordinator history. Give each gate its mandate once in a fresh context.
- Read [authorization.md](authorization.md) before acting; retain original user authorization, scoped approval replies, limits, consumed allowances and revocations through handoffs. Internal budget exhaustion triggers focused acceptance triage within that authorization, never another request for the same permission.
- Keep the checkpoint current. Send interim status only when the coordinator asks.
- At 100,000 cumulative input tokens, checkpoint and hand off to a fresh worker for the same child.
- Send one final hand-back with checkpoint path, PR, gated head, merge commit, issue state and blocker or completion result.
