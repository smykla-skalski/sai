---
type: regex
pattern: 'fast-paced business landscape'
flags: i
match: not_contains
target:
  source: file
  path: docs/plan.md
---

docs/plan.md no longer has the original opening sentence
