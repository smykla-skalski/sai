---
type: llm
focus: last_message
weight: 1
---

The note's Next results, in order, were: "A review of the example for gaps" and "Rules that a future system could check".
PASS if the reply lets the user choose what comes next, offers the review of the example as an option, and asks exactly one question. It may also suggest another result, a change of direction or a pause.
FAIL if it treats a suggested next result as the user's decision, omits the review option, or asks two or more questions.
