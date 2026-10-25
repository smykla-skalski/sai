---
type: regex
pattern: '^\W*(?:\S+\s+){75}\S'
match: not_contains
target:
  source: file
  path: deploy.md
---

deploy.md is at most 75 words, down from 127
