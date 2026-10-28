---
tags: [smallsteps]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write, ToolSearch]
disallowed_tools: [Bash, AskUserQuestion]
---

/smallsteps resume ideas/contract-format.md

Done. I wrote the example for "Authorize a payment": two inputs, amount as an integer in minor units and currency as a three-letter code, and three results, approved, declined and unknown. I listed two gaps: the error result, and how a contract refers to it.
