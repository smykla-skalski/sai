# Publish the draft PR

Publish after the first committed revision passes every selected local check. Claims apply only when enabled by bookkeeping policy. Validate the local-check evidence record or checkpoint gate verdict for the exact `HEAD`; review and manual-test results may remain pending until the ready gate.

Push without rewriting history and create a **draft** PR. Its body follows the repository template and identifies the source, risk, diff class, selected gates and current revision. Mark review and test as pending. Store the PR URL and `headRefOid` in the checkpoint before dispatching either gate.

Start one background CI waiter for the PR and let review run concurrently with it. A CI failure that arrives before the single fix pass is complete joins the same batched fix. Never start manual testing before review is clean for the same revision.

Keep the draft while review, test or required CI is pending. Fixes push ordinary commits, update the checkpoint head and assess local input validity. Carry verified unaffected results; CI follows live revision policy. Never force-push or rebase after first push.
