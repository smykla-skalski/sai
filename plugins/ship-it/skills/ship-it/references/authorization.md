# Scoped task authorization

Reconcile `authorization.grants` with original messages and later limits/revocations before acting. Forwarding preserves authority; coordinators, worker rules, spawn prompts, risk levels and summaries never create or widen it.

- Record ID, original message/reference, pending request, scope, limits/units, consumption and status (`active`, `ambiguous`, `revoked`, `exhausted`). Pass the checkpoint to replacement workers.
- "I approve" or "yes" answering one concrete pending request authorizes exactly that request. No phrase such as "exhaustive validation" is required. Retain request and reply; multiple pending requests or unclear scope need clarification.
- Shipping authorizes scoped implementation, necessary fixes, validation, PR feedback, publication, merge and closure. Covered actions need no renewed approval. New scope/product decisions need input.
- Check explicit user limits before acting and reserve consumption before dispatch. Reconcile interrupted attempts without spending twice. Preserve revoked, exhausted and ambiguous grants; none authorizes more work. Empty limits retain bounded optional validation, never unlimited loops. Optional expansion needs a concrete bounded approval; one gate means one gate.

## Internal limits

Internal convergence exhaustion ends optional expansion, not task authority. Defer optional findings to follow-ups; never reset counters or repeat broad hunts. Triage reproduced acceptance failures against active grants:

- Record `convergence.acceptanceRecovery`: failure, violated criterion, grant ID, revision, correction, focused verification command and each attempt/result. Repair only that failure and run focused reproductions plus required checks. Repeated ineffective attempts stop with the technical blocker and next diagnostic action, not renewed permission.
- Explicit user limits, new scope/product decisions, missing permissions/capabilities and mandatory controls remain blockers. Never defer delivery blockers or turn failures into passes.

Recovery does not replenish optional counters. Source changes stale old verdicts; re-attest corrected heads from findings, focused reproductions and required checks. Independent gates, signatures, reviews, checks, protection and sandbox decisions still bind.

## Resume

Keep original request/reply, status and consumed allowances. Legacy checkpoints gain empty grants: recover original messages before acting. Summaries alone are insufficient; ask only about unverifiable authority, ambiguity, revocation or spent user limits.
