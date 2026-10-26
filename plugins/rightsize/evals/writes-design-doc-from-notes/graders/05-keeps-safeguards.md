---
type: llm
focus:
  source: file
  path: docs/design/appointment-reminders.md
weight: 1
---

PASS if the design explicitly ensures that a cancelled appointment gets no reminder and that the same appointment never gets two reminders, for example with a sent mark, a unique record or an idempotency key checked before sending.
FAIL if either safeguard is missing or left vague.
