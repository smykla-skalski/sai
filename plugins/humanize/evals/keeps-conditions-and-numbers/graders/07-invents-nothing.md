---
type: llm
focus:
  source: file
  path: on-call.md
weight: 1
---

The original on-call.md says only this: despite any other part of the runbook, the on-call engineer must notify the security team in writing, without undue delay and no later than 48 hours after becoming aware of any actual or suspected incident that affects, or is reasonably likely to affect, customer data, unless the incident is limited to staging environments. It also claims this makes the response process robust and seamless.

PASS if the file keeps that duty with the same scope (incidents limited to staging stay the only exception) and adds nothing the original lacks, such as a channel (Slack, PagerDuty, email), a shorter or longer deadline, a new step, a new exception or a reason.
FAIL if the scope, the deadline or the exception changed, or anything new was added.
