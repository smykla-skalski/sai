# Revision-bound completion evidence

Keep one portable evidence record per committed task revision. Claude Code, Codex, OpenCode, Copilot CLI and Sail read and write this contract directly; do not translate it into conversation state or a harness-specific format.

## Location and identity

Store records under `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/evidence/<checkpoint-id>/`. Create directories and files with owner-only permissions. A record is named `<revision>.json`, where `revision` is the full hexadecimal commit SHA it proves. Never put evidence in the repository, plugin cache or system temporary directory.

Every record's `checkpointId` must match its directory and the task checkpoint. Its `revision` must match its filename and every result's `sourceRevision`. The checkpoint-selected, non-stale current record must also match the checkpoint's `workflow.revision`, the current committed `HEAD`, and, after a PR exists, its `headRefOid`. Retained stale records describe only their historical revision and must not match live Git or checkpoint state.

## Format

Write UTF-8 JSON and preserve unknown fields. Every result includes its producer and bounded proof, including deterministic commands that used no model.

```json
{
  "schemaVersion": 1,
  "checkpointId": "64 lowercase hexadecimal characters",
  "repository": "normalized repository identity",
  "revision": "full hexadecimal commit SHA",
  "claim": null,
  "status": "complete",
  "invalidatedAt": null,
  "invalidatedByRevision": null,
  "roleRoutes": [
    {
      "role": "implementation",
      "requested": {"provider": "default", "model": "default", "variant": "default"},
      "actual": {"provider": "codex", "model": "resolved-model", "variant": "resolved-variant"},
      "sourceRevision": "full hexadecimal commit SHA",
      "mechanism": "inline",
      "executionId": "opaque execution identifier",
      "modelResolution": "resolved",
      "independence": "not-applicable",
      "degradationReasons": [],
      "timestamp": "RFC 3339 UTC timestamp"
    }
  ],
  "routeDiagnostics": [],
  "results": [
    {
      "id": "ac-1",
      "category": "acceptance-criterion",
      "name": "first resolved acceptance criterion",
      "required": true,
      "requiredBy": "pr",
      "status": "passed",
      "sourceRevision": "full hexadecimal commit SHA",
      "provider": "codex",
      "model": "model identifier or null",
      "timestamp": "RFC 3339 UTC timestamp",
      "outputReference": {
        "kind": "inline",
        "value": "bounded result, command, path, or URL",
        "sha256": "64 lowercase hexadecimal characters or null"
      }
    },
    {
      "id": "local-tests",
      "category": "local-check",
      "name": "repository test command",
      "required": true,
      "requiredBy": "pr",
      "status": "passed",
      "sourceRevision": "full hexadecimal commit SHA",
      "provider": "local-process",
      "model": null,
      "timestamp": "RFC 3339 UTC timestamp",
      "outputReference": {"kind": "command", "value": "test command", "sha256": null}
    },
    {
      "id": "adversarial-review",
      "category": "review",
      "name": "two-pass adversarial review",
      "required": true,
      "requiredBy": "pr",
      "status": "passed",
      "sourceRevision": "full hexadecimal commit SHA",
      "provider": "codex",
      "model": "model identifier or null",
      "timestamp": "RFC 3339 UTC timestamp",
      "outputReference": {"kind": "inline", "value": "Review Verdict: CLEAN", "sha256": null}
    },
    {
      "id": "adversarial-test",
      "category": "manual-test",
      "name": "adversarial manual test",
      "required": true,
      "requiredBy": "pr",
      "status": "passed",
      "sourceRevision": "full hexadecimal commit SHA",
      "provider": "codex",
      "model": "model identifier or null",
      "timestamp": "RFC 3339 UTC timestamp",
      "outputReference": {"kind": "inline", "value": "Test Verdict: PASS", "sha256": null}
    },
    {
      "id": "ci-test",
      "category": "ci",
      "name": "required CI check",
      "required": true,
      "requiredBy": "merge",
      "status": "passed",
      "sourceRevision": "full hexadecimal commit SHA",
      "provider": "github-actions",
      "model": null,
      "timestamp": "RFC 3339 UTC timestamp",
      "outputReference": {"kind": "url", "value": "CI job URL", "sha256": null},
      "ciTriage": {"failureIds": [], "resolution": null}
    }
  ],
  "createdAt": "RFC 3339 UTC timestamp",
  "updatedAt": "RFC 3339 UTC timestamp"
}
```

