---
tags: [humanize]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
---

humanize this commit message before I push it:

fix(pool): enhance connection handling — a pivotal improvement

This commit delves into the connection pool, addressing a crucial race condition in `pool.Acquire()` that could lead to deadlocks under high concurrency. Additionally, it adds a 30s timeout to `pool.Release()`, ensuring seamless and robust resource management. Fixes #482.

I hope this helps!
