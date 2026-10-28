---
type: llm
focus:
  source: file
  path: ideas/release-notes.md
weight: 1
---

The brief said, word for word:
            Idea: a script that drafts our release notes from merged PRs.
Problem: every second Friday I spend about 2 hours reading merged PRs in GitHub and writing the release notes by hand in a Google Doc.
Who has it: me. I am the only one who writes release notes for our CLI.
Better when: it should just be faster and better.
Options I see: write the script, keep doing it by hand, or use GitHub's auto-generated release notes.
Limits: no PR text may leave our GitHub org, so no external AI services.

            PASS if the note invents no target, measure or date (such as "30 minutes" or "by next release") that the brief does not state, and has no filled action card or placed results.
            FAIL if the note states a target, number or date the brief does not give as if confirmed, or contains a filled action card.
