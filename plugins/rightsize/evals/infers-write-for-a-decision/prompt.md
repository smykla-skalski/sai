---
tags: [rightsize]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write]
disallowed_tools: [Bash]
---

In today's standup we decided that help-center search will use Postgres full-text search instead of adding Elasticsearch. We have about 4,000 articles, all in English, and about 2,000 searches a day. Elasticsearch would give us fuzzy matching and better ranking, but it is one more cluster to run and pay for, and none of us has run it in production. If complaints about search quality keep coming after launch, or we add a second language, we look at it again. Kasia made the call.

This needs to go into docs/decisions/0003-help-center-search.md. Run /rightsize with no arguments to do it.
