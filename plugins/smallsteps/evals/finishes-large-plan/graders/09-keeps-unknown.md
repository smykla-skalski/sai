---
type: regex
pattern: 'How much I overspend each month[^\n]*unknown|unknown[^\n]*How much I overspend each month'
flags: i
target:
  source: file
  path: ideas/spending-tracker.md
---

The unknown about overspending stays unknown
