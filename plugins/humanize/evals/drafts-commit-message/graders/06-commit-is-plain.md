---
type: llm
focus: last_message
weight: 1
---

Find the commit message in the reply, usually in a fenced code block.

PASS if all of these hold:
- The subject is in the imperative mood and has at most 72 characters. Conventional-commit format is optional.
- The body, if any, has at most 4 lines, not counting a "Fixes #91" line, and adds only detail the subject lacks: naming the subject's topic again to attach that detail is fine, saying a whole fact twice is not.
- It uses none of "enhance", "robust", "seamless", "crucial", "streamline", "leverage" or "improve resilience", has no em dash (—) and no filler.

FAIL if there is no commit message or any of these does not hold.
