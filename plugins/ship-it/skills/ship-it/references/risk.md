# Risk-derived validation gates

Select gates from the committed revision before validation. The portable default is [risk-policy.json](risk-policy.json). A repository may replace it with `.sai/ship-it-risk.json` using the same versioned format.

## Policy format

The document has `schema_version: sai.ship-it.risk-policy/v1`, `risk_order: [low, medium, high]`, one `default_risk`, `independent_review: strict|degraded`, policies for all three levels, and ordered path `rules`. Each policy has unique non-empty `required_gates` and a `fallbacks` object mapping an unavailable gate to a non-empty ordered list of compatible fallback mechanisms. IDs use lowercase letters, digits and hyphens. Missing `independent_review` in a legacy v1 policy means `strict`; reject every other value.

An optional root `ci_reruns` object authorizes reruns only for its unique `allowed_classifications` (`flaky`, `infrastructure` or `unknown`) and positive `max_reruns_per_job`. The limit applies to a revision/workflow/job group across all attempts. It never permits a `code` rerun instead of a source fix. Absence authorizes no reruns; the bundled policy intentionally omits it. Invalid values reject the repository policy.

A rule is `{"risk":"high","paths":["infra/**","**/auth/**"]}`. Paths are repository-relative POSIX globs: `*` and `?` stay within one component; `**` crosses components. Match against every tracked, staged, untracked or deleted path changed from the merge-base with the current default branch. Reject an invalid policy; never partially apply it.

The supported gate IDs are `local-checks` (implementation, due before PR), `adversarial-review` (review, due before PR), `adversarial-test` (test, due before PR), `ci` (PR loop, due before merge), and `copilot-review` (PR loop, due before merge). Reject unknown IDs.

Fallback mechanisms are boundary-compatible, not substitute gates. `portable-review-fallback` is valid only for `adversarial-review`; `portable-test-fallback` only for `adversarial-test`; and `human-review` only for `copilot-review`. No fallback is defined for `local-checks` or `ci`. Reject every other mapping. Run the first available declared mechanism and record both IDs. Without one, set the required gate's evidence to blocked and stop. Never silently drop a gate or move its evidence boundary.

Example repository policy:

```json
{
  "schema_version": "sai.ship-it.risk-policy/v1",
  "risk_order": ["low", "medium", "high"],
  "default_risk": "low",
  "independent_review": "strict",
  "policies": {
    "low": {
      "required_gates": ["local-checks", "adversarial-review", "ci"],
      "fallbacks": {"adversarial-review": ["portable-review-fallback"]}
    },
    "medium": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci"],
      "fallbacks": {
        "adversarial-review": ["portable-review-fallback"],
        "adversarial-test": ["portable-test-fallback"]
      }
    },
    "high": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci", "copilot-review"],
      "fallbacks": {
        "adversarial-review": ["portable-review-fallback"],
        "adversarial-test": ["portable-test-fallback"]
      }
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

The policy's `independent_review` field authorizes role routing. `strict` enforces an independently resolved review route. `degraded` explicitly authorizes a weaker route only when its evidence records every degradation reason and the repository policy path. A command-line risk floor never changes this field.

Before the first validation command, report exactly:

```text
Risk: <low|medium|high>
Policy: <repository-relative path|bundled default>
Required gates: <ordered gate IDs>
Source: <default, matching rules, explicit user choice, agent elevation, or recorded override>
```

Store the selected level, policy source, matched rules, required gates and any override authorization in the checkpoint. Create one required evidence result for each selected gate. Evidence belongs to the exact revision: each result must pass before its declared PR or merge boundary. Gates not selected create no required result and do not run. The bundled policy selects the existing full sequence at every level, preserving behavior when a repository has no policy.
