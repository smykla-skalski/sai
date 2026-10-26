---
type: llm
focus: last_message
weight: 1
---

PASS if the reply is a change report: a table whose columns are #, Rule and Change, each row naming a rule ID, followed by a summary line with counts and the word counts, with no copy of the rewritten plan and no offer.
FAIL if the table is missing, a row has no rule ID, the reply copies the plan, or it ends with an offer or question.
