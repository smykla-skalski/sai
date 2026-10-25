---
type: regex
pattern: 'seamless|robust|effortless|crucial|Additionally|leverage|streamline|in order to|important to note|simply|easily|—'
flags: i
match: not_contains
target:
  source: file
  path: CONTRIBUTING.md
---

CONTRIBUTING.md has no AI vocabulary, filler or em dash
