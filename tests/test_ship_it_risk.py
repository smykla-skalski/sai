"""Validate ship-it's portable risk-derived gate contract."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any, Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
POLICY_FILE: Final[Path] = SKILL_DIR / "references" / "risk-policy.json"
RISK_REFERENCE: Final[Path] = SKILL_DIR / "references" / "risk.md"
REVIEW_REFERENCE: Final[Path] = SKILL_DIR / "references" / "review.md"
TEST_REFERENCE: Final[Path] = SKILL_DIR / "references" / "test.md"
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"
RISKS: Final[tuple[str, ...]] = ("low", "medium", "high")
FULL_GATES: Final[set[str]] = {
    "local-checks",
    "adversarial-review",
    "adversarial-test",
    "ci",
    "hosted-review",
}
EXPECTED_GATES: Final[dict[str, list[str]]] = {
    "low": ["local-checks", "inline-review", "ci"],
    "medium": ["local-checks", "adversarial-review", "adversarial-test", "ci"],
    "high": [
        "local-checks",
        "adversarial-review",
        "adversarial-test",
        "ci",
        "hosted-review",
    ],
}
ADVERSARIAL_FALLBACKS: Final[dict[str, list[str]]] = {
    "inline-review": ["portable-review-fallback"],
    "adversarial-review": ["portable-review-fallback"],
    "adversarial-test": ["portable-test-fallback"],
}
SUPPORTED_GATES: Final[set[str]] = FULL_GATES | {"inline-review", "copilot-review"}
DIFF_CLASS_CASES: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (("README.md",), "docs"),
    (
        (
            "plugins/ship-it/skills/ship-it/references/risk.md",
            "plugins/ship-it/skills/ship-it/references/risk-policy.json",
        ),
        "docs",
    ),
    (("Brewfile", ".editorconfig", ".github/workflows/ci.yml", "mise.toml"), "docs"),
    (("docs/images/flow.png", "data/fixtures.csv", "LICENSE"), "docs"),
    (("scripts/bump_plugin_versions.py",), "code"),
    (("src/main.go", "Dockerfile", "Makefile", "bin/run.sh"), "code"),
    (("README.md", "scripts/bump_plugin_versions.py"), "code"),
    ((), "code"),
)
FALLBACKS: Final[dict[str, set[str]]] = {
    "inline-review": {"portable-review-fallback"},
    "adversarial-review": {"portable-review-fallback"},
    "adversarial-test": {"portable-test-fallback"},
    "copilot-review": {"human-review"},
}
GATE_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a risk-policy glob with the semantics risk.md documents."""
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            parts.append("[^/]")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(parts) + "$")


def classify(policy: dict[str, Any], changed_paths: tuple[str, ...]) -> str:
    """Return the diff class risk.md selects for the changed paths."""
    docs_globs = [
        glob_to_regex(glob) for glob in policy["diff_classes"]["docs"]["paths"]
    ]
    if changed_paths and all(
        any(docs_glob.match(path) for docs_glob in docs_globs)
        for path in changed_paths
    ):
        return "docs"
    return "code"


class ShipItRiskContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy: dict[str, Any] = json.loads(
            POLICY_FILE.read_text(encoding="utf-8")
        )
        self.guidance = RISK_REFERENCE.read_text(encoding="utf-8")

    def test_default_policy_selects_gates_by_level(self) -> None:
        self.assertEqual(
            self.policy["schema_version"], "sai.ship-it.risk-policy/v1"
        )
        self.assertEqual(tuple(self.policy["risk_order"]), RISKS)
        self.assertEqual(self.policy["default_risk"], "medium")
        self.assertNotIn("independent_review", self.policy)
        self.assertEqual(set(self.policy["policies"]), set(RISKS))
        self.assertEqual(self.policy["rules"], [])
        for risk, policy in self.policy["policies"].items():
            with self.subTest(risk=risk):
                gates = policy["required_gates"]
                self.assertEqual(gates, EXPECTED_GATES[risk])
                self.assertEqual(len(gates), len(set(gates)))
                expected_fallbacks = {
                    gate: fallbacks
                    for gate, fallbacks in ADVERSARIAL_FALLBACKS.items()
                    if gate in gates
                }
                self.assertEqual(policy["fallbacks"], expected_fallbacks)

    def test_low_risk_runs_one_isolated_review_and_no_manual_test(self) -> None:
        low = self.policy["policies"]["low"]["required_gates"]
        self.assertIn("inline-review", low)
        self.assertNotIn("adversarial-review", low)
        self.assertNotIn("adversarial-test", low)
        for risk in ("medium", "high"):
            with self.subTest(risk=risk):
                gates = self.policy["policies"][risk]["required_gates"]
                self.assertNotIn("inline-review", gates)
                self.assertIn("adversarial-review", gates)
                self.assertIn("adversarial-test", gates)
        self.assertEqual(
            set(self.policy["policies"]["high"]["required_gates"]), FULL_GATES
        )
        for expected in (
            "`inline-review` is the legacy gate ID for one review pass by a fresh subagent",
            "does not allow current-context or inline execution",
            "`gate-inline-review`",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.guidance)
        review = REVIEW_REFERENCE.read_text(encoding="utf-8")
        self.assertIn("risk policy selects `inline-review`", review)
        self.assertIn("fresh generic subagent context", review)
        test = TEST_REFERENCE.read_text(encoding="utf-8")
        self.assertIn("selects `adversarial-test` for `medium` and `high` only", test)

    def test_docs_class_is_low_and_mixed_diffs_take_code(self) -> None:
        docs = self.policy["diff_classes"]["docs"]
        self.assertEqual(list(self.policy["diff_classes"]), ["docs"])
        self.assertEqual(docs["risk"], "low")
        self.assertTrue(docs["paths"])
        self.assertEqual(len(docs["paths"]), len(set(docs["paths"])))
        for pattern in docs["paths"]:
            self.assertFalse(pattern.startswith("/"), pattern)
        for changed_paths, expected_class in DIFF_CLASS_CASES:
            with self.subTest(changed_paths=changed_paths):
                self.assertEqual(classify(self.policy, changed_paths), expected_class)
        for expected in (
            "A change set that mixes docs with code takes the `code` class.",
            "Diff classes are bundled-only.",
            "Reject a repository policy that contains `diff_classes`",
            "it can never widen a class or lower its level",
            "an empty level is never a floor",
            "`low` for `docs`, `medium` for `code`",
            "Raise it to a repository policy's `default_risk` when that is higher.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.guidance)

    def test_context_isolation_applies_to_every_review_gate(self) -> None:
        roles = json.loads(
            (SKILL_DIR / "references" / "roles.json").read_text(encoding="utf-8")
        )
        isolation = roles["context_isolation"]
        self.assertEqual(isolation["required_for"], ["review", "testing"])
        self.assertFalse(isolation["model_difference_required"])
        self.assertEqual(
            set(isolation["rejections"]),
            {"execution-context-reuse", "inline-execution"},
        )
        roles_guidance = (SKILL_DIR / "references" / "roles.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Every review and testing pass runs in a fresh subagent context", roles_guidance)
        self.assertIn("one-pass `inline-review` gate too", roles_guidance)
        evidence = (SKILL_DIR / "references" / "evidence.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Every review and testing route uses a fresh subagent execution", evidence)
        self.assertIn("Provider and model may match implementation", evidence)

    def test_hosted_review_is_resolved_by_release_policy(self) -> None:
        self.assertIn(
            "The hosted-review gate satisfies the reviewers resolved by repository release policy",
            self.guidance,
        )
        self.assertIn("it never implies Copilot", self.guidance)
        self.assertIn("cannot be replaced by another reviewer", self.guidance)

    def test_legacy_copilot_gate_has_deterministic_migration(self) -> None:
        for expected in (
            "Legacy v1 repository policies may also use `copilot-review`",
            "replace that gate with `hosted-review`",
            "copilot-pull-request-reviewer[bot]",
            "When that gate declares `human-review`",
            "any-authorized-reviewer",
            "deterministic compatibility migration",
            "Preserve the repository policy file and schema version",
        ):
            self.assertIn(expected, self.guidance)

    def test_policy_gate_and_fallback_ids_are_portable(self) -> None:
        for policy in self.policy["policies"].values():
            for gate in policy["required_gates"]:
                self.assertIsNotNone(GATE_ID.fullmatch(gate))
                self.assertIn(gate, SUPPORTED_GATES)
            for gate, fallbacks in policy["fallbacks"].items():
                self.assertIn(gate, policy["required_gates"])
                self.assertIn(gate, FALLBACKS)
                self.assertTrue(fallbacks)
                self.assertEqual(len(fallbacks), len(set(fallbacks)))
                for fallback in fallbacks:
                    self.assertIsNotNone(GATE_ID.fullmatch(fallback))
                    self.assertIn(fallback, FALLBACKS[gate])

    def test_legacy_model_independence_field_is_ignored(self) -> None:
        self.assertIn("Legacy `independent_review` fields are ignored", self.guidance)
        self.assertIn("context isolation is fixed by the role contract", self.guidance)

    def test_rejects_incompatible_fallback_fixture(self) -> None:
        fixture = {
            "required_gates": ["adversarial-review"],
            "fallbacks": {"adversarial-review": ["ci"]},
        }
        invalid = [
            fallback
            for gate, fallbacks in fixture["fallbacks"].items()
            for fallback in fallbacks
            if fallback not in FALLBACKS.get(gate, set())
        ]
        self.assertEqual(invalid, ["ci"])

    def test_selection_is_deterministic_and_monotonic(self) -> None:
        for expected in (
            "Raise it to the highest risk from every matching path rule.",
            "Treat `--risk <level>` from the original user request as another floor.",
            "Never lower the selected risk from the checkpoint, a matching rule or an earlier revision.",
            "only when the user explicitly authorizes overriding the named source and level",
            "Recompute after every source change or default-branch merge.",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.guidance)

    def test_gate_selection_is_reported_and_bound_to_evidence(self) -> None:
        for field in ("Risk:", "Diff class:", "Policy:", "Required gates:", "Source:"):
            self.assertIn(field, self.guidance)
        self.assertIn(
            "Repeat the level, diff class and gate set in the completion report.",
            self.guidance,
        )
        for expected in (
            "Create one required evidence result for each selected gate.",
            "each result must pass before its declared PR or merge boundary",
            "Without one, set the required gate's evidence to blocked",
            "never silently drop a gate",
        ):
            self.assertIn(expected.lower(), self.guidance.lower())

    def test_skill_loads_risk_guidance_progressively(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        link = "[references/risk.md](references/risk.md)"
        self.assertEqual(skill.count(link), 1)
        self.assertNotIn(self.guidance, skill)
        self.assertLessEqual(len(skill.encode()), 6000)


if __name__ == "__main__":
    unittest.main()
