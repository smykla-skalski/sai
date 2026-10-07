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
  "status": "complete",
  "invalidatedAt": null,
  "invalidatedByRevision": null,
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
      "outputReference": {"kind": "url", "value": "CI job URL", "sha256": null}
    }
  ],
  "createdAt": "RFC 3339 UTC timestamp",
  "updatedAt": "RFC 3339 UTC timestamp"
}
```

`status` is `collecting`, `complete`, `failed`, `blocked` or `stale`. A result status is `pending`, `passed`, `failed`, `blocked` or `stale`. Each required result has `requiredBy: pr` or `requiredBy: merge`; a merge result is not due at the PR gate. `provider`, `model`, `timestamp` and `outputReference` are always present; `model` is null when no model produced the result. Provider values identify the actual producer, such as `local-process`, `github-actions`, `claude-code`, `codex`, `opencode` or `sail`.

An output reference has kind `inline`, `command`, `path` or `url`; a non-empty UTF-8 `value` of at most 2048 bytes; and `sha256`, which is null or the lowercase digest of a referenced immutable artifact. Store only a concise verdict or summary inline. Keep secrets and unbounded logs out of the record.

## Required result set

Create one stable result ID for each resolved acceptance criterion and each gate required by the revision's selected risk policy. Expand `local-checks` into the checks discovered during exploration. Review and manual-test gates are due by PR creation; CI and hosted-review gates are due by merge. A policy-declared fallback keeps the required gate ID in `name`, keeps `provider` as the actual harness or service, and records both gate IDs in its bounded output reference. Optional diagnostics use `required: false`, omit `requiredBy`, and never compensate for missing required results.

A gate passes only when every required result due at that gate has `status: passed` for the exact record revision. Missing, pending, failed, blocked or stale due evidence blocks that gate. CI results that are not available before PR creation remain pending with `requiredBy: merge`.

A record becomes complete at the merge gate only when all of these are true:

- It contains every required result and no duplicate result ID.
- Every required result has `status: passed` and the exact record revision.
- Every selected review reference records its required passing verdict.
- Every selected manual-test reference records its required passing verdict.
- Every required CI result names the final successful job URL.
- The record revision equals committed `HEAD` and, after PR creation, the current PR head.

Missing, pending, failed, blocked or stale required evidence makes the record non-complete and blocks the gate where it is due. Never infer a pass from a workflow phase, old verdict, successful sibling check or checkpoint status.

## Revision changes and safe writes

After each successful commit, history rewrite, merge from the default branch or code-changing review/CI fix:

1. Atomically mark the previous current record `stale`, set `invalidatedAt`, and set `invalidatedByRevision` to the new full SHA.
2. Create the new revision's record with `status: collecting`; copy the required result identities, but set their statuses to `pending` and replace their source revisions, timestamps and output references.
3. Point the task checkpoint's evidence fields at the new record only after that record is valid and durable.
4. Rerun every required result against the new revision. Do not copy a pass from the stale record.

Validate a complete next document before replacing a record. Write to a same-directory owner-only temporary file, flush and sync it, preserve the current valid record as `<revision>.json.bak`, then atomically rename the temporary file. A failed write leaves the previous record authoritative.

## Resume and recovery

On resume, validate the current record and compare it with the checkpoint, Git and GitHub before any mutation. Preserve historical revision files.

Stop and report one recovery action when JSON is invalid; required fields, results or enums are missing; identities or revisions disagree; an output reference is unbounded; or a supposedly complete record contains non-passing evidence. Restore its `.bak` after inspection, or rerun the missing evidence for the current revision. Never rewrite an old record to claim it proves a newer revision.
