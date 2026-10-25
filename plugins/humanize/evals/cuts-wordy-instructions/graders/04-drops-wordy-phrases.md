---
type: regex
pattern: 'prior to|it is necessary to|in order to|at this point in time|has the ability to|important to note|in the event that|make a decision|period of time|in a position to|once this has been done'
flags: i
match: not_contains
target:
  source: file
  path: deploy.md
---

deploy.md has none of the wordy phrases
