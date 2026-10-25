---
type: regex
pattern: 'different than|as to whether|kind of|(^|[.!?]\s+)Due to'
match: not_contains
target:
  source: file
  path: migrations.md
---

migrations.md no longer uses different than, as to whether, kind of or a sentence-opening Due to
