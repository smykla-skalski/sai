---
type: llm
focus: last_message
weight: 1
---

Find the rewritten status update in the reply. Ignore any pattern report and any quotes of the original.

PASS if the rewritten update ends on a line that carries information, and does not end with a generic closer such as "We'll keep everyone updated", "We'll post updates here", "Stay tuned" or "Let me know if you have any questions". A closer that names a time or place for the next update would be fine, but the original names none, so the rewrite should not invent one either.
FAIL if there is no rewritten update, or it ends with such a generic closer or with an invented time or place.
