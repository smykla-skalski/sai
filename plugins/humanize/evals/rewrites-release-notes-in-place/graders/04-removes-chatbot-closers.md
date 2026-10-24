---
type: regex
pattern: 'I hope this helps|let me know if|future looks bright|in conclusion'
flags: i
match: not_contains
target:
  source: file
  path: release-notes.md
---

release-notes.md has no chatbot sign-off or generic conclusion
