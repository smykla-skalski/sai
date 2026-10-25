---
type: regex
pattern: '^(?=[\s\S]*\n## Running tests)(?=[\s\S]*make test)(?=[\s\S]*Docker[\s\S]*Docker)(?=[\s\S]*about (3|three) minutes)(?=[\s\S]*5432)(?=[\s\S]*TEST_DB_PORT)'
flags: i
target:
  source: file
  path: CONTRIBUTING.md
---

CONTRIBUTING.md has a Running tests section with make test, Docker, about 3 minutes, 5432 and TEST_DB_PORT
