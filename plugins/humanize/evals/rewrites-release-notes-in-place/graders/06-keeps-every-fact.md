---
type: regex
pattern: '^(?=[\s\S]*2\.4\.0)(?=[\s\S]*--retry-limit)(?=[\s\S]*\b5\b)(?=[\s\S]*1\.8\s?s)(?=[\s\S]*0\.9\s?s)(?=[\s\S]*Postgres 16)(?=[\s\S]*connect_legacy\(\))(?=[\s\S]*\bconnect\(\))'
target:
  source: file
  path: release-notes.md
---

release-notes.md still states 2.4.0, --retry-limit with default 5, 1.8s to 0.9s, Postgres 16, connect_legacy() and connect()
