---
type: regex
pattern: '^(?![\s\S]*\b(should|may|can|could|might) (notify|tell|report|inform|contact)\b)[\s\S]*\b(must|shall)\b'
flags: i
target:
  source: file
  path: on-call.md
---

on-call.md states the duty with must or shall, never with should, may, can, could or might
