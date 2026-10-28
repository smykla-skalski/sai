---
tags: [smallsteps]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write, ToolSearch]
disallowed_tools: [Bash, AskUserQuestion]
---

/smallsteps resume ideas/contract-format.md

Done when the example has one operation with its inputs and their types and its results. By the way, the checker should later run in CI on every PR, read the YAML with a JSON schema and post errors as PR comments.
