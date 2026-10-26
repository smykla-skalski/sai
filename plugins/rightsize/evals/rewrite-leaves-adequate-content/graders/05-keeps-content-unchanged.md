---
type: llm
focus:
  source: file
  path: docs/decisions/0004-retry-safe-exports.md
weight: 1
---

PASS if the record still has every part with the same meaning: the summary; the context with the problem, the unchanged file format, the success signal and the non-goal; the chosen idempotency key (24-hour mapping, scoped to the client, a request without a key unchanged, a unique constraint for concurrent retries, a changed body rejected); both rejected options with their reasons; the consequences with the storage cost, the one-week record-only phase with its rule for enabling deduplication and for a shared key, and the rollback that keeps the mappings until they expire; and the revisit trigger. It adds no new mechanism, requirement or open question.
FAIL if any part is missing, changed in meaning or weakened, or a new mechanism, requirement or open question is added.
