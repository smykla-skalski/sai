---
type: llm
focus: last_message
weight: 1
---

The user answered the appetite question with "as much time as needed. There is no deadline."
PASS if the reply asks exactly one question, and it does not ask for a number of hours or days, a deadline, or the appetite again.
FAIL if it asks for a fixed amount of time in any form, asks the appetite again, or asks two or more questions.
