---
type: regex
pattern: 'seamless|robust|effortless|crucial|Additionally|leverag|streamline|cutting-edge|world-class|comprehensive|future-proof|empower|unlock|in order to|important to note|going forward|—|landscape|embrac|innovative'
flags: i
match: not_contains
target:
  source: file
  path: docs/plan.md
---

docs/plan.md has no AI vocabulary, hype or em dash
