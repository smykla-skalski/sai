---
type: regex
pattern: '^(?=[\s\S]*\b48 hours\b)(?=[\s\S]*actual or suspected)(?=[\s\S]*reasonably likely)(?=[\s\S]*in writing)(?=[\s\S]*without undue delay)(?=[\s\S]*staging)(?=[\s\S]*customer data)(?=[\s\S]*security team)(?=[\s\S]*on[- ]call)'
flags: i
target:
  source: file
  path: on-call.md
---

on-call.md keeps 48 hours, actual or suspected, reasonably likely, in writing, without undue delay, staging, customer data, the security team and the on-call actor
