---
tags: [rightsize]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

/rightsize write docs/design/appointment-reminders.md from my notes from Tuesday's call:

- Clinic booking app: Django monolith, one Postgres database, a web dyno and a worker dyno on Heroku. The worker already runs Celery for receipt emails.
- About 12% of appointments are no-shows. The front desk calls every patient the day before, which takes Ola about an hour a day.
- Ask: email each patient a reminder 24 hours before the appointment.
- About 300 bookings a day across 4 clinics.
- Receipts already go out through SendGrid.
- Never remind a patient whose appointment was cancelled.
- Last year a retry bug sent receipts twice and patients complained, so no double reminders.
- Marek wants it scalable for the future: Kafka for events, a separate notification microservice, Redis to cache appointments, and a plugin system for SMS, WhatsApp and push later.
- SMS would be nice one day, but nobody has asked for it and we have no SMS provider.
- Ola owns the outcome, Marek writes the code.
