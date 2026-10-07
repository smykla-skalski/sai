# Expiring GitHub work claims

Use one visible issue comment as a portable lease for GitHub-backed work. Claude Code, Codex, OpenCode, Copilot CLI and Sail use this contract directly. Jira tickets and plain task descriptions do not create claims.

## Comment format

The comment starts with `<!-- sai:ship-it-claim:v1 -->`, then a short human-readable ownership line, then one fenced `json` object. Preserve unknown fields when updating it.

```json
{
  "schemaVersion": 1,
  "task": "github:github.com/owner/repository#155",
  "checkpointId": "64 lowercase hexadecimal characters",
  "holder": {
    "id": "github-login/harness/session-or-worker-id",
    "githubLogin": "authenticated GitHub login",
    "harness": "claude-code|codex|opencode|copilot-cli|sail",
    "session": "stable session or worker id"
  },
  "status": "active|released",
  "acquiredAt": "RFC 3339 UTC timestamp",
  "renewedAt": "RFC 3339 UTC timestamp",
  "expiresAt": "RFC 3339 UTC timestamp",
  "releasedAt": null,
  "releaseReason": null,
  "takeover": null
}
```

Use the canonical GitHub task string from the checkpoint. Resolve `githubLogin` with the authenticated GitHub API. Use the harness's stable session or Sail worker identity. When none exists, generate one random identifier and atomically store a provisional checkpoint claim with that holder, `status: pending`, and null comment fields before the GitHub write. Set `holder.id` to `<githubLogin>/<harness>/<session>`. Never put a hostname, filesystem path, secret or conversation content in a claim.

An active claim uses a 30-minute lease. Set `acquiredAt` once, `renewedAt` to the successful comment create or update time, and `expiresAt` to 30 minutes later. Treat a claim as conflicting only when its marker and required fields validate, its task and checkpoint match this issue, its status is `active`, and `expiresAt` is later than the current UTC time. Report malformed matching comments as a hard stop rather than guessing their ownership.

## Acquire

Acquire after the task checkpoint is created or reconciled and before branch creation or source edits:

1. Read every issue comment with the marker and validate each matching claim. Ignore released claims and claims for another canonical task.
2. If another holder has an unexpired claim, stop and report its `holder.id`, `renewedAt`, `expiresAt` and comment URL. Do not create a competing claim. If this holder has one or more unexpired claims after a lost response or crash, keep the lowest numeric GitHub comment database ID, release its own duplicates with reason `lost acquisition race`, reconcile the winner into the checkpoint and continue.
3. If no active matching claim exists, create one active comment. If claims are released or expired, create a new comment instead of erasing their audit history.
4. Wait five seconds, reread all matching comments and resolve acquisition races. The winner among all valid active matching claims is the lowest numeric GitHub comment database ID. A losing holder immediately marks its own comment released with reason `lost acquisition race`, records the conflict in its checkpoint, and stops.
5. Store the winning comment ID, URL and full claim fields in the checkpoint only after the reread proves this holder won.

Creating the checkpoint does not establish ownership. Branch creation, source edits, commits and evidence writes require a verified unexpired claim owned by the current holder.

## Renew and reconcile

Renew the same comment at least every 10 minutes while work is active and before a repository or GitHub write when the last successful renewal is older than 10 minutes. Update only `renewedAt` and `expiresAt`, then reread the comment and persist the new values in the checkpoint. A failed or unverifiable renewal stops repository and remote writes until reconciliation succeeds.

On resume, reread the issue and the checkpoint's claim comment before changing repository or remote state. Continue only when the comment is active, unexpired and owned by the checkpoint holder. If another active holder exists, stop with its identity. If this holder's claim expired, use the takeover flow; never silently reactivate it.

## Audited takeover

Before replacing an expired claim, treat the matching expired comment with the greatest numeric GitHub comment database ID as the previous claim and retain every older comment as history:

1. Record the expired comment URL, previous holder, expiry and the UTC audit time.
2. Inspect the issue's linked pull requests and cross-references, then search the repository's open pull requests for the issue number, canonical task, matching title and recorded task branch.
3. Inspect pull requests merged in the previous 30 days with the same issue reference or equivalent title. If equivalent work is open, adopt and reconcile that PR instead of taking over implementation. If equivalent work merged, verify delivery and mark this as a terminal delivery takeover; finish steps 4-5, release the new claim with reason `merged`, then complete without implementation. Stop when equivalence is ambiguous.
4. Create a new claim comment whose `takeover` object records `previousCommentUrl`, `previousHolder`, `previousExpiry`, `auditedAt`, `openPullRequestsChecked` and `recentMergesChecked`. Each check is a bounded list of inspected URLs, or an empty list.
5. Run the normal five-second acquisition-race check. Store the new claim only after it wins.

Never edit the expired holder's comment. The old and new comments form the takeover audit trail.

When takeover adopts an existing committed revision, atomically rebind its evidence record to the new claim before advancing: preserve the result IDs and source revision, replace the claim binding, set record status to `collecting`, and reset every required result to `pending` with provider `claim-takeover`, null model, the takeover timestamp and a bounded `pending after claim takeover` output reference. Rerun every required result. The issue comments and new claim's `takeover` object preserve the prior ownership audit.

## Release

Release only the current holder's comment. Set `status` to `released`, set `releasedAt`, copy it to `renewedAt`, set `expiresAt` to the same time, and set `releaseReason` to `merged`, `cancelled`, `terminal failure` or `lost acquisition race`. Reread the comment before recording the release in the checkpoint.

Release after merge verification, explicit cancellation, or a failure that ends the run and cannot resume. A temporary wait or recoverable blocker keeps the claim only while the holder can renew it; otherwise let it expire. Failure to release after a verified merge does not undo delivery, but it must be reported with the comment URL and exact cleanup action.
