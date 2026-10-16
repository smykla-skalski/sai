# Meaningful worker events

Register local worker recovery with `bookkeeping.py record-worker-event` after the native identity is known and before waiting. Reuse the issue worker's orchestration dispatch ID and issue URL; bind a gate to its pending reservation ID. The worker records `started` on entry and a durable `result` receipt before sending its terminal message. See [checkpoint.md](checkpoint.md#worker-recovery-commands).

After suspension or reconnect, run `reconcile-workers` with the observed UTC resume time before downstream work. Read and reconcile an unacknowledged result's checkpoint, then acknowledge its event ID. A worker receipt never attests a passing gate or closes an issue. `queued-unobserved` means no durable entry observation; `executing-observed` records entry, not current process health. `completed-but-undelivered` means a durable receipt lacks acknowledgement, regardless of native mailbox state. Correlated runtime traces are still required to distinguish provider silence, suspended execution and queued native delivery.

UTC deadline expiry requires ownership reconciliation, never success, more authority or timeout reassignment. Retain active or unknown owners. Record `release-owner` only after the native host reports `closed` or `exited`, retaining its observation; interruption requests, timeouts and missing replies are insufficient. A held owner blocks orchestration redispatch and a new reservation of the same gate kind. This helper cannot wake a stalled native model; it recovers receipts when the parent executes again. Receipt storage is bounded to 256 dispatches per run and fails closed at capacity without changing user limits.

Use this contract for implementation workers, gate subagents and hosted-state waiters. Give each fresh worker its applicable mandate exactly once. A same-context resume reads the checkpoint and only current-phase guidance missing from that context; never resend its mandate or coordinator history. A replacement handoff is a fresh context: give it the mandate once with the checkpoint and missing current-phase guidance.

Before launch, persist a stable dispatch ID from the task, role, revision and ordinal and an explicit deadline for every implementation, review, test and hosted-state dispatch. Launch every eligible dispatch before waiting. After launch, keep exactly one blocking event waiter for that dispatch; multiplex worker events so a wait for one dispatch never prevents another ready dispatch. Wake only for:

- completion or failure;
- a gate-capacity request or released capacity;
- cancellation or user input;
- the configured deadline;
- a hosted check, review or thread change for a PR waiter.

No event means continue the same wait. It triggers no progress message, agent listing, terminal read, checkpoint read or unrelated state query. A host-required progress update reports the last meaningful event and that the wait continues; producing the update performs no status read and does not restart the waiter.

When the harness has no event-driven wait, use one bounded fallback waiter per dispatch. Poll the declared target no more than once per ten minutes, stop at the configured deadline and never start an overlapping poller. Treat only a changed target snapshot as an event.

Give worker completion and failure events an identity scoped to their dispatch. Scope cancellation and user-input controls to the run, process them before filtering stale dispatch events, and atomically record them in the checkpoint. An accepted cancellation stops active waiters and forbids any later gate or delivery action. Before a worker terminal event starts the next gate or delivery, atomically record its identity and terminal state. Ignore duplicate worker events, worker events for an older dispatch and delayed terminal events after the worker is terminal; resume waiting for the active dispatch. Close a worker once after its accepted terminal event when supported. Release capacity according to the host: if finished open threads still count and no close mechanism exists, retain their slots and stop dispatch when capacity is exhausted; report the missing thread-release capability. Never pretend an occupied slot is free.
