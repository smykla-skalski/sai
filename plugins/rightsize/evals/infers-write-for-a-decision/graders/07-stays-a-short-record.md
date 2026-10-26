---
type: regex
pattern: '^\W*(?:\S+\s+){400}\S'
match: not_contains
target:
  source: file
  path: docs/decisions/0003-help-center-search.md
---

The record is at most 400 words
