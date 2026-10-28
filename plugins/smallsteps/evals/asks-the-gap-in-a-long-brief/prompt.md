---
tags: [smallsteps]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent, Edit, Write, ToolSearch]
disallowed_tools: [Bash, AskUserQuestion]
---

/smallsteps Save the note as ideas/release-notes.md. I wrote my idea down already:

Idea: a script that drafts our release notes from merged PRs.
Problem: every second Friday I spend about 2 hours reading merged PRs in GitHub and writing the release notes by hand in a Google Doc.
Who has it: me. I am the only one who writes release notes for our CLI.
Better when: it should just be faster and better.
Options I see: write the script, keep doing it by hand, or use GitHub's auto-generated release notes.
Limits: no PR text may leave our GitHub org, so no external AI services.