`status` is `collecting`, `complete`, `failed`, `blocked` or `stale`. A result status is `pending`, `passed`, `untested`, `failed`, `blocked` or `stale`. Each required result has `requiredBy: pr` or `requiredBy: merge`; a merge result is not due at the PR gate. `provider`, `model`, `timestamp` and `outputReference` are always present; `model` is null when no model produced the result. Provider values identify the actual producer, such as `local-process`, `github-actions`, `claude-code`, `codex`, `opencode` or `sail`.

A CI result also has `ciTriage` with unique `failureIds` from the checkpoint and a bounded `resolution` or null. On failure, keep the result failed and attach every observation for that job and revision. On a passing authorized rerun or provider recovery, set the result passed and record the matching resolution. After a source-changing fix, mark each old observation `superseded-by-revision`; the replacement revision starts with pending CI and no copied pass. This preserves failure, recurrence and resolution history without embedding logs in evidence.

`roleRoutes` follows the portable role contract. It records requested and actual provider, model and variant, source revision, mechanism, execution identity, resolution and independence for every role invocation. Every route in a record has `sourceRevision` equal to the record revision. A result produced by a routed role references its route's `executionId` in `outputReference`. Preserve repeated role records for retries. Strict review evidence is invalid when the review route violates any independent-review rule. Policy-permitted degraded execution requires `independence: degraded`, non-empty `degradationReasons` and the authorization in the result output reference.

`routeDiagnostics` records rejected route candidates and does not satisfy or block a gate. Pre-dispatch diagnostics have no execution metadata; post-dispatch diagnostics preserve returned route metadata for outputs rejected by independence checks. Only accepted dispatched executions belong in `roleRoutes`; therefore a later valid fallback can complete strict review while preserving all rejection history.

`claim` is null for Jira and description tasks. For a GitHub implementation issue it contains the current claim's `issueUrl`, `commentUrl`, `holderId`, `acquiredAt` and latest verified `renewedAt`. Create or update evidence only while that claim is active, unexpired and matches the checkpoint. Claim renewal changes `renewedAt` in the current record without invalidating revision-bound results. Another holder, comment or acquisition time blocks ordinary evidence writes; an audited takeover follows the claim contract's rebind procedure and reruns every required result. Releasing the same claim after verified merge preserves the completed delivery evidence.

An output reference has kind `inline`, `command`, `path` or `url`; a non-empty UTF-8 `value` of at most 2048 bytes; and `sha256`, which is null or the lowercase digest of a referenced immutable artifact. Store only a concise verdict or summary inline. Keep secrets and unbounded logs out of the record.

## Required result set

Create one stable result ID for each resolved acceptance criterion and each gate required by the revision's selected risk policy. Use `gate-<gate-id>` for a one-result gate. Expand `local-checks` into one result per discovered command and expand `ci` into one result per required check, each with the final job URL. Review and manual-test gates are due by PR creation; CI and hosted-review gates are due by merge. A policy-declared fallback retains the original required gate result ID, keeps `provider` as the actual harness or service, and records the gate and fallback mechanism IDs in its bounded output reference. Optional diagnostics use `required: false`, omit `requiredBy`, and never compensate for missing required results.

A gate passes only when every required result due at that gate has `status: passed`, or `status: untested` under the partial-pass rule below, for the exact record revision. Missing, pending, failed, blocked or stale due evidence blocks that gate. CI results that are not available before PR creation remain pending with `requiredBy: merge`.

