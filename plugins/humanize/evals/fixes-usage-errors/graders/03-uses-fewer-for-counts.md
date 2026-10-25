---
type: regex
pattern: '^(?![\s\S]*\bless tables\b)[\s\S]*\bfewer tables\b'
flags: i
target:
  source: file
  path: migrations.md
---

migrations.md says fewer tables, not less tables
