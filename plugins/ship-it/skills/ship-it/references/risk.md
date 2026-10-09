# Risk-derived validation gates

Select gates from the committed revision before validation. The portable default is [risk-policy.json](risk-policy.json). A repository may replace it with `.sai/ship-it-risk.json` using the same versioned format.

## Policy format

The document has `schema_version: sai.ship-it.risk-policy/v1`, `risk_order: [low, medium, high]`, one `default_risk`, `independent_review: strict|degraded`, policies for all three levels, and ordered path `rules`. Each policy has unique non-empty `required_gates` and a `fallbacks` object mapping an unavailable gate to a non-empty ordered list of compatible fallback mechanisms; the object is empty when no selected gate has one. IDs use lowercase letters, digits and hyphens. Missing `independent_review` in a legacy v1 policy means `strict`; reject every other value.

The bundled policy also declares `diff_classes`: each class ID maps to `{"risk": <level>, "paths": [globs]}`. Diff classes are bundled-only. Reject a repository policy that contains `diff_classes`: a repository raises matched paths with `rules`; it can never widen a class or lower its level.

An optional root `ci_reruns` object authorizes reruns only for its unique `allowed_classifications` (`flaky`, `infrastructure` or `unknown`) and positive `max_reruns_per_job`. The limit applies to a revision/workflow/job group across all attempts. It never permits a `code` rerun instead of a source fix. Absence authorizes no reruns; the bundled policy intentionally omits it. Invalid values reject the repository policy.

A rule is `{"risk":"high","paths":["infra/**","**/auth/**"]}`. Paths are repository-relative POSIX globs: `*` and `?` stay within one component; `**` crosses components, and a leading `**/` also matches a path at the repository root. Match against every tracked, staged, untracked or deleted path changed from the merge-base with the current default branch. Reject an invalid policy; never partially apply it.

The supported gate IDs are `local-checks` (implementation, due before PR), `inline-review` (review, due before PR), `adversarial-review` (review, due before PR), `adversarial-test` (test, due before PR), `ci` (PR loop, due before merge), and `hosted-review` (PR loop, due before merge). The hosted-review gate satisfies the reviewers resolved by repository release policy; it never implies Copilot. Legacy v1 repository policies may also use `copilot-review`; normalize it as described below. Reject every other ID.

Fallback mechanisms are boundary-compatible, not substitute gates. `portable-review-fallback` is valid only for `adversarial-review`, `portable-test-fallback` only for `adversarial-test`, and legacy `human-review` only for legacy `copilot-review`. No fallback is defined for `local-checks`, `inline-review`, `ci` or `hosted-review`; release policy names the actual required reviewer and cannot be replaced by another reviewer. Reject every other mapping. Run the first available declared mechanism and record both IDs. Without one, set the required gate's evidence to blocked and stop. Never silently drop a gate or move its evidence boundary.

For a valid v1 repository policy containing `copilot-review`, replace that gate with `hosted-review` in the selected checkpoint gates and add a normalized required reviewer for actor `copilot-pull-request-reviewer[bot]`, request target `copilot-pull-request-reviewer` and requirement `review`. When that gate declares `human-review` and Copilot is unavailable, replace the Copilot entry with `any-authorized-reviewer`, requirement `approval` and request `automatic`; record `human-review` as the fallback mechanism in evidence. This is a deterministic compatibility migration, not a policy override. Preserve the repository policy file and schema version. New policies use `hosted-review` and the release-policy file instead.

Example repository policy:

