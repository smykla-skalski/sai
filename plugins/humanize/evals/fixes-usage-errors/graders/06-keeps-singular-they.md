---
type: regex
pattern: '\b(his|her|he|she|him)\b'
flags: i
match: not_contains
target:
  source: file
  path: migrations.md
---

migrations.md keeps the singular their and adds no gendered pronoun
