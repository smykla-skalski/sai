# Durable ship-it checkpoint

Use one portable JSON checkpoint as the source of truth for a task across Claude Code, Codex, OpenCode, Copilot CLI and Sail. It is both resumable workflow state and the task context supplied to review and test gates.

## Location and identity

Resolve the data root once as `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/checkpoints/`. Create it with owner-only permissions. Never store checkpoints in a repository, plugin cache or system temporary directory.

Normalize a repository identity from `remote.origin.url`: convert SCP-style SSH to its URL host/path form, lowercase the host and case-insensitive forge path, and remove credentials, query, fragment, trailing slash and `.git`. When no remote exists, resolve `git rev-parse --git-common-dir` against the repository, then use its physical absolute path. Linked worktrees therefore share an identity; independent no-remote clones cannot share a checkpoint automatically.

Canonicalize the task source before deriving its key:

- GitHub: lowercase host and owner/repository plus issue number, for example `github:github.com/owner/repo#154`.
- Jira: lowercase site host plus uppercase key, for example `jira:example.atlassian.net/ABC-12`.
- Description: normalized repository identity plus the exact resolved objective and acceptance criteria.

Encode the canonical source as compact JSON with lexicographically sorted object keys and UTF-8 text: `{sourceType, repository, issue}` for GitHub, `{sourceType, site, key}` for Jira, or `{sourceType, repository, objective, acceptanceCriteria}` for a description. Store that exact JSON serialization as the `task.canonicalSource` string. The checkpoint ID is the lowercase hexadecimal SHA-256 digest of those exact bytes. Store the document as `<checkpoint-id>.json`. This makes the same task resolve to the same file across worktrees and harnesses. Treat a hash collision or an existing file with another canonical source as a mismatch and stop.

## Format

Write UTF-8 JSON with these fields. Preserve unknown fields so a newer harness can safely add data.

```json
{
  "schemaVersion": 1,
  "checkpointId": "64 lowercase hexadecimal characters",
  "task": {
    "sourceType": "github|jira|description",
    "canonicalSource": "canonical source used for the ID",
    "sourceUrl": "URL or null",
    "title": "resolved task title",
    "objective": "resolved outcome",
    "acceptanceCriteria": ["testable criterion"]
  },
  "repository": {
    "identity": "normalized remote or absolute path",
    "defaultBranch": "main",
    "branch": "current task branch or null"
  },
  "workflow": {
    "phase": "resolve|orchestrate|explore|branch|implement|review|test|pr|complete",
    "status": "active|blocked|completed",
    "revision": "full commit SHA or null",
    "blocker": "specific blocker or null",
    "unresolvedQuestions": [],
    "nextAction": "one concrete action or none"
  },
  "delivery": {
    "pullRequestUrl": "URL or null",
    "pullRequestHead": "full commit SHA or null",
    "mergeCommit": "full commit SHA or null"
  },
  "evidence": {
    "revision": "full commit SHA or null",
    "recordPath": "absolute evidence record path or null",
    "status": "missing|collecting|complete|failed|blocked|stale",
    "updatedAt": "RFC 3339 UTC timestamp or null"
  },
  "claim": null,
  "orchestration": null,
  "outcome": null,
  "createdAt": "RFC 3339 UTC timestamp",
  "updatedAt": "RFC 3339 UTC timestamp"
}
```

For a single change, `outcome` is an object with `result: merged`, `pullRequestUrl`, `pullRequestHead`, `mergeCommit`, `sourceState` (`closed`, `unchanged` or `not-applicable`) and `completedAt`. For orchestration it has `result: coordinated`, `umbrellaUrl`, each child's final PR head and merge commit, `sourceState: closed` and `completedAt`. Use JSON `null`, never an empty string, for unknown optional values. Timestamps use `Z`; commit IDs are full hexadecimal SHAs.

`orchestration` is null for a single change. For an approved plan or umbrella, it is an object with `umbrellaUrl` and a `children` array. Every child records `issueUrl`, dependency issue URLs, status, worker identity, worktree, branch, revision, `evidenceRevision`, `evidenceRecordPath`, `evidenceStatus`, gated head, PR URL, unresolved-thread count, merge commit, issue state and next action. Unknown optional values are null. This state supplements rather than replaces live GitHub and worker reconciliation.

`claim` is null for Jira and description sources. For a GitHub implementation issue it repeats the claim comment's `commentId`, `commentUrl`, `holder`, `status`, `acquiredAt`, `renewedAt`, `expiresAt`, `releasedAt`, `releaseReason` and `takeover`. Before the first comment, `status` may be `pending`, with a generated holder and null comment and lease fields; resume uses that holder for the acquisition attempt. Once a comment exists, the issue comment is authoritative and status is `active` or `released`. An umbrella coordinator keeps its own claim null and stores each worker's claim fields in that child's orchestration entry.

