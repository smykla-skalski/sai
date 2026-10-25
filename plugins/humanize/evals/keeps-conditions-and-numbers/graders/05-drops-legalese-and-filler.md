---
type: regex
pattern: 'notwithstanding|forty-eight|important to note|Additionally|robust|seamless|in any event'
flags: i
match: not_contains
target:
  source: file
  path: on-call.md
---

on-call.md drops the legalese, the filler and the puffery
