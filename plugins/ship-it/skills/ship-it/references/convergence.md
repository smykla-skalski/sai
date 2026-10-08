# Bounded validation convergence

Use [convergence-policy.json](convergence-policy.json) directly in Claude Code, Codex, OpenCode and Sail. Do not translate it into harness-specific limits. Start the elapsed budget when the first review worker is dispatched and persist the selected mode, start time, review-cycle count, fix-pass count and full-quality-gate count in the durable checkpoint.

## Default bounded mode

Routine work gets one review cycle: one Code Adversary pass followed by one independent Findings challenge. Batch every surviving blocking finding into at most one fix pass. During that pass, run focused tests for the changed behavior and each reproduced failure. Run the repository's complete local quality gate once against the final candidate revision before delivery.

A source-changing fix does not by itself start another adversarial review or broad manual-test pass. Re-attest the new revision from the independent findings record, the focused fix verification and the final quality gate. Start a second and final review cycle only when the fix touches security, risks data loss, changes destructive concurrency, or leaves an acceptance criterion unresolved. The second cycle has the same one-Code-pass and one-Findings-challenge shape.

When the single fix pass is spent, convert later non-blocking findings into follow-up issues and continue delivery. Never defer a repository-required check, mandatory human approval, unresolved acceptance criterion, security defect, data-loss risk or destructive-concurrency defect. If one of those remains unresolved, or a second review cycle or 90 elapsed minutes would be exceeded, stop with the exact blocking condition and next human action.

Review, manual testing, CI fixes and hosted-review feedback share these counters. They do not each reset the budget. An ordinary later suggestion becomes a follow-up issue. A reproduced test or CI failure is an unresolved acceptance failure and may enter the second cycle; if it cannot be resolved inside the remaining budget, stop instead of claiming success.

## Copilot and repository controls

Never wait for Copilot. Ignore optional Copilot requests, comments, quota failures and missing reviews. If repository policy explicitly requires Copilot, immediately activate its configured non-Copilot fallback; when no compliant fallback exists, hard-stop with the policy action required instead of polling. Continue waiting for repository-required checks and mandatory non-Copilot human review within their existing hosted-gate deadlines.

The convergence budget never bypasses repository checks, permissions, commit signatures, branch protection, merge policy or mandatory human review. Those controls remain release gates even after the time or cycle budget is exhausted.

## Exhaustive opt-in

Use `exhaustive` mode only when the user's current request explicitly asks for exhaustive review. Repository risk level, a complex diff or agent preference does not activate it. Record the exact authorization and user-directed limits in the checkpoint. Without explicit limits, ask once before exceeding the bounded mode; do not infer an unlimited loop.

## Completion signal

Treat merged pull requests and closed issues as completion metrics. Review iterations are diagnostic only and never a reason to extend an otherwise complete run.
