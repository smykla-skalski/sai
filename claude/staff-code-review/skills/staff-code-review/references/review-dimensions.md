# Review Dimensions — Detailed Checklists

Reference material for each review dimension. Read the section relevant to your assigned dimension.

## Table of Contents

1. [Architectural Alignment](#architectural-alignment)
2. [API Design](#api-design)
3. [Failure Mode Analysis](#failure-mode-analysis)
4. [Performance](#performance)
5. [Observability & Debuggability](#observability--debuggability)
6. [Security](#security)
7. [Migration & Rollback Safety](#migration--rollback-safety)
8. [Data Model Evolution](#data-model-evolution)
9. [Dependency Management](#dependency-management)
10. [Cross-Team Impact](#cross-team-impact)
11. [Backward Compatibility](#backward-compatibility)
12. [Dead Code](#dead-code)

---

## Architectural Alignment

Does this change fit the direction the system is heading, not just its current state?

- Does it introduce a new pattern that others will copy? If so, is it a pattern worth copying?
- Does it violate an ADR or established convention?
- Is it solving the right problem, or optimizing for the wrong layer?
- Does it create a fork where a shared solution exists?
- Would this approach survive a 10x growth in the relevant dimension (users, data, services)?

**Red flag:** A team adds a new service/abstraction for something an existing shared solution handles. The code may be correct, but it creates divergence.

---

## API Design

APIs are the hardest thing to change. Disproportionate scrutiny is warranted.

- Backward compatibility: what does adding/removing/renaming a field break?
- Hyrum's Law: will every observable behavior be depended on by someone?
- Deprecation story: how would you change this API if you needed to?
- Versioning: consistent with existing API strategy?
- Surface area: does the API expose implementation details that constrain future changes?
- Error contracts: are error codes/messages stable? Will consumers depend on them?
- Expand-and-contract for breaking changes: add new → migrate consumers → remove old

**Thresholds from industry:**
- Stripe: 20-page design docs for API changes
- Deprecation timelines: typically 6 months announcement, 12 months migration, 18-24 months removal

---

## Failure Mode Analysis

"Will you be able to diagnose a 3am outage effectively with this code?" — Yelp

- What happens when the downstream service is unavailable? Timeout? Retry? Circuit break?
- What happens with an unexpected exception? Is the error boundary appropriate?
- Blast radius: limited or cascading?
- Are retries idempotent? Will retrying cause double-processing?
- Behavior under partial failure (some shards/replicas fail, some succeed)?
- Race conditions in concurrent access paths?
- Thundering herd: what happens when a cache expires and all requests hit the backend?

---

## Performance

> **Agent 4 has a dedicated deep reference.** See `performance-scalability.md` for the full checklist with 3-tier severity, language-specific patterns, and USE/RED/Four Golden Signals frameworks.

Quick summary — key questions for triage:
- Does the performance profile hold at 10x current load?
- N+1 query patterns, unbounded fetching, missing pagination?
- Resource leaks (connections, goroutines, file handles)?
- Missing timeouts on outbound calls?
- Cache strategy present and stampede-safe?

---

## Observability & Debuggability

Charity Majors' standard: before approving, can you answer "how will I know when this isn't working?"

- Structured logging with correlation IDs on new code paths
- Metrics/counters for new operations (request rates, error rates, latencies)
- Distributed traces spanning service boundaries
- Alert-ability: is there a metric that would trigger an alert if this breaks?
- Log levels appropriate: don't spam error logs with expected conditions
- Google's Four Golden Signals coverage: Latency, Errors, Traffic, Saturation

**Anti-pattern:** Approving a new critical feature with no instrumentation because "we can add metrics later." In practice, "later" means "after the first incident."

---

## Security

- All inputs validated/sanitized
- No secrets/credentials in code or logs
- Authentication required on all endpoints
- Authorization checks correct (RBAC/ABAC)
- Parameterized queries (no string interpolation in SQL)
- No sensitive data in error messages
- Cryptographic algorithms are current standard (AES-256, SHA-256+)
- SSRF, command injection, path traversal risks
- PII in logs or error responses
- CORS configuration appropriate
- Rate limiting on public endpoints

---

## Migration & Rollback Safety

For database migrations:
- Backward-compatible with current application version?
- App can run with both old and new schema simultaneously (blue/green)?
- Rollback procedure documented?
- Destructive operations (drops, type changes) explicitly called out?
- Tested against production-scale data volumes?
- Expand-and-contract for breaking schema changes?
- No full table scans in migration?

For application code:
- Feature flags allowing disable without rollback?
- Canary deployment with health-check gates?
- Progressive rollout path (internal → limited → full)?

---

## Data Model Evolution

Data models are among the hardest things to change.

- Impact on existing records?
- Future query patterns: does the model accommodate them?
- Unbounded growth? (No pagination, no TTL, no archival strategy)
- Relationships between entities: painful joins at scale?
- Intentional denormalization documented?
- What happens to existing data when the code deploys?
- Indexing strategy for new access patterns?

---

## Dependency Management

Treat new dependencies as untrusted third-party input.

- License compatibility with the project
- Maintenance status: actively maintained? Last release?
- Security track record: recent CVEs?
- Transitive dependency footprint: what does adding this pull in?
- Vendor lock-in risk: commodity library or tight coupling?
- Supply chain risk: well-known/widely-used or obscure?
- Could this be implemented without the dependency given the scope of use?
- Is there an internal library that already solves this?

**Context:** Malicious packages increased 156% YoY. 90% of modern applications are open-source components.

---

## Cross-Team Impact

- Which teams consume the affected APIs/events? Were they notified?
- Does this create a new dependency that other teams will absorb?
- Does this drift from the "paved road" / golden path that platform teams support?
- Will this require on-call burden for another team?
- Does this change a shared library or internal package?
- If code review reveals competing patterns for the same problem, that signals an undocumented decision that needs an ADR.

---

## Backward Compatibility

> **Agent 5 has a dedicated deep reference.** See `backward-compatibility.md` for the full checklist with 3-tier severity, Hyrum's Law analysis, expand-and-contract patterns, and cross-service coordination guidance.

Quick summary — key questions for triage:
- Does this remove, rename, or change types of any public API surface?
- Are new required fields added to existing requests/schemas?
- Do behavioral changes (defaults, error codes, ordering) affect existing consumers?
- Is there a migration path (expand-and-contract, versioned endpoints, deprecation notices)?
- Can the system rollback after this deploys?
- Do wire format changes require coordinated multi-service deployment?

---

## Dead Code

> **Agent 7 has a dedicated deep reference.** See `dead-code.md` for the full checklist with detection categories, language-specific patterns, and false positive guardrails.

Quick summary — key questions:
- Does the PR introduce functions, types, or exports with zero callers?
- Does the PR orphan existing code by changing call sites without removing the old target?
- Are there commented-out code blocks that should be deleted (version control has history)?
- Is there unreachable code after unconditional returns, impossible branches, or exhaustive switches?
- Do any tests cover functionality that was removed or refactored by the PR?

**Anti-pattern:** Leaving orphaned helper functions after a refactor because "someone might need them later." They won't — and they'll mislead the next person reading the module.

---

## Sources

- Google eng-practices: https://google.github.io/eng-practices/review/reviewer/
- GitHub Staff Engineer philosophy: https://github.blog/developer-skills/github/how-to-review-code-effectively-a-github-staff-engineers-philosophy/
- Pragmatic Engineer: https://blog.pragmaticengineer.com/good-code-reviews-better-code-reviews/
- Conventional Comments: https://conventionalcomments.org/
- Netlify Feedback Ladders: https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/
- The Staff Engineer's Path — Tanya Reilly
- Staff Engineer — Will Larson
- Charity Majors on shipping safely: https://charity.wtf/
