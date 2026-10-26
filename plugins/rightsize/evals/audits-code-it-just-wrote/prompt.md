---
tags: [rightsize]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

In export.py, add a --format option so the export can write JSON as well as the CSV it writes now. Make it future-proof so we can add XML and YAML later: a Formatter base class, a registry with a @register_format decorator, and loading of extra formatter modules from a plugins/ directory. When you're done, run /rightsize.

Input files: export.py
