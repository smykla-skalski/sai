# Completing the shipped task

Confirm the PR is merged and record its merge commit. Apply the checkpoint's resolved issue-closing behavior: verify keyword closure, close manually only when policy says `manual-after-merge`, or preserve the source state for `unchanged`. Leave Jira unchanged unless the user explicitly requested otherwise.

For a GitHub implementation issue with claims enabled, release the current work claim with reason `merged` after the merge and issue state are verified. Reread the released comment and store it in the checkpoint before finalizing. On explicit cancellation or terminal failure, release with the matching reason before reporting when GitHub remains reachable. With claims disabled, keep `claim: null` and perform no claim write.

Cancellation and terminal failure are durable terminal outcomes. After releasing the claim, set `phase: complete`, set status to `cancelled` or `failed`, clear the blocker and next action, and record the reason, unchanged source state and completion time in `outcome`. A later run reports that outcome and stops unless the user explicitly restarts it through the checkpoint recovery contract.

Finalize the durable checkpoint only after those checks succeed, release-policy closure and branch cleanup are verified, and any enabled GitHub claim is released. With evidence enabled, its pointer must identify the complete record for the gated PR head. With evidence disabled, the checkpoint must contain every selected gate verdict bound to that exact head. Set `phase` to `complete`, `status` to `completed`, clear `blocker` and `unresolvedQuestions`, set `nextAction` to `none`, and atomically write the final `outcome` with `bookkeeping.py transition --outcome-json`. Preserve the completed checkpoint and any enabled evidence record as the cross-harness delivery record.

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

Return to the default branch and remove the task worktree only when safe and when the current harness owns that cleanup. A Sail worker reports completion and leaves its assigned worktree lifecycle to Sail.
