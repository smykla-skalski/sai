# Portable workflow role routing

[roles.json](roles.json) is authoritative for role IDs, route fields, independence rules and harness mechanisms. Resolve routes before dispatching work and store them in the current revision's evidence record.

## Roles

| Role | Responsibility | Isolation |
| :-- | :-- | :-- |
| `exploration` | Repository discovery, constraints and implementation map | May use the primary execution |
| `implementation` | Product changes, behavior tests and local checks | Owns the implementation execution identity |
| `review` | Adversarial review passes and finding verification | Independent when review policy is strict |
| `testing` | Real-surface adversarial testing and reproductions | Use a fresh execution when a subagent is available |
| `ci-triage` | Failed hosted-check diagnosis and fix recommendation | Use a fresh execution when a subagent is available |

The review role covers each Code or Findings Adversary invocation. Create a route record for every invocation; repeated role IDs are valid when `executionId` differs. Testing and CI triage retries use new records rather than overwriting history. CI triage is invoked only for a hosted-check failure; successful CI needs no triage route.

## Select and resolve a route

For each role, capture the requested selector before choosing a worker. Each requested `provider`, `model` and `variant` is a string; use `default` when the requester gave no preference. Preserve aliases only in `requested`. Every `actual` selector key remains present and is either a concrete, non-secret string or JSON `null` when worker metadata is unavailable. Use `none` only when a deterministic process or service has no model or variant. Any null actual selector requires `modelResolution: unresolved`.

Exploration and implementation record the already-running execution because their active capability profiles do not authorize worker dispatch. Other roles choose the first mechanism that both satisfies the selected profile and can honor and expose the requested selectors:

1. A configured native role worker.
2. An installed skill that accepts the selectors and exposes every actual worker route, including retries.
3. A fresh generic subagent with the role mandate prepended.
4. Outside Sail, inline execution only when the active independence policy permits it.

Harness adapters map the portable selector, not role names, to their available provider, model, variant and subagent controls. `session-provider` accepts `default` or the active provider; any other request is unsupported.

| Harness | Provider / model / variant mapping | Worker mapping |
| :-- | :-- | :-- |
| Claude Code | Active session provider / agent `model` / unsupported | Named agent, then fresh generic Task worker |
| Codex | Active session provider / `spawn_agent.model` / `spawn_agent.reasoning_effort` | Fresh `spawn_agent` worker |
| OpenCode | `task.model` provider / model ID / variant | Fresh `task` session |
| Copilot CLI | Active session provider / agent model / unsupported | Registered agent, then fresh generic worker |
| Sail | ACP worker provider / model / variant | Assigned worker or fresh gate worker; no inline fallback |

For each non-default request, pass the selector through its mapped control and compare returned worker metadata with the request before accepting the route. Never silently ignore, substitute or normalize an unsupported selector. Reject it before dispatch, append the request and reason to non-gating `routeDiagnostics`, try the next mechanism, and block with the exact unsupported selector when none can satisfy it. Rejected candidates never enter `roleRoutes`.

Never invent an actual selector. If the harness cannot expose the concrete provider, model and variant, set `modelResolution: unresolved`. A strict independent review then stops before dispatch. Other roles may proceed only under a policy that permits degraded execution and must expose the degradation in evidence.

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

A diagnostic contains `role`, the full requested selector, `reason: unsupported-selector|unavailable-mechanism|metadata-unavailable`, and `timestamp`. Diagnostics explain fallback selection but never participate in independence or completion checks because no worker executed.

## Independent review policy

Strict independent review is the default. Before each review dispatch, compare its resolved route with the implementation route for the same revision. Reject the route when any of these is true:

- Actual provider and model equal the implementation provider and model, regardless of variant.
- `modelResolution` is `unresolved`, including a requested alias without a concrete actual model.
- `executionId` equals the implementation execution ID or otherwise reuses its context.
- `mechanism` is `inline`.

Try the next adapter mechanism after a rejection. If no strict route remains, block the review gate and name the missing independent route as the next action.

A repository risk policy with `independent_review: degraded` explicitly disables strict independence. Then execution may continue only with `independence: degraded`, a non-empty `degradationReasons` array containing every failed strict rule, and the policy path in the evidence output reference. Missing `independent_review` means `strict`. The gate remains visibly degraded; a fallback never records `independent`.

No role contract pins a provider or commercial model identifier. Repositories and harnesses choose concrete selectors at runtime.
