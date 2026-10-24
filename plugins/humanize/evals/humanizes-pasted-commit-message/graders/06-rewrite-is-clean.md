---
type: llm
focus: last_message
weight: 1
---

Find the rewritten commit message in the reply, usually in a fenced code block. Judge only that message. Words that appear only in the pattern report or in quotes of the original do not count.

PASS if the rewritten message meets all of these:
- Its subject line follows conventional commits and has at most 72 characters.
- It has no em dash (—).
- It does not use "enhance", "pivotal", "delves", "crucial", "Additionally", "seamless" or "robust", and has no "I hope this helps".
- It still conveys, in any wording, that the race or deadlock in `pool.Acquire()` is fixed, that `pool.Release()` now has a 30s timeout, and that it fixes #482.

FAIL if the reply has no rewritten commit message, or the message breaks any of these.
