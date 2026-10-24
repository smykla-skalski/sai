---
type: regex
pattern: '\b(thrilled|groundbreaking|testament|unwavering|delves?|showcas\w*|enhance|landscape|fostering|pivotal|crucial|underscores?|additionally)\b'
flags: i
match: not_contains
target:
  source: file
  path: release-notes.md
---

release-notes.md no longer uses the AI vocabulary from the original
