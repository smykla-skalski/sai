# Self-check and cold-read gate

Two checks sit between the draft and the user. The self-check always runs and costs nothing extra. The cold-read gate runs a separate reviewer and only above a size or risk threshold, because no controlled study shows a net benefit, detection of underspecification by an LLM is unreliable, and extra review passes multiply token cost. Evidence and the unproven parts are in [evidence.md](evidence.md).

## Self-check (always)

Run it yourself on the draft, with no extra agent. Fix the draft, or add to Open items, until every line holds:

- Every outcome names a runnable check or an example input and output.
- No acceptance check can be passed by only one implementation.
- Non-goals and task-specific Do-not lines are stated, or you decided none apply.
- Every file, symbol and command named was verified in this session. No line numbers.
- Any cause is labelled with the check that supports it, or marked as a hypothesis.
- Premise confirmed on the default branch; duplicates searched.
- Each locked choice is marked, and each one-way door has a stop trigger.
- No repo-wide rule restated that the root instruction file already holds.
- Unverified assumptions are listed in Open items, not written as facts.

## Cold-read gate (threshold)

Run the review when any condition holds, or `--cold-read` was passed. Skip it for `--no-cold-read`, and skip it when the diff fits in one sentence and the draft already has a runnable check and verified anchors.

The numeric cut-offs below are heuristics, not measured values.

- The diff cannot be described in one sentence **and** it spans three or more files or modules, or about an hour or more of human work.
- Failure is expensive or hard to reverse: a public API, a schema, a migration, authorization, infrastructure, or an unattended or background run.
- The Open items list holds unverified assumptions, or the intent is second-hand (pasted context, a vague request).
- The work is the parent of a fan-out to several agents. Gate the parent or the largest child once, not each child.

## Reviewer

One reviewer, fresh context, one round. A second round only if the first changed scope or the outcomes. Never more than two.

Give the reviewer the issue text and read-only access to the repository. Do not give it the author's notes, the conversation or the research. Ungrounded review misfires about half the time, so repo access matters; author context defeats the point.

Prompt for the reviewer (pass it verbatim, with the issue text appended):

```text
You are about to implement the issue below. You have read-only access to the repository and no other context. Do not edit anything.

Return exactly these four parts:

1. Restatement: what you would build, in five sentences or fewer.
2. Diff boundary: the files you would touch and the files you would deliberately not touch.
3. Questions: only where two plausible readings of the issue would lead to materially different work. For each, give both readings and tag it BLOCKING or NON-BLOCKING. If there are none, write "none".
4. Checklist, answering yes or no with one clause of evidence each:
   - Is every outcome checkable by a command, test or example you could run?
   - Is out of scope stated or clearly unneeded?
   - Do the named files and symbols exist?
   - Do any two statements in the issue contradict each other or an existing test?

Report everything you notice, tagged. Do not soften or filter your findings, and do not suggest improvements beyond these four parts.
```

Do not tell the reviewer to be conservative or to report only high-severity items; strong recent models may follow that literally and under-report. Tag instead, and filter in the next step.

### Subagent or inline

| Situation | What to do |
| :-- | :-- |
| A subagent tool exists (Claude Code, Copilot CLI, others that have one) | Spawn one generic read-only subagent with the prompt above and the issue text |
| Codex, opencode, or no subagent tool | Run the review inline: write the restatement and boundary from the issue text only, without consulting your research notes, then answer the checklist by reading the repository. Say in the gate result that independence is reduced |
| The user wants true independence and none is available | Save the draft to the scratch directory and tell the user the prompt above can be run in a fresh session. Continue without it |

Codex subagent fan-out can be unreliable; one inline pass is the safe default there.

## Reading the result

You are the filter, not the reviewer. Compare the restatement and boundary to your intent.

- **Edit the issue** when the restatement or boundary diverges from intent, when a BLOCKING question names two readings you had not resolved, or when a checklist answer is no.
- **Drop** NON-BLOCKING items and suggestions that widen scope. A reviewer asked for gaps reports some even in sound work, and chasing every finding leads to over-engineering.
- **Every question the reviewer asks is a spec defect** only if it is BLOCKING. Resolve it in the issue, or move it to Open items for the user.
- If the first round changed scope or outcomes, run one more round. Otherwise stop.

Report the gate result to the user in one line: ran or skipped, why, what changed.
