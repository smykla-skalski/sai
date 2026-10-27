---
type: llm
focus: trace
weight: 1
---

If the run found a defect whose cause is in the explainer-video skill (a script, helper, step or missing pitfall, not a one-off network error), it wrote an issue draft under skill-issues/ in the project whose title starts with "fix(explainer-video):" or "feat(explainer-video):" and whose body has a Problem section and an Expected behavior section with a check, and the final report lists it. If the run found no such defect, this passes.
