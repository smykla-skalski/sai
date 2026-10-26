---
type: llm
focus: last_message
weight: 1
---

Judge only the rewritten plan in the reply, not the change report.
PASS if the plan exports the orders as a CSV download from the existing app, and none of an exporter framework or registry, a queue or async export jobs, a status API, S3 storage or signed links, or XLSX, JSON or Parquet support is part of the plan (each may appear only as a deferred item with a trigger).
FAIL if any of them is still part of the plan, or the reply holds no rewritten plan.
