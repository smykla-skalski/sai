---
type: llm
focus:
  source: file
  path: migrations.md
weight: 1
---

PASS if migrations.md has no comma splice (two independent clauses joined only by a comma), no opening phrase that refers to the wrong subject, and no other grammar error. In the original, "Having finished the schema review, the migration was approved by the platform team" wrongly says the migration finished the review; the platform team did.
FAIL if any comma splice, dangling opening phrase or grammar error remains.
