---
tags: [rightsize]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

Create docs/parking.md with the architecture for our parking booking tool. 20 people share the office's 3 parking spots and book one a day ahead. I want it future-proof: four microservices (booking, spots, users, notifications), Kafka between them, a Redis cache and Kubernetes. Keep the doc under 40 lines. When you're done, run /rightsize.
