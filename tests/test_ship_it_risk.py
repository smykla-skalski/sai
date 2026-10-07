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
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"
RISKS: Final[tuple[str, ...]] = ("low", "medium", "high")
FULL_GATES: Final[set[str]] = {
    "local-checks",
    "adversarial-review",
    "adversarial-test",
    "ci",
    "hosted-review",
}
SUPPORTED_GATES: Final[set[str]] = FULL_GATES | {"copilot-review"}
FALLBACKS: Final[dict[str, set[str]]] = {
    "adversarial-review": {"portable-review-fallback"},
    "adversarial-test": {"portable-test-fallback"},
    "copilot-review": {"human-review"},
}
GATE_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ShipItRiskContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy: dict[str, Any] = json.loads(
            POLICY_FILE.read_text(encoding="utf-8")
        )
        self.guidance = RISK_REFERENCE.read_text(encoding="utf-8")

    def test_default_policy_preserves_full_validation(self) -> None:
        self.assertEqual(
            self.policy["schema_version"], "sai.ship-it.risk-policy/v1"
        )
        self.assertEqual(tuple(self.policy["risk_order"]), RISKS)
        self.assertIn(self.policy["default_risk"], RISKS)
        self.assertEqual(self.policy["independent_review"], "strict")
        self.assertEqual(set(self.policy["policies"]), set(RISKS))
        self.assertEqual(self.policy["rules"], [])
        for risk, policy in self.policy["policies"].items():
            with self.subTest(risk=risk):
                gates = policy["required_gates"]
                self.assertEqual(set(gates), FULL_GATES)
                self.assertEqual(len(gates), len(set(gates)))
                self.assertEqual(
                    policy["fallbacks"],
                    {
                        "adversarial-review": ["portable-review-fallback"],
                        "adversarial-test": ["portable-test-fallback"],
                    },
                )

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

    def test_independent_review_policy_is_explicit_and_safe_by_default(self) -> None:
        self.assertIn(self.policy["independent_review"], {"strict", "degraded"})
        for expected in (
            "Missing `independent_review` in a legacy v1 policy means `strict`",
            "`degraded` explicitly authorizes a weaker route",
            "repository policy path",
        ):
            self.assertIn(expected, self.guidance)

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
        for field in ("Risk:", "Policy:", "Required gates:", "Source:"):
            self.assertIn(field, self.guidance)
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
