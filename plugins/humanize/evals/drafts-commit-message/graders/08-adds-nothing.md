---
type: llm
focus: last_message
weight: 1
---

The request gives only these facts: the retry logic moved from client.go into a new retry.go; up to 250ms of random jitter is now added between retries; a bug where the client ignored Retry-After headers is fixed; the change fixes #91.

Find the commit message in the reply. PASS if it states nothing beyond these facts. Restating them in other words is fine.
FAIL if it adds a reason or benefit (such as avoiding a thundering herd or retry storms), a number, a file, a test, a config option or a behavior that the request does not give, or turns "up to 250ms" into a fixed 250ms.
