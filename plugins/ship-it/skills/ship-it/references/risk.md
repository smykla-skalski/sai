# Risk-derived validation gates

Select gates from the committed revision before validation. The portable default is [risk-policy.json](risk-policy.json). A repository may replace it with `.sai/ship-it-risk.json` using the same versioned format.

## Policy format

The document has `schema_version: sai.ship-it.risk-policy/v1`, `risk_order: [low, medium, high]`, one `default_risk`, policies for all three levels, and ordered path `rules`. Each policy has unique non-empty `required_gates` and a `fallbacks` object mapping an unavailable gate to a non-empty ordered list of substitute gates. Gate IDs use lowercase letters, digits and hyphens.

A rule is `{"risk":"high","paths":["infra/**","**/auth/**"]}`. Paths are repository-relative POSIX globs: `*` and `?` stay within one component; `**` crosses components. Match against every tracked, staged, untracked or deleted path changed from the merge-base with the current default branch. Reject an invalid policy; never partially apply it.

The supported gate IDs are `local-checks` (implementation, due before PR), `adversarial-review` (review, due before PR), `adversarial-test` (test, due before PR), `ci` (PR loop, due before merge), and `copilot-review` (PR loop, due before merge). Reject unknown IDs. If the harness cannot execute a required gate, run its first available policy-declared fallback and record both IDs. Without an available declared fallback, set the evidence result to blocked and stop. Never silently drop a gate.

Example repository policy:

```json
{
  "schema_version": "sai.ship-it.risk-policy/v1",
  "risk_order": ["low", "medium", "high"],
  "default_risk": "low",
  "policies": {
    "low": {
      "required_gates": ["local-checks", "adversarial-review", "ci"],
      "fallbacks": {}
    },
    "medium": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci"],
      "fallbacks": {}
    },
    "high": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci", "copilot-review"],
      "fallbacks": {}
    }
  },
  "rules": [
    {"risk": "medium", "paths": ["src/**"]},
    {"risk": "high", "paths": ["infra/**", "**/auth/**"]}
  ]
}
```

## Deterministic selection

1. Load the repository policy, or the bundled policy when it is absent.
2. Start at `default_risk`. Raise it to the highest risk from every matching path rule.
3. Treat `--risk <level>` from the original user request as another floor. An agent may raise this result for an identified risk and record its reason.
4. Never lower the selected risk from the checkpoint, a matching rule or an earlier revision. Lower it only when the user explicitly authorizes overriding the named source and level; record that authorization in the checkpoint.
5. Recompute after every source change or default-branch merge. A higher result invalidates the revision's gate evidence. A lower recomputation keeps the prior floor unless the user authorized the reduction.

Before the first validation command, report exactly:

```text
Risk: <low|medium|high>
Policy: <repository-relative path|bundled default>
Required gates: <ordered gate IDs>
Source: <default, matching rules, explicit user choice, agent elevation, or recorded override>
```

Store the selected level, policy source, matched rules, required gates and any override authorization in the checkpoint. Create one required evidence result for each selected gate. Evidence belongs to the exact revision: each result must pass before its declared PR or merge boundary. Gates not selected create no required result and do not run. The bundled policy selects the existing full sequence at every level, preserving behavior when a repository has no policy.
