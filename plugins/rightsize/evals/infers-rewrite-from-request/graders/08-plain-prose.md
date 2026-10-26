---
type: regex
pattern: 'seamless|robust|effortless|crucial|Additionally|leverag|streamline|cutting-edge|world-class|comprehensive|future-proof|empower|unlock|in order to|important to note|going forward|—|journey'
flags: i
match: not_contains
target:
  source: file
  path: docs/onboarding.md
---

docs/onboarding.md has no AI vocabulary, hype or em dash
