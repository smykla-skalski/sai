---
type: regex
pattern: '^\W*(?:\S+\s+){100}\S'
match: not_contains
target:
  source: file
  path: release-notes.md
---

release-notes.md is at most 100 words, down from 190
