---
type: llm
focus: last_message
weight: 1
---

PASS if the reply asks exactly one question, and it is a playback: it lists the drafted items (such as the action card and the test of the riskiest guess) and asks whether they are right, for example "Is this right?".
            FAIL if the reply asks for another single field (such as Done when, Need or a time box) instead of a playback, asks two or more questions, or asks nothing.
