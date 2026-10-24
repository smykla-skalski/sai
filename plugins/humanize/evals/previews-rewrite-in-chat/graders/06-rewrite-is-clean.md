---
type: llm
focus: last_message
weight: 1
---

The reply holds a rewritten changelog, usually in a fenced code block, and may also hold a pattern report that quotes the original. Judge only the rewritten changelog. Words that appear only in the report or in quotes of the original do not count.

PASS if the rewritten changelog meets all of these:
- It has no em dash (—).
- It does not use "robust", "cutting-edge", "seamlessly", "empowering" or "game-changer".
- It has no bold labels at the start of list items.
- It still says the cache cuts API calls by 40%, that logs include request IDs, and that a `sync --force` bug that could overwrite local changes is fixed.

FAIL if the reply has no rewritten changelog, or the rewritten changelog breaks any of these.
