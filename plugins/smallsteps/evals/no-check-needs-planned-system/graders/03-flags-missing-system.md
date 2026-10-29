---
type: llm
focus: last_message
weight: 1
---

The note plans "A system that checks contracts automatically" only as a Later result. The user said: "Done when the checker accepts the example without errors."
PASS if the reply says the checker does not exist yet, offers a feasible present check, and asks exactly one question. It may also offer to change the order and build the checker first.
FAIL if it treats the unavailable checker as a feasible current check, claims an unconfirmed tool already exists, or asks two or more questions.
