---
type: llm
focus:
  source: file
  path: CONTRIBUTING.md
weight: 1
---

Judge only the new "Running tests" section of CONTRIBUTING.md.

PASS if it states the four facts from the request (Docker must be running, `make test` starts the tests, a full run takes about 3 minutes, and `TEST_DB_PORT` sets another port when port 5432 is taken), adds no fact the request does not give (no other command, flag, time, CI detail or troubleshooting step), and is concise: no preamble, no filler, no closing line, and at most 50 words.
FAIL if a fact is missing or changed (for example "3 minutes" without "about"), anything is added, or the section is padded or longer than 50 words.
