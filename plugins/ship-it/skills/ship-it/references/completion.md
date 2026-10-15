# Completing the shipped task

Confirm the exact reconciled PR is merged and retain its head, merge commit and `mergedAt` as delivered even when compliance or cleanup audit remains. Query the source issue separately, then apply the resolved issue-closing behavior: verify keyword closure, close manually only for `manual-after-merge`, or preserve `unchanged`. Leave Jira unchanged unless the user explicitly requested otherwise.

For a GitHub implementation issue with claims enabled, release the current work claim with reason `merged` after the merge and issue state are verified. Reread the released comment and store it in the checkpoint before finalizing. On explicit cancellation or terminal failure, release with the matching reason before reporting when GitHub remains reachable. With claims disabled, keep `claim: null` and perform no claim write.

Cancellation and terminal failure are durable terminal outcomes. After releasing the claim, set `phase: complete`, set status to `cancelled` or `failed`, clear the blocker and next action, and record the reason, unchanged source state and completion time in `outcome`.

Finalize the durable checkpoint only after those checks succeed, release-policy closure and branch cleanup are verified, and any enabled GitHub claim is released. With evidence enabled, its pointer must identify the complete record for the gated PR head. With evidence disabled, the checkpoint must contain every selected gate verdict bound to that exact head. Set `phase` to `complete`, `status` to `completed`, clear `blocker` and `unresolvedQuestions`, set `nextAction` to `none`, and atomically write the final `outcome` with `bookkeeping.py transition --outcome-json`.

When telemetry is enabled, finish the run and attach its privacy-safe cost aggregate to the merged PR as specified in the already-loaded telemetry guidance. Include the plugin version so cost per merged PR can be compared across skill versions. A publication failure is a separate audit diagnostic and never rewrites confirmed delivery. With telemetry disabled, create no cost report or PR cost comment.

Report:

- task source and PR URL
- commits and merge commit
- selected hosted-gate results, resolved release-policy source and required thread status
- selected risk level, diff class and gate set
- selected review and test verdicts with the gated PR head SHA
- completion evidence path and status, or checkpoint verdict status when evidence is disabled
- GitHub issue closure or unchanged Jira status
- any review or test round-cap overrun

Judge completion by the merged pull request and resolved source issue. Review-cycle counts are diagnostic only and never justify extending a delivery whose required controls already passed.

Return to the default branch and remove the task worktree only when safe and when the current harness owns that cleanup. Assigned workers report completion; the host owns their worktree cleanup.
