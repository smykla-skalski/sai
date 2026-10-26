---
type: llm
focus:
  source: file
  path: docs/plan.md
weight: 1
---

PASS if the proposed architecture is one application (one deployable) with one database, and none of the five microservices, Kafka, the Redis cluster, Kubernetes with Istio or the ERP plugin framework is part of the proposed design.
FAIL if any of them is still part of the proposed design.
