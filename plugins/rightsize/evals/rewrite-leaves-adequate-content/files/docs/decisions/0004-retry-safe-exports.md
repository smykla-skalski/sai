# 4. Retry-safe report exports

Status: Proposed · Owner: Reporting team · Date: 2026-10-20 · Confidence: High

We will accept an idempotency key with each export request, so that a retried request returns the original export job instead of creating a second one.

## Context

At this point in time, it is the case that clients have a tendency to retry export requests in the event that a network failure occurs. It should be noted that a retry of this kind can result in the creation of two identical export jobs, which in turn causes duplicate work to be performed and confuses users. In order to facilitate a fix, the exported file format should not be changed in any way. Success means that no retried request that carries a key creates a second export job. Detecting two independently submitted but identical reports is not something that this decision attempts to address.

## Options

- Idempotency key, chosen: the mapping from key to job is stored for a period of 24 hours, and each key is scoped to the client that sent it. A request without a key behaves as it does today. A unique constraint on the client and key makes a concurrent retry return the same job, and a repeated key that arrives with a different request body is rejected.
- Deduplicate by a hash of the request body: rejected, because two people who ask for the same report on purpose would get one job.
- Do nothing: rejected, because users keep seeing duplicate jobs after network failures.

## Consequences

We add a small amount of temporary metadata storage. First, keys will be recorded without being enforced for one week; if no two different requests share a key in that week, deduplication will be enabled, and otherwise we change the key format and record for another week. Rollback means ignoring the key; the stored mappings are kept until they expire.

## Revisit if

Clients start to retry requests more than 24 hours after the first one.
