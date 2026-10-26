---
type: regex
pattern: 'at this point in time|it is the case that|have a tendency to|in the event that|it should be noted|in order to|facilitate|for a period of|is not something that'
flags: i
match: not_contains
target:
  source: file
  path: docs/decisions/0004-retry-safe-exports.md
---

docs/decisions/0004-retry-safe-exports.md has none of the wordy phrases
