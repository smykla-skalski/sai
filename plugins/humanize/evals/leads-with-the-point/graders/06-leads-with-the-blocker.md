---
type: llm
focus: last_message
weight: 1
---

Find the rewritten status update in the reply. Ignore any pattern report and any quotes of the original.

PASS if the first sentence of the rewritten update says that the v3.2 rollout is blocked (by DB-142 or by the missing index).
FAIL if there is no rewritten update, or its first sentence is preamble, background or anything other than the blocker.
