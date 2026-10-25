---
type: llm
focus:
  source: file
  path: migrations.md
weight: 1
---

These are the only facts in the original migrations.md:

- The platform team finished the schema review and approved the migration.
- Each engineer must run `make migrate` before Friday and should not skip it.
- The new schema has fewer tables than the old one.
- The query planner behaves differently than before.
- Because of the index changes, some reports are somewhat slow.
- The team is not sure whether the slowdown is permanent.
- Anybody unsure of their role should ask Priya.

PASS if the file states each of these with the same strength (running `make migrate` stays required, only some reports are slow, and the permanence of the slowdown stays uncertain), and adds no fact, cause, number or instruction they do not support.
FAIL if a fact is missing, weakened, strengthened or changed, or anything new is added.
