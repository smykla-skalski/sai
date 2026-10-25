---
type: regex
pattern: '^(?=[\s\S]*## Setup)(?=[\s\S]*Install Go 1\.23 and Docker, then run `make dev`\.)(?=[\s\S]*## Pull requests)(?=[\s\S]*Keep each PR to one change\. Add a test for every bug fix\.)'
target:
  source: file
  path: CONTRIBUTING.md
---

CONTRIBUTING.md keeps the Setup and Pull requests sections word for word
