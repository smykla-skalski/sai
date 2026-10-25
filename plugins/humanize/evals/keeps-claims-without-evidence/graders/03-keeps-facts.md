---
type: regex
pattern: '^(?=[\s\S]*/search)(?=[\s\S]*Redis)(?=[\s\S]*SEARCH_CACHE_TTL)(?=[\s\S]*\b300\b)(?=[\s\S]*\b500\b)(?=[\s\S]*empty quer)'
flags: i
target:
  source: file
  path: pr-body.md
---

pr-body.md keeps /search, Redis, SEARCH_CACHE_TTL, 300, 500 and empty queries
