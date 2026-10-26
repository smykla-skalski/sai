---
type: regex
pattern: 'seamless|robust|effortless|crucial|Additionally|leverag|streamline|cutting-edge|world-class|comprehensive|future-proof|empower|unlock|in order to|important to note|going forward|—'
flags: i
match: not_contains
target:
  source: file
  path: docs/design/appointment-reminders.md
---

The design doc has no AI vocabulary, filler or em dash