An acceptance-criterion result is `untested` only under a `PASS (partial)` manual-test verdict whose `Untested` line names an environmental blocker for that criterion: the result carries that blocker in its output reference and still satisfies the PR and merge gates for that revision. No other result category, and no criterion the verdict leaves unnamed, may be `untested`. PR creation copies every such criterion into `## Untested criteria`, then verifies the live body separately; PR-body state is not a prerequisite for validating pre-PR evidence.

A record becomes complete at the merge gate only when all of these are true:

- It contains every required result and no duplicate result ID.
- It contains valid role routes for every invoked exploration, implementation, review, testing and CI-triage role.
- Every strict review route is resolved, fresh, non-inline and uses a different actual provider-and-model pair from implementation.
- Every required result has `status: passed`, or `status: untested` under the partial-pass rule, and the exact record revision.
- Every selected review reference records its required passing verdict.
- Every selected manual-test reference records its required passing verdict.
- Every required CI result names the final successful job URL.
- The record revision equals committed `HEAD` and, after PR creation, the current PR head.
- At a GitHub PR or merge gate, the record's claim matches the checkpoint and its authoritative issue comment is active and unexpired.

Missing, pending, failed, blocked or stale required evidence makes the record non-complete and blocks the gate where it is due. Never infer a pass from a workflow phase, old verdict, successful sibling check or checkpoint status.

## Revision changes and safe writes

After each successful commit, history rewrite, merge from the default branch or code-changing review/CI fix:

1. Atomically mark the previous current record `stale`, set `invalidatedAt`, and set `invalidatedByRevision` to the new full SHA.
2. Create the new revision's record with `status: collecting`; copy the required result identities, but set their statuses to `pending` and replace their source revisions, timestamps and output references. Carry still-active exploration and implementation routes with `sourceRevision` rebound to the new revision. Drop old review, testing and CI-triage routes; record fresh routes when those gates rerun.
3. Point the task checkpoint's evidence fields at the new record only after that record is valid and durable.
4. Validate every required result against the new revision under the convergence contract. Do not copy a pass from the stale record.

After the bounded mode's single routine fix pass, do not dispatch another broad adversarial review or manual-test run. Re-attest their pending results against the new revision only after the diff since the checkpoint's `reviewedRevision` matches the recorded findings, focused reproductions pass and the final full quality gate passes, or after every remaining finding has become a follow-up issue under the limit rule. Use provider `ship-it-convergence`, model null, and a bounded output reference that names the prior evidence revision, the finding dispositions and the focused commands. This is fresh evidence for the fixed revision, not a copied verdict. A default-branch merge that leaves the branch files unchanged is re-attested the same way, naming the first-parent comparison. Security, data-loss or destructive-concurrency triggers instead require the second and final review cycle, which a spent fix pass does not prevent; an unresolved acceptance criterion blocks delivery. Required CI and hosted-review results always come from their actual current-head providers.

Validate a complete next document before replacing a record. Write to a same-directory owner-only temporary file, flush and sync it, preserve the current valid record as `<revision>.json.bak`, then atomically rename the temporary file. A failed write leaves the previous record authoritative.

## Resume and recovery

On resume, validate the current record and compare it with the checkpoint, Git and GitHub before any mutation. Preserve historical revision files.

A schema-v1 legacy record whose CI results have every previously required field but no `ciTriage` may be migrated for the same revision. Add `ciTriage: {"failureIds": [], "resolution": null}` to each such result and write the record atomically. A passed or pending result keeps its status. A failed or blocked result remains non-complete and returns to CI triage; never invent historical failure IDs or a resolution. Missing any other required field remains invalid.

Stop and report one recovery action when JSON is invalid; required fields, results or enums are missing; identities or revisions disagree; an output reference is unbounded; or a supposedly complete record contains required evidence other than `passed` or `untested` evidence valid under the partial-pass rule. Restore its `.bak` after inspection, or rerun the missing evidence for the current revision. Never rewrite an old record to claim it proves a newer revision.
