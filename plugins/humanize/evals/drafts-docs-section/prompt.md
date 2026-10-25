---
tags: [humanize]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
---

Add a short "Running tests" section to CONTRIBUTING.md. The tests need Docker running, you start them with `make test`, a full run takes about 3 minutes, and if port 5432 is taken you can set `TEST_DB_PORT` to another port.
