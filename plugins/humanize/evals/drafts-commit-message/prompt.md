---
tags: [humanize]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
---

Write a commit message for this change. I moved the retry logic from client.go into a new retry.go, added up to 250ms of random jitter between retries, and fixed a bug where the client ignored Retry-After headers. It fixes #91.
