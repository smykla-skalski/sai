# Meaningful worker events

Use this contract for implementation workers, gate subagents and hosted-state waiters. Give each worker its applicable mandate once in fresh context. A resume or handoff reads the checkpoint and only current-phase guidance missing from that context; never resend the mandate or coordinator history.

Before launch, persist a stable dispatch ID from the task, role, revision and ordinal. After launch, keep exactly one blocking event waiter for that dispatch. Wake only for:

- completion or failure;
- cancellation or user input;
- the configured deadline;
- a hosted check, review or thread change for a PR waiter.

No event means continue the same wait. It triggers no progress message, agent listing, terminal read, checkpoint read or unrelated state query. A host-required progress update reports the last meaningful event and that the wait continues; producing the update performs no status read and does not restart the waiter.

When the harness has no event-driven wait, use one bounded fallback waiter per dispatch. Poll the declared target no more than once per ten minutes, stop at the configured deadline and never start an overlapping poller. Treat only a changed target snapshot as an event.

Give every event an identity scoped to its dispatch. Before a terminal event starts the next gate or a delivery action, atomically record that identity and the terminal state in the checkpoint. Ignore duplicate events, events for an older dispatch and delayed terminal events after the worker is terminal; resume waiting for the active dispatch. Close a worker once after its accepted terminal event.
