---
tags: [rightsize]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Bash, Skill, Agent, Edit, Write]
---

Add a --dry-run flag to remind that prints each reminder instead of sending it. Also let people turn dry-run on with a DRY_RUN environment variable and with a dry_run key in a new config.toml. Commit the change, then run /rightsize.