```json
{
  "schema_version": "sai.ship-it.risk-policy/v1",
  "risk_order": ["low", "medium", "high"],
  "default_risk": "low",
  "independent_review": "strict",
  "policies": {
    "low": {
      "required_gates": ["local-checks", "inline-review", "ci"],
      "fallbacks": {}
    },
    "medium": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci"],
      "fallbacks": {
        "adversarial-review": ["portable-review-fallback"],
        "adversarial-test": ["portable-test-fallback"]
      }
    },
    "high": {
      "required_gates": ["local-checks", "adversarial-review", "adversarial-test", "ci", "hosted-review"],
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

## Gate shapes

`inline-review` is one review pass by the current execution: hunt concrete defects and unmet acceptance criteria in `git diff origin/<default>...HEAD`, prove each finding with `file:line`, and reply `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`. It dispatches no Code or Findings Adversary. Sail never runs a gate inline, so there one fresh gate worker makes the single pass. Record a `review` route with the actual mechanism (`inline`, or the Sail worker's) and `independence: not-applicable`; the strict independent-review policy governs `adversarial-review` routes only, because `inline-review` claims no independence. Its evidence result is `gate-inline-review`. A `NEEDS_FIXES` verdict spends the same fix pass and convergence counters as `adversarial-review`.

`adversarial-review` is the two-pass cycle (Code Adversary, then Findings Adversary) under the convergence policy, and `adversarial-test` is the adversarial manual-test pass. The capability fact `review_gate_required` is true when either review gate is selected; `test_gate_required` is true only when `adversarial-test` is. A level without a review gate runs no review, and a level without `adversarial-test` runs no manual test.

## Bundled gate sets

| Risk | Review | Manual test | Required gates |
| :-- | :-- | :-- | :-- |
| `low` | one inline pass | none | `local-checks`, `inline-review`, `ci` |
| `medium` | one adversarial cycle | one adversarial pass | `local-checks`, `adversarial-review`, `adversarial-test`, `ci` |
| `high` | one adversarial cycle | one adversarial pass | `local-checks`, `adversarial-review`, `adversarial-test`, `ci`, `hosted-review` |

`high` keeps the full sequence of every supported gate. Release policy still adds `ci` and `hosted-review` as floors whenever the repository requires checks or reviewers, so a lower level never drops a repository control.

## Diff class

Classify the committed change set before selecting a level. The change set is every path changed from the merge-base with the current default branch, as for rules. Its class is `docs` when it is non-empty and every path matches a `diff_classes.docs` glob; otherwise it is `code`. A change set that mixes docs with code takes the `code` class. The bundled docs class covers documentation (`*.md`, `*.rst`, `*.txt`, license files), configuration (`*.json`, `*.yaml`, `*.toml`, `*.ini`, lock files, `Brewfile`, dotfile config) and data (`*.csv`, `*.ndjson`, `*.xml`, images); its level is `low`. The `code` class level is the bundled `default_risk`, `medium`. Both class levels are floors: a repository policy's `default_risk` raises every change set when it is higher and never lowers one, so `default_risk: low` in a repository policy keeps the bundled class levels. A repository that treats some of those files as product, or wants adversarial gates on executable configuration such as CI workflow definitions and dependency manifests, raises their paths with a rule, for example `{"risk": "medium", "paths": ["plugins/**", ".github/workflows/**"]}`.

Before the first commit there is no committed change set: leave `risk.level`, `risk.diffClass` and `risk.requiredGates` empty and record only the policy source and any `--risk` floor. The first committed revision selects the class and level; an empty level is never a floor. After that, recomputation raises the level when the class changes but never lowers it.

## Deterministic selection

1. Load the repository policy, or the bundled policy when it is absent. Diff classes always come from the bundled policy.
2. Classify the change set and start at its bundled class level: `low` for `docs`, `medium` for `code`. Raise it to a repository policy's `default_risk` when that is higher. Raise it to the highest risk from every matching path rule.
3. Treat `--risk <level>` from the original user request as another floor. An agent may raise this result for an identified risk and record its reason.
4. Never lower the selected risk from the checkpoint, a matching rule or an earlier revision. Lower it only when the user explicitly authorizes overriding the named source and level; record that authorization in the checkpoint.
5. Recompute after every source change or default-branch merge. A higher result invalidates the revision's gate evidence. A lower recomputation keeps the prior floor unless the user authorized the reduction.

The policy's `independent_review` field authorizes role routing. `strict` enforces an independently resolved review route. `degraded` explicitly authorizes a weaker route only when its evidence records every degradation reason and the repository policy path. A command-line risk floor never changes this field.

Before the first validation command, report exactly:

```text
Risk: <low|medium|high>
Diff class: <docs|code> (<n> changed path(s))
Policy: <repository-relative path|bundled default>
Required gates: <ordered gate IDs>
Source: <diff class, matching rules, explicit user choice, agent elevation, or recorded override>
```

Store the selected level, diff class, policy source, matched rules, required gates and any override authorization in the checkpoint (`risk.level`, `risk.diffClass`, `risk.policySource`, `risk.matchedRules`, `risk.requiredGates`, `risk.overrideAuthorization`). Repeat the level, diff class and gate set in the completion report. Create one required evidence result for each selected gate. Evidence belongs to the exact revision: each result must pass before its declared PR or merge boundary. Gates not selected create no required result and do not run.
