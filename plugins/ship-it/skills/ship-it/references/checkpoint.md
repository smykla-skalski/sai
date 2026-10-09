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
    "phase": "resolve|orchestrate|explore|branch|implement|publish|review|test|pr|wait|complete",
    "status": "active|blocked|completed|cancelled|failed",
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
    "status": "disabled|missing|collecting|complete|failed|blocked|stale",
    "updatedAt": "RFC 3339 UTC timestamp or null"
  },
  "claim": null,
  "bookkeeping": {
    "claims": false,
    "evidence": false,
    "telemetry": false,
    "policySource": "bundled default|repository path|explicit user request"
  },
  "risk": {
    "level": "low|medium|high|null",
    "diffClass": "docs|code|null",
    "policySource": "repository-relative path|bundled default|null",
    "matchedRules": [],
    "requiredGates": [],
    "overrideAuthorization": "exact user authorization or null"
  },
  "releasePolicy": null,
  "hostedReviewDecision": {
    "status": "not-required|serviceable|fallback|blocked",
    "reason": "bounded decision",
    "decidedAt": "RFC 3339 UTC timestamp"
  },
  "convergence": {
    "mode": "bounded",
    "authorizedBy": null,
    "startedAt": null,
    "reviewCycles": 0,
    "fixPasses": 0,
    "fullQualityGateRuns": 0,
    "reviewedRevision": null,
    "findings": [],
    "followUpIssues": []
  },
  "ciTriage": {
    "failures": []
  },
  "orchestration": null,
  "outcome": null,
  "createdAt": "RFC 3339 UTC timestamp",
  "updatedAt": "RFC 3339 UTC timestamp"
}
```

For a single change, a delivered `outcome` is an object with `result: merged`, `pullRequestUrl`, `pullRequestHead`, `mergeCommit`, `sourceState` (`closed`, `unchanged` or `not-applicable`), `branchCleanup` (`deleted`, `preserved` or `not-applicable`) and `completedAt`. A terminal undelivered outcome has `result: cancelled|failed`, null delivery fields, the unchanged source state, `branchCleanup: not-applicable`, a non-empty `reason` and `completedAt`. For orchestration it has `result: coordinated`, `umbrellaUrl`, each child's final PR head and merge commit, `sourceState: closed` and `completedAt`. Use JSON `null`, never an empty string, for unknown optional values. Timestamps use `Z`; commit IDs are full hexadecimal SHAs.

`orchestration` is null for a single change. For an approved plan or umbrella, it is an object with `umbrellaUrl` and a `children` array. Every child records `issueUrl`, dependency issue URLs, status, worker identity, worktree, branch, revision, `evidenceRevision`, `evidenceRecordPath`, `evidenceStatus`, gated head, PR URL, unresolved-thread count, merge commit, issue state and next action. Unknown optional values are null. This state supplements rather than replaces live GitHub and worker reconciliation.

`bookkeeping` is resolved from `.sai/ship-it-bookkeeping.json` or the current user's explicit request; the bundled default disables claims, revision evidence and telemetry. The checkpoint itself is mandatory in every mode. When claims are disabled, `claim` stays null and no claim comment is created. When evidence is disabled, the checkpoint records gate verdicts directly and its evidence status is `disabled`. When telemetry is disabled, no telemetry file or event is created.

With claims enabled, `claim` is null for Jira and description sources. For a GitHub implementation issue it repeats the claim comment's `commentId`, `commentUrl`, `holder`, `status`, `acquiredAt`, `renewedAt`, `expiresAt`, `releasedAt`, `releaseReason` and `takeover`. Before the first comment, `status` may be `pending`, with a generated holder and null comment and lease fields; resume uses that holder for the acquisition attempt. Once a comment exists, the issue comment is authoritative and status is `active` or `released`. An umbrella coordinator keeps its own claim null and stores each worker's claim fields in that child's orchestration entry.

`hostedReviewDecision` is written once after release-policy resolution and reused after compaction. `not-required` means no hosted reviewer is configured; `serviceable` names an available configured reviewer; `fallback` names the immediately activated policy fallback; `blocked` names the required reviewer and exact policy action. Never request or poll a reviewer after a quota, permission or unavailable-service result.

`ciTriage.failures` preserves CI observations that conform to `ci-triage.schema.json`. Failure IDs are unique. A failed CI result names its observations; resolution and recurrence remain recorded after a rerun, provider recovery or source-changing fix. Unknown fields in a triage record are preserved for forward compatibility.

`convergence` is the shared cross-harness budget state. In bounded mode, `authorizedBy` is null, `startedAt` is set when the first review worker starts, counters are monotonic, and follow-up issue URLs are unique. `reviewCycles` counts Code Adversary dispatches, `fixPasses` counts fix passes spent before their first edit and `fullQualityGateRuns` counts complete local quality-gate runs inside the validation loop. `reviewedRevision` is the full SHA the last completed review cycle attested, or null. `findings` holds that cycle's surviving findings as bounded entries with `id` (`F1`, `F2`, …), `label` (`blocking|issue|question`), `location` (`path:line`), `summary` (one sentence) and `disposition` (`open|fixed|follow-up|blocked`); a `follow-up` entry has its issue URL in `followUpIssues`. Exhaustive mode requires the user's exact current-request sentence in `authorizedBy`; no repository risk level, harness, coordinator, worker-rules file, spawn prompt or compaction summary may supply or infer it.

Validate these invariants in addition to field presence and types:

- `checkpointId` equals the filename and the digest of `task.canonicalSource`; `acceptanceCriteria` is non-empty.
- `status: blocked` has a non-empty `blocker` and actionable `nextAction`; other statuses have a null blocker.
- `phase: complete` and a non-null `outcome` occur together with `status: completed|cancelled|failed`; active and blocked states have a null outcome. Completed means delivered, cancelled means explicitly cancelled, and failed means a terminal failure ended the run.
- A merge commit requires a PR URL and PR head. A completed single-change outcome repeats the matching delivery values.
- Evidence is `disabled` when bookkeeping evidence is off. When enabled, it is `missing` before the first task commit; otherwise its revision and record path identify the current revision's valid evidence record, and `complete` requires the exact workflow revision.
- With claims enabled, an active GitHub implementation checkpoint has exactly one claim comment for its holder. Repository or GitHub writes require `status: active`, an unexpired `expiresAt`, and values reconciled with the authoritative issue comment. A completed checkpoint with a claim has released it with reason `merged`. With claims disabled, `claim` remains null and writes need no claim lease.
- Before validation, risk has a level, a diff class, a policy source and unique required gates. A lower level than an earlier revision, matching rule or resumed checkpoint requires non-null explicit override authorization; a null level recorded before the first commit is not a floor.
- Before validation, `releasePolicy` is non-null, normalized from repository instructions and live forge policy, and has a successful reconciliation timestamp. A material policy change invalidates hosted-review and CI evidence.
- Before validation, convergence mode and counters conform to `convergence-policy.json`. Review, test, CI and hosted feedback update the same counters; bounded mode never exceeds two review cycles, one fix pass, one full local quality gate inside the validation loop or 90 elapsed minutes. `reviewedRevision` is non-null only when `reviewCycles` is positive; a `blocked` finding occurs only with `status: blocked`; every `follow-up` finding has a URL in `followUpIssues`.
- Every CI triage failure has a unique identity derived from revision, workflow, job and attempt. A resolved failure has a resolution; an open failure does not. Rerun authorization never exceeds its recorded limit.
- An orchestration checkpoint has one child entry for every native subissue; each dependency names another recorded child. A completed child has `evidenceStatus: complete`, and its evidence revision equals its gated PR head.
- `createdAt` never changes and is not later than `updatedAt`.

## Safe writes

Validate the complete next document before replacing state. Write it to a same-directory temporary file with owner-only permissions, flush and sync it, preserve the current valid file as `<checkpoint-id>.json.bak`, then atomically rename the temporary file over the checkpoint. Never update state before its associated operation succeeds. A failed write leaves the previous checkpoint authoritative.

Use `python3 <skill-dir>/scripts/bookkeeping.py policy --repository <root>` once during resolve, adding `--enable claims,evidence,telemetry` only for features the current user explicitly enabled. Use `bookkeeping.py transition` for every checkpoint phase or status transition so each transition is one validated call; never write an ad-hoc state helper. Optional claim, evidence and telemetry operations run only when the returned policy enables them.

## Creation and resume

On a fresh task, create the checkpoint with `phase: resolve`, `status: active`, no revision, and task resolution as `nextAction`. Then advance to `explore` only after the source and acceptance criteria are complete.

When the file exists, migrate only the known legacy shapes before validating current required fields. A schema v1 checkpoint that has every previously required field may lack any subset of `risk`, `claim`, `ciTriage` and `convergence`, including only one of those fields, and may also lack `releasePolicy` because they were added in successive ship-it versions. This preserves the older migration case including only `ciTriage` among the newer optional fields. A previously valid terminal single-change outcome may lack `branchCleanup`; add `branchCleanup: not-applicable` so its recorded delivery remains reportable without inventing cleanup. Validate that legacy document, add a null claim or release policy when absent, add the risk object with `level`, `diffClass` and `policySource` null and empty `matchedRules` and `requiredGates` when absent, add `diffClass: null` to a risk object that lacks it, add `ciTriage: {"failures": []}` when absent, and add bounded convergence with null start and zero counters when absent. For a convergence object written before `reviewedRevision` and `findings` existed, add `reviewedRevision: null` and `findings: []` only when `reviewCycles` is zero. When `reviewCycles` is positive, reconstruct both fields only from unambiguous revision-bound review evidence; if that evidence lacks the attested revision or structured surviving findings, stop with the checkpoint path and the action to rerun review rather than inventing empty review state. Preserve every other field, then write atomically with `overrideAuthorization` null. This migration adds unknown state; it never selects or lowers risk, invents ownership, invents a CI observation, spends validation budget or invents release requirements. Missing any other required field remains invalid. Do not silently repair or replace invalid state.

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
- `status: cancelled|failed`: report the recorded reason and released claim, then stop. Resume only on an explicit restart instruction; atomically clear the terminal outcome, set status active, and follow audited claim takeover before any repository or GitHub write.

Never infer success from an advanced phase name. Revision, PR, issue and merge facts must agree before advancing or finalizing.
