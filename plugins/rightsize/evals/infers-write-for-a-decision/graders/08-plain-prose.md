---
type: regex
pattern: 'seamless|robust|effortless|crucial|Additionally|leverag|streamline|cutting-edge|world-class|comprehensive|future-proof|empower|unlock|in order to|important to note|going forward|—'
flags: i
match: not_contains
target:
  source: file
  path: docs/decisions/0003-help-center-search.md
---

The record has no AI vocabulary, filler or em dash
