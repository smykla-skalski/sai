---
type: regex
pattern: 'Next action:(\*\*)?[ \t]*When\b[^\n]*20:00'
flags: i
target:
  source: file
  path: ideas/spending-tracker.md
---

The next action is in the form "When ..., I will ..." with the time the user gave