Validate these invariants in addition to field presence and types:

- `checkpointId` equals the filename and the digest of `task.canonicalSource`; `acceptanceCriteria` is non-empty.
- `status: blocked` has a non-empty `blocker` and actionable `nextAction`; other statuses have a null blocker.
- `status: completed`, `phase: complete` and a non-null `outcome` occur together; all other states have a null outcome.
- A merge commit requires a PR URL and PR head. A completed single-change outcome repeats the matching delivery values.
- Evidence is `missing` before the first task commit. Otherwise its revision and record path identify the current revision's valid evidence record; `complete` requires the exact workflow revision.
- An active GitHub implementation checkpoint has exactly one claim comment for its holder. Repository or GitHub writes require `status: active`, an unexpired `expiresAt`, and values reconciled with the authoritative issue comment. A completed checkpoint with a claim has released it with reason `merged`; a completed legacy checkpoint with `claim: null` remains valid after delivery verification.
- An orchestration checkpoint has one child entry for every native subissue; each dependency names another recorded child. A completed child has `evidenceStatus: complete`, and its evidence revision equals its gated PR head.
- `createdAt` never changes and is not later than `updatedAt`.

## Safe writes

Validate the complete next document before replacing state. Write it to a same-directory temporary file with owner-only permissions, flush and sync it, preserve the current valid file as `<checkpoint-id>.json.bak`, then atomically rename the temporary file over the checkpoint. Never update state before its associated operation succeeds. A failed write leaves the previous checkpoint authoritative.

## Creation and resume

On a fresh task, create the checkpoint with `phase: resolve`, `status: active`, no revision, and task resolution as `nextAction`. Then advance to `explore` only after the source and acceptance criteria are complete.

When the file exists, validate every required field and enum before using it. Do not silently repair or replace invalid state.

1. Recompute the ID from `task.canonicalSource`; it must match both `checkpointId` and the filename.
2. Compare the resolved task source and repository identity with the checkpoint. They must match exactly after normalization.
3. Reconcile Git before edits: current repository identity, default branch, task branch, `HEAD`, dirty files and ancestry.
4. For GitHub work, reread the issue, claim comment, linked PR and PR head. For Jira, reread its status without mutating it. Reconcile claim and delivery fields with that external state.
5. Update stale but unambiguous facts atomically, then continue from `workflow.nextAction` rather than replaying completed phases.

Safe reconciliation cases:

- `HEAD` equals the recorded revision: continue after external-state checks.
- `HEAD` descends from the recorded revision and every intervening commit belongs to this task: inspect it, update the revision, and invalidate review or test evidence from the older revision.
- The current evidence record matches `HEAD`: validate it and continue collecting only the results still pending for that revision.
- GitHub already shows the recorded PR merged: advance to completion verification using its actual head and merge commit.
- The issue is closed and its linked PR is merged: finalize only after verifying the merge contains the task revision.

## Recovery stops

Stop before repository changes and report the checkpoint path plus exactly one recovery action:

- Invalid JSON, missing required fields, bad enums or an ID mismatch: restore the `.bak` after inspecting it, or move the invalid file aside and explicitly restart the task.
- Different canonical source or repository identity: open the task in the matching repository, or explicitly start a distinct task; never rewrite identity in place.
- Recorded revision descends from the current `HEAD`, histories diverge, unrelated dirty files overlap, or intervening commits cannot be attributed: switch to the recorded task branch/worktree or reconcile the Git history manually.
- Open PR branch or head conflicts with the checkpoint: inspect the PR and choose the authoritative branch before resuming.
- Missing, expired, conflicting or mismatched GitHub claim: follow the claim contract's reconciliation or audited takeover flow; never rewrite ownership in the checkpoint alone.
- Missing, invalid or mismatched evidence: restore its `.bak` after inspection, or rerun the required evidence for the current revision; never advance with an older record.
- Closed issue without a verifiable merged PR, or merged PR that does not contain the recorded revision: inspect the external state and correct it before completion.
- `status: blocked`: perform the named `nextAction`; resume only after verifying the blocker is gone.
- `status: completed`: report the recorded outcome after checking it still matches GitHub. If the PR, merge or issue state no longer matches, stop and inspect that external state; do not reopen or overwrite the task.

Never infer success from an advanced phase name. Revision, PR, issue and merge facts must agree before advancing or finalizing.
