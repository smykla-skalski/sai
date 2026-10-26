---
tags: [rightsize]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

/rightsize write a short message for the #eng Slack channel about the decision: help-center search will use Postgres full-text search instead of Elasticsearch. About 4,000 articles, English only, about 2,000 searches a day. We give up fuzzy matching and better ranking, and we avoid running a new cluster that none of us has run in production. Kasia decided. We look again if search-quality complaints keep coming after launch or we add a second language. Ask people to send search complaints to #help-center by Friday.
