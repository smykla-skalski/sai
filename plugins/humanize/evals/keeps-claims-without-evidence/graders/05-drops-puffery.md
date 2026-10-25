---
type: regex
pattern: 'groundbreaking|seamless|Additionally|I hope this helps'
flags: i
match: not_contains
target:
  source: file
  path: pr-body.md
---

pr-body.md drops the puffery and the chatbot closer
