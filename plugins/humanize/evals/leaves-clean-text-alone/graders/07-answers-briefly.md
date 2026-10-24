---
type: llm
focus: last_message
weight: 1
---

PASS if the reply is brief: it tells the user the file needs no changes in at most three sentences, with no bulleted or numbered list of the things it checked.
FAIL if the reply runs longer than three sentences, or walks through what it checked in a list.
