---
type: llm
focus: last_message
weight: 1
---

The user asked: "Suggest something small I can do instead."
PASS if the reply proposes exactly one small action that takes minutes, says what it is for, and asks whether it is right.
FAIL if it proposes two or more actions, gives no purpose, proposes an action that needs a system that does not exist yet, or only asks what the user wants to do.
