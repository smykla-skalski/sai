---
type: llm
focus:
  source: file
  path: docs/design/appointment-reminders.md
weight: 1
---

PASS if the proposed design sends the reminders from the existing system, such as a scheduled task in the Django app or the existing Celery worker that queries Postgres and sends through SendGrid, and its proposed design contains no Kafka, no separate notification service, no Redis cache and no plugin system.
FAIL if any of Kafka, a separate notification service, Redis or a plugin system is part of the proposed design.
