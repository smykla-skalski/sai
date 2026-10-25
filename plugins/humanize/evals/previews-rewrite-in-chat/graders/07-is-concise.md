---
type: llm
focus: last_message
weight: 1
---

Find the rewritten changelog in the reply, usually in a fenced code block. Ignore any pattern report and any quotes of the original.

PASS if the rewritten changelog has at most 50 words, heading included, and still says that v1.7.0 adds a cache that cuts API calls by 40%, that logs include request IDs, and that a bug is fixed where `sync --force` could, in certain edge cases, overwrite local changes (the edge-case condition and the "could" stay).
FAIL if there is no rewritten changelog, it runs longer than 50 words, or a fact or condition is missing.
