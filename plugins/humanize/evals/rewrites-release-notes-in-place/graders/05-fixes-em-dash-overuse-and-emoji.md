---
type: regex
pattern: '—[\s\S]*—|🚀'
match: not_contains
target:
  source: file
  path: release-notes.md
---

release-notes.md has at most one em dash and no emoji
