# Meaningful worker events

Use this contract for implementation workers, gate subagents and hosted-state waiters. Give each fresh worker its applicable mandate exactly once. A same-context resume reads the checkpoint and only current-phase guidance missing from that context; never resend its mandate or coordinator history. A replacement handoff is a fresh context: give it the mandate once with the checkpoint and missing current-phase guidance.

Before launch, persist a stable dispatch ID from the task, role, revision and ordinal and an explicit deadline for every implementation, review, test and hosted-state dispatch. After launch, keep exactly one blocking event waiter for that dispatch. Wake only for:

- completion or failure;
- cancellation or user input;
- the configured deadline;
- a hosted check, review or thread change for a PR waiter.

No event means continue the same wait. It triggers no progress message, agent listing, terminal read, checkpoint read or unrelated state query. A host-required progress update reports the last meaningful event and that the wait continues; producing the update performs no status read and does not restart the waiter.

When the harness has no event-driven wait, use one bounded fallback waiter per dispatch. Poll the declared target no more than once per ten minutes, stop at the configured deadline and never start an overlapping poller. Treat only a changed target snapshot as an event.

Give worker completion and failure events an identity scoped to their dispatch. Scope cancellation and user-input controls to the run, process them before filtering stale dispatch events, and atomically record them in the checkpoint. An accepted cancellation stops active waiters and forbids any later gate or delivery action. Before a worker terminal event starts the next gate or delivery, atomically record its identity and terminal state. Ignore duplicate worker events, worker events for an older dispatch and delayed terminal events after the worker is terminal; resume waiting for the active dispatch. Close a worker once after its accepted terminal event.
