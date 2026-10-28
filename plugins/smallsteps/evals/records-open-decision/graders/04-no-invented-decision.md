---
type: llm
focus:
  source: file
  path: ideas/contract-format.md
weight: 1
---

Before this run the note said: "Then: if right, I will write the rules next. If wrong," and the user then said, word for word: "Honestly, I don't know yet. I'll decide when I see what they say."
PASS if the note keeps "if right, I will write the rules next" and records the wrong case as open, or as a decision made after the result, with no decision the user did not give.
FAIL if the note adds a decision for the wrong case, such as rewriting the example or simplifying the format, or changes the decision for the right case.
