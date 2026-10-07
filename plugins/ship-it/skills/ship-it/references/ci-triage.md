# CI failure triage

Triage every failed required CI job before changing source or requesting a rerun. The machine-readable record shape is [ci-triage.schema.json](ci-triage.schema.json). JSON Schema cannot compare sibling fields, records or recompute hashes, so export the complete checkpoint value as `{"failures": checkpoint.ciTriage.failures}` and run `python3 <skill-dir>/scripts/ci_triage.py validate <ci-triage.json>` before persisting, routing or rerunning. Both per-record schema validation and full-set semantic validation are mandatory. Keep valid records in the task checkpoint and bind them to the current revision's CI evidence result.

## Identity and deduplication

Use the full PR head SHA as `revision`, the provider's stable workflow identity as `workflow`, the stable job identity as `job`, and the provider's positive run attempt as `attempt`. Encode that object as compact JSON with keys in lexicographic order and hash its UTF-8 bytes with SHA-256. Prefix the lowercase digest with `cif_`; this is `failureId`.

Before retrieving logs, look for that exact `failureId` in `checkpoint.ciTriage.failures`. An existing observation is the same failure: do not retrieve or send its logs again. First reconcile it into the matching evidence result by failure ID, then emit the cumulative telemetry snapshot derived from checkpoint records, refresh `lastObservedAt`, and continue from its recorded `nextAction`. It does not count as a new failure. Never deduplicate across revisions, workflows, jobs or attempts.

For a new attempt, derive `recurrenceKey` from the revision, workflow, job and a normalized error signature that removes timestamps, runner paths, random IDs and attempt numbers. A prior matching recurrence key makes the observation a recurrence: set `recurrenceOf` to the most recent matching failure and set `recurrenceCount` to that record's count plus one. The target must have the same revision, workflow, job and recurrence key, and a lower attempt. Increment the telemetry recurrence counter. If a safe stable signature cannot be derived, use `null`; never merge uncertain failures.

Also derive `rerunGroupId` from compact lexicographically keyed JSON containing revision, workflow and job, without attempt. Every record in that group carries the group's cumulative `rerunsUsed`. Before a rerun, take the maximum value across the group and compare it with the authorization limit. After the provider accepts the rerun request, atomically set every group record to that maximum plus one; a newly observed attempt inherits it. This prevents each new attempt from resetting the limit.

## Bounded log collection

Fetch failed-job logs once into an owner-only temporary file, not into the model transcript. Extract only sections containing the failing command, first causal error and final failure summary. A record contains at most three sections, each at most 40 lines. To make the JSON Schema bound portable, each line is at most 125 Unicode code points; every code point encodes to at most four UTF-8 bytes, so a line is always at most 500 bytes. Remove secrets and credentials before any excerpt enters conversation, checkpoint or evidence. Delete the temporary file through the harness's approved cleanup flow after the record is durable.

Do not send an entire workflow or job log to an implementation role. If the bounded sections do not establish a cause, classify the failure as `unknown` and name the next diagnostic action.

## Classification

Choose exactly one classification and record at least one bounded supporting-evidence statement:

- `code`: a compiler, lint, test, build or acceptance failure attributable to the current revision. Include the failed acceptance evidence and route it to the checkpoint's owning implementation role.
- `flaky`: the same revision and materially identical job or signature has both failed and passed, or the repository documents that exact nondeterministic failure. A guess based on one failure is `unknown`.
- `infrastructure`: runner, image, network, quota, provider or external-service evidence shows the job failed independently of task code.
- `unknown`: evidence is insufficient, mixed or safely bounded extraction cannot identify the cause.

Classification never converts failed required CI evidence into a pass. A code failure sets the CI result and evidence record to `failed`, sets the checkpoint to `phase: implement`, and makes `nextAction` identify the owner, failure ID and failed acceptance evidence. Infrastructure and unknown failures keep the merge gate blocked and name their recovery or diagnostic action. Flaky failures remain failed until an authorized rerun passes.

## Rerun authorization

Never rerun CI merely because the provider exposes a rerun command. Authorization must be one of:

1. A repository policy in `.sai/ship-it-risk.json` under `ci_reruns`, naming the allowed classifications and `max_reruns_per_job`. The limit is a positive integer and applies to the same revision, workflow and job.
2. An explicit user approval naming the failure or classification and a maximum rerun count.

Repository prose counts only when it explicitly states the same allowed classifications and limit. The bundled policy authorizes no reruns. Record the authorization source, bounded reference and limit in `rerunAuthorization` before invoking the provider. Enforce that limit against the group's durable `rerunsUsed`.

Before invoking the provider, atomically set the same `rerunRequest` on every group record with `requestedAttempt: rerunsUsed + 1` and persist the checkpoint. Do not send another request while it is non-null. After the provider accepts, atomically advance every group record's `rerunsUsed` to that attempt and clear `rerunRequest`; only then does telemetry `retries` advance. On resume with a pending request, query the provider for that exact workflow attempt. If it exists, count it and clear the intent. If the provider proves it was never accepted, clear the intent without consuming budget. An ambiguous provider response keeps the intent pending and blocks another request. Exhausted or absent authorization blocks the rerun and names the exact approval needed.

## Resolution and recurrence

Checkpoint, evidence and append-only telemetry cannot share one atomic write. Make convergence idempotent: the checkpoint's unique failure records are authoritative, evidence attaches failure IDs as a set, and telemetry counters are cumulative values recomputed from checkpoint records rather than increments applied to an event stream. After every CI state change, update the stores in this order:

1. Checkpoint: append a new triage record or update the exact record's status, recurrence fields, authorization, resolution and `nextAction`.
2. Evidence: keep the CI result failed until the exact current revision passes; attach its failure IDs and, when resolved, the bounded resolution. A source-changing fix creates a new revision record and leaves the old failure unresolved by CI; its resolution is `superseded-by-revision` with the new SHA.
3. Telemetry: report cumulative `ci_failures`, `ci_recurrences` and `ci_resolutions` derived from checkpoint records; derive `retries` from the maximum durable `rerunsUsed` per group. Do not put failure text, repository data, paths or URLs in telemetry.

If the process stops between stores, resume from the checkpoint, add any missing failure ID or resolution to evidence, and emit the same cumulative counters before taking `nextAction`. Repeating reconciliation is a no-op for checkpoint and evidence and another equivalent cumulative snapshot for telemetry; consumers take the latest value per run instead of summing snapshots.

A passing authorized rerun resolves the observed failures as `rerun-passed`. A provider recovery without a requested rerun resolves them as `provider-recovered`. A code fix resolves old-revision failures as `superseded-by-revision`; the new revision must collect fresh CI evidence. Never erase historical failures or rewrite them as passes.
