---
type: regex
pattern: '^(?=[\s\S]*\b120\b)(?=[\s\S]*\b(19|nineteen) days)(?=[\s\S]*(5,000 EUR|EUR 5,000|€ ?5,000))(?=[\s\S]*\b(7|seven) years)(?=[\s\S]*Dana Kowalski)(?=[\s\S]*2026-12-01)(?=[\s\S]*\b(two|2) developers)'
flags: i
target:
  source: file
  path: docs/plan.md
---

docs/plan.md keeps 120 employees, 19 days, 5,000 EUR, 7 years, Dana Kowalski, 2026-12-01 and two developers
