---
type: llm
focus: last_message
weight: 1
---

Judge only what the assistant says in its own voice. Quotes of the original inside a pattern report do not count.

These are allowed and never count against the reply: the result, a pattern report table, a one-line summary, a list of claims without evidence, a list of changed details, a one-line note that a qualified reviewer must check the text, and plain explanations of what was or was not changed.

FAIL only if the assistant does one of these:
- offers to do more, such as "Want me to...", "Tell me if you want...", "I can also...", "Let me know if..."
- suggests optional alternatives or extra changes the user did not ask for, such as "You could also..." or "If you prefer, ..."

PASS otherwise.
