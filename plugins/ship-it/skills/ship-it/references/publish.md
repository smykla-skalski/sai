# Publish the draft PR

Publish after selected local checks pass for committed `HEAD`. Apply enabled claims. Verify local evidence or checkpoint verdicts; review and testing remain due before ready.

Push without rewriting history and create a **draft** PR. Its body follows the repository template and identifies the source, risk, diff class, selected gates and current revision. Mark review and test as pending. Store the PR URL and `headRefOid` in the checkpoint before dispatching either gate.

Then apply [handoff.md](handoff.md) at `draft-published`.

Start one background CI waiter for the PR and let review run concurrently with it. A CI failure that arrives before the single fix pass is complete joins the same batched fix. Never start manual testing before review is clean for the same revision.

Keep the draft while review, test or required CI is pending. Fixes push ordinary commits, update the checkpoint head and assess local input validity. Carry verified unaffected results; CI follows live revision policy. Never force-push or rebase after first push.
