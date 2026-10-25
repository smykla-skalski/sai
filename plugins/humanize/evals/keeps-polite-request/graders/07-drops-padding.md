---
type: llm
focus: last_message
weight: 1
---

Find the rewritten email in the reply. Ignore any pattern report and any quotes of the original.

PASS if the rewritten email has none of "I hope this email finds you well", "just wanted to reach out", "might possibly", "extremely grateful for any assistance" or "Thanks so much in advance" (a plain "Thanks" is fine), and its body between the greeting and the sign-off has at most 40 words.
FAIL if there is no rewritten email, any of that padding remains, or the body runs longer than 40 words.
