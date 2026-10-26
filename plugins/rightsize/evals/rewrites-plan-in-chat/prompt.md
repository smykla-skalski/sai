---
tags: [rightsize]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

Reply in chat only and don't create or edit any files. We need CSV export for the orders table in our internal admin app: about 2,000 orders a month, exported once a month by the 3-person finance team. Propose an implementation plan. Make it future-proof: a pluggable exporter framework with a registry, async export jobs on a queue with a status API, S3 storage with signed download links, and room for XLSX, JSON and Parquet later. Finance must never see customers' card numbers in an export.

After you post the plan, I want it slimmed down to what we actually need. Run /rightsize with no arguments for that.
