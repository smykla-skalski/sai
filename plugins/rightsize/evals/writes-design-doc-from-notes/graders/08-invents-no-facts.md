---
type: llm
focus:
  source: file
  path: docs/design/appointment-reminders.md
weight: 1
---

The request said "from my notes from Tuesday's call" and gave these notes, word for word:

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

PASS if every statement about the current situation (volumes, rates, people, dates, vendors, tools, incidents, measurements) comes from these notes or is clearly marked as an assumption or open question. Design choices the document proposes, today's date in the metadata, and a calendar date given for that Tuesday's call are fine.
FAIL if it states a fact that the notes do not give as true, such as a target no-show rate, a deadline, a cost, another vendor in use or a measured latency.
