---
type: llm
focus: last_message
weight: 1
---

PASS if the reply tells the user that setup.md has no AI writing patterns (or already reads naturally) and does not present a rewritten version.
Saying the single em dash is fine, or naming an alternative in case a style guide bans dashes, still counts as leaving the file alone.

FAIL if the reply presents a rewritten file, or reports problems that are not in the file. The file has one em dash used the way a person would, normal contractions, no AI vocabulary, no boldface, no emoji, no filler and no chatbot phrases, so listing the single dash or the contractions as a pattern to fix is a FAIL.
