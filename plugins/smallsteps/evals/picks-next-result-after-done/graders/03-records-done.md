---
type: llm
focus:
  source: file
  path: ideas/contract-format.md
weight: 1
---

The user reported, word for word: "Done. I wrote the example for "Authorize a payment": two inputs, amount as an integer in minor units and currency as a three-letter code, and three results, approved, declined and unknown. I listed two gaps: the error result, and how a contract refers to it."
PASS if the note records the new completed example and its two gaps, preserves the earlier author review and its limitation, and keeps both the current format decision and the earlier change from YAML alone.
FAIL if it drops that history, marks an unrun reader or system check done, or invents a result.
