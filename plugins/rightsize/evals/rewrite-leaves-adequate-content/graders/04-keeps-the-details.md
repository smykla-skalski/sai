---
type: regex
pattern: '^(?=[\s\S]*idempotency key)(?=[\s\S]*24 hours)(?=[\s\S]*Reporting team)(?=[\s\S]*2026-10-20)(?=[\s\S]*hash)(?=[\s\S]*(one|first) week)(?=[\s\S]*Proposed)(?=[\s\S]*High)'
flags: i
target:
  source: file
  path: docs/decisions/0004-retry-safe-exports.md
---

docs/decisions/0004-retry-safe-exports.md keeps the idempotency key, 24 hours, the owner, date, status, confidence the hash alternative and the one-week phase
