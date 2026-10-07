# Completing the shipped task

Confirm the PR is merged and record its merge commit. For a GitHub source, confirm the issue closed; when automatic closure failed, add a concise completion comment and close it. Leave Jira unchanged unless the user explicitly requested otherwise.

Finalize the durable checkpoint only after those checks succeed. Set `phase` to `complete`, `status` to `completed`, clear `blocker` and `unresolvedQuestions`, set `nextAction` to `none`, and write an `outcome` containing the final result, PR URL, gated PR head, merge commit, source state and completion time. Preserve the completed checkpoint as the cross-harness delivery record.

Report:

- task source and PR URL
- commits and merge commit
- CI result and Copilot thread status
- review and test verdicts with the gated PR head SHA
- GitHub issue closure or unchanged Jira status
- any review or test round-cap overrun

Return to the default branch and remove the task worktree only when safe and when the current harness owns that cleanup. A Sail worker reports completion and leaves its assigned worktree lifecycle to Sail.
