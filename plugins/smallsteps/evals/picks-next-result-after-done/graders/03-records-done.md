---
type: llm
focus:
  source: file
  path: ideas/contract-format.md
weight: 1
---

The user reported, word for word: "Done. I wrote the example for "Authorize a payment": two inputs, amount as an integer in minor units and currency as a three-letter code, and three results, approved, declined and unknown. I listed two gaps: the error result, and how a contract refers to it."
PASS if the note's "Checks" list has an item for writing the example, with the status done, what it showed (the operation with its two inputs and three results) and the two gaps.
FAIL if there is no such item, its status is not done, or it states a result the user did not report, such as a reader test or a check by a system.
