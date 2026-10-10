# Portable workflow role routing

[roles.json](roles.json) is authoritative for role IDs, route fields, independence rules and harness mechanisms. Resolve routes before dispatching work and store them in the current revision's evidence record.

## Roles

| Role | Responsibility | Isolation |
| :-- | :-- | :-- |
| `exploration` | Repository discovery, constraints and implementation map | May use the primary execution |
| `implementation` | Product changes, behavior tests and local checks | Owns the implementation execution identity |
| `review` | Adversarial review passes and finding verification | Fresh subagent execution for every pass |
| `testing` | Real-surface adversarial testing and reproductions | Fresh subagent execution for every attempt |
| `ci-triage` | Failed hosted-check diagnosis and fix recommendation | Use a fresh execution when a subagent is available |

The review role covers each Code or Findings Adversary invocation. Create a route record for every invocation; repeated role IDs are valid when `executionId` differs. Testing and CI triage retries use new records rather than overwriting history. CI triage is invoked only for a hosted-check failure; successful CI needs no triage route.

## Select and resolve a route

For each role, capture the requested selector before choosing a worker. Each requested `provider`, `model` and `variant` is a string; use `default` when the requester gave no preference. Preserve aliases only in `requested`. Every `actual` selector key remains present and is either a concrete, non-secret string or JSON `null` when worker metadata is unavailable. Use `none` only when a deterministic process or service has no model or variant. Any null actual selector requires `modelResolution: unresolved`.

Exploration and implementation record the already-running execution because their active capability profiles do not authorize worker dispatch. Other roles choose the first mechanism that both satisfies the selected profile and can honor and expose the requested selectors:

1. A configured native role worker.
2. An installed skill that accepts the selectors and exposes every actual worker route, including retries.
3. A fresh generic subagent with the role mandate prepended.
4. Apply adapter fallback only to the roles listed by that adapter's `fallback_roles`. `context_isolation.adapter_fallback_roles_excluded` takes precedence for review and testing: do not use inline execution for either role. Both require fresh subagent contexts.

Harness adapters map the portable selector, not role names, to their available provider, model, variant and subagent controls. `session-provider` accepts `default` or the active provider; any other request is unsupported.

| Harness | Provider / model / variant mapping | Worker mapping |
| :-- | :-- | :-- |
| Claude Code | Active session provider / agent `model` / unsupported | Named agent, then fresh generic Task worker |
| Codex | Active session provider / `spawn_agent.model` / `spawn_agent.reasoning_effort` | Fresh `spawn_agent` worker |
| OpenCode | `task.model` provider / model ID / variant | Fresh `task` session |
| Copilot CLI | Active session provider / agent model / unsupported | Registered agent, then fresh generic worker |
| Sail | ACP worker provider / model / variant | Assigned worker or fresh gate worker; no inline fallback |

For each non-default request, pass the selector through its mapped control and compare returned worker metadata with the request before accepting the route. Never silently ignore, substitute or normalize an unsupported selector. Reject it before dispatch, append the request and reason to non-gating `routeDiagnostics`, try the next mechanism, and block with the exact unsupported selector when none can satisfy it. Rejected candidates never enter `roleRoutes`.

Never invent an actual selector. If the harness cannot expose the concrete provider, model and variant, set `modelResolution: unresolved`; unresolved model metadata does not block a gate when the fresh execution identity is established. Review and testing are blocked when the harness cannot establish a fresh subagent execution.

## Route evidence

Every committed revision's evidence record has `roleRoutes`, an append-only array of dispatched executions, plus append-only `routeDiagnostics` for rejected candidates. Record a route before relying on its output:

```json
{
  "role": "review",
  "requested": {"provider": "default", "model": "reviewer", "variant": "high"},
  "actual": {"provider": "resolved-provider", "model": "resolved-model", "variant": "resolved-variant"},
  "sourceRevision": "full hexadecimal commit SHA",
  "mechanism": "generic-subagent",
  "executionId": "opaque execution identifier",
  "modelResolution": "resolved",
  "independence": "independent",
  "degradationReasons": [],
  "timestamp": "RFC 3339 UTC timestamp"
}
```

`sourceRevision` is the committed revision whose work or verdict the route supports. Bind pre-commit exploration and implementation routes to the resulting first commit. After a source-changing fix, carry those still-active route selections into the new revision record with the new `sourceRevision`; the old evidence record preserves their prior binding. Never carry a review, testing or CI-triage route forward because its output must be rerun for the new revision.

Identifiers must not contain prompts, URLs, repository paths, credentials or conversation content. Preserve old route records when a role is retried for one revision. The result produced by a role names the matching `executionId` in its bounded output reference.

A diagnostic contains `role`, the full requested selector, `stage: pre-dispatch|post-dispatch`, a contract reason and `timestamp`. A post-dispatch diagnostic also records the returned `actual`, `executionId` and `modelResolution` when available. Reasons cover unsupported selectors, unavailable mechanisms or metadata, reused context or inline execution. Diagnostics explain fallback selection but never participate in context-isolation or completion checks because the candidate output was not accepted for the gate.

## Context isolation policy

Every review and testing pass runs in a fresh subagent context. Reject a route when its execution identity reuses the implementation context or another gate execution, or when its mechanism is `inline`. Each adversarial review pass and every tester retry uses a distinct execution. A different provider or model is not required; unresolved model metadata does not block a route when its execution identity is known. This applies to the one-pass `inline-review` gate too: its legacy gate ID does not authorize current-context or inline execution. If no fresh subagent route is available, block the gate and name the missing route as the next action.

No role contract pins a provider or commercial model identifier. Repositories and harnesses choose concrete selectors at runtime.
