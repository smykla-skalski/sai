---
type: llm
focus:
  source: file
  path: release-notes.md
weight: 1
---

These are the only facts in the original release notes:

- Version 2.4.0, a release about reliability
- A new `--retry-limit` flag caps retries per request, default 5, for more predictable behavior across distributed systems
- Cold start time drops from 1.8s to 0.9s
- The driver supports Postgres 16
- The deprecated `connect_legacy()` function is removed; projects that still call it fail at build time; migrate to `connect()` before upgrading

PASS if every statement in the file is one of these facts, a restatement of one, or follows from them directly (1.8s to 0.9s is "twice as fast"; a removed function is a breaking change to check before upgrading). Dropping marketing claims is fine.
FAIL if the file adds a fact that none of these supports, such as a new number, percentage, benchmark, feature, customer, date or cause.
