# Fresh phase continuations

Hand off after draft publication (destination `review`) and after selected review/test gates pass (destination `pr`), including low-risk runs with no manual test. Each boundary occurs once per task. A continuation owns the remaining lifecycle; the outgoing worker stops writes once the successor accepts. This transfers ownership; it is not a validation gate and consumes no validation allowance.

## Prepare

- Include pinned plugin `bundle`, `skillRoot`, store and sender lease in the brief. The receiver acquires its own active-run lease before helper resolution or acceptance; the sender releases its lease only after that acquisition and accepted ownership. On launch failure or fallback the sender retains its lease. Never change checkpoint authority or budgets when pinning a continuation.

- Persist phase, exact head, PR identity, next action, authorization grants and completed gate receipts through bookkeeping before dispatch. Retain claims, evidence paths, convergence counters, release policy and gate verdicts in the same checkpoint. Never create a replacement checkpoint or stale verdicts solely because the worker changes.
- Record `bookkeeping.py handoff --checkpoint FILE --handoff-json '{"id":"draft-1","boundary":"draft-published","status":"pending","brief":"..."}'`. At the second boundary use a new stable ID and `boundary: before-pr-loop`. Retries reuse the receipt and ID. Interrupted pending receipts resume from that boundary.
- The brief contains only checkpoint path, worktree, boundary, next action, durable artifact paths and scoped exceptions requiring attention. Keep it below 2,000 tokens. The helper enforces at most 1,999 UTF-8 bytes, a conservative tokenizer-independent limit. Original authorization stays in the checkpoint.
- Spawn a fresh agent with no inherited conversation (`fork_turns: none` on Codex). Supply the brief and this continuation mandate only. Request coordinator capacity when supervised. Do not forward implementation transcripts, full diffs, repeated skill text or gate logs.

## Accept and continue

- Read the checkpoint first, reconcile original authorization and live delivery, then load only the destination phase reference and missing applicable repository instructions. Do not repeat completed phases or broad gates. Apply existing validity rules when source, runtime or policy inputs actually change.
- Start under 25,000 input tokens including host/system instructions, brief and loaded guidance. Use the host input count; if unavailable, conservatively bound the complete startup input using UTF-8 bytes. Unknown hidden startup instructions cannot establish the bound.
- Before taking ownership, acknowledge the same ID/boundary with `status: accepted`, a fresh `worker` identity and verified `inputTokens` count (or conservative byte upper bound). The helper rejects counts of 25,000 or more. Report acceptance to the outgoing owner/coordinator, then continue from `workflow.nextAction`. For enabled claims, reconcile the live unexpired claim and receipt `claimBinding` before acceptance. Resume the same logical task holder under the explicit cooperative-continuation rule in [claims.md](claims.md), retaining its comment and evidence binding while recording the fresh execution separately. Only the accepted successor renews or releases that holder.
- Before resending a pending dispatch, reconcile whether its successor is alive. A live successor remains sole owner. After acceptance, an interrupted successor resumes from the checkpoint without repeating the boundary handoff.

## Host fallback

When no fresh agent can start, no capacity can be released, or the startup bound cannot be established, continue in place and record the same ID/boundary with `status: fallback` and a concrete `reason`. A capacity queue alone is not a capability failure: use coordinator scheduling first. Record fallback only after verifying no successor owns the task. Failed launches never consume gates or reset budgets. This lifecycle fallback never waives independent review/test agents; missing gate agents still block those gates.

Never acknowledge before the successor starts, invent token counts, clear gate evidence or conceal an oversized continuation with fallback.
