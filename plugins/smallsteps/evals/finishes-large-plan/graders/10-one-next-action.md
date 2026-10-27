---
type: llm
focus: last_message
weight: 1
---

PASS if the reply shows one next action (downloading last month's transactions as CSV, today at 20:00), its Done when (seeing the total per category for last month) and the note path, and says that no Miro board was made because Miro is not connected.
            FAIL if the reply lists the Next or Later results as things to do now, gives more than one next action, claims a Miro board exists, or leaves out the note path.
