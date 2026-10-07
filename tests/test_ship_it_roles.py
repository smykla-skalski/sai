"""Validate ship-it's portable role-routing contract."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Final


ROOT: Final[Path] = Path(__file__).resolve().parent.parent
SKILL_DIR: Final[Path] = ROOT / "plugins" / "ship-it" / "skills" / "ship-it"
ROLE_IDS: Final[set[str]] = {
    "exploration",
    "implementation",
    "review",
    "testing",
    "ci-triage",
}
SELECTOR_FIELDS: Final[list[str]] = ["provider", "model", "variant"]


class ShipItRolesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads((SKILL_DIR / "references" / "roles.json").read_text())
        self.guidance = (SKILL_DIR / "references" / "roles.md").read_text()
        self.evidence = (SKILL_DIR / "references" / "evidence.md").read_text()

    def test_contract_defines_every_portable_role(self) -> None:
        self.assertEqual(
            {role["id"] for role in self.contract["roles"]},
            ROLE_IDS,
        )
        self.assertEqual(
            self.contract["route_record"]["selector_fields"],
            SELECTOR_FIELDS,
        )

    def test_every_harness_has_a_portable_adapter(self) -> None:
        self.assertEqual(
            set(self.contract["adapters"]),
            {"claude-code", "codex", "opencode", "copilot-cli", "sail"},
        )
        self.assertIsNone(self.contract["adapters"]["sail"]["fallback"])
        for adapter in self.contract["adapters"].values():
            self.assertTrue(adapter["subagents"])
            self.assertEqual(set(adapter["selectors"]), set(SELECTOR_FIELDS))
            self.assertEqual(
                adapter["unsupported_selector"], "reject-before-dispatch"
            )

    def test_adapter_maps_each_harness_selector_control(self) -> None:
        adapters = self.contract["adapters"]
        self.assertEqual(adapters["codex"]["selectors"]["model"], "spawn-agent-model")
        self.assertEqual(
            adapters["codex"]["selectors"]["variant"],
            "spawn-agent-reasoning-effort",
        )
        self.assertEqual(adapters["sail"]["selectors"]["provider"], "worker-provider")
        self.assertIn("Never silently ignore", self.guidance)
        self.assertIn("block with the exact unsupported selector", self.guidance)

    def test_portable_fallback_order_is_deterministic(self) -> None:
        skill_position = self.guidance.index("An installed skill")
        generic_position = self.guidance.index("A fresh generic subagent")
        self.assertLess(skill_position, generic_position)
        capabilities = (SKILL_DIR / "references" / "capabilities.md").read_text()
        self.assertLess(
            capabilities.index("adversarial-review skill"),
            capabilities.index("fresh generic subagent"),
        )

    def test_strict_review_rejects_every_unsafe_route(self) -> None:
        self.assertEqual(self.contract["independent_review"]["default"], "strict")
        self.assertEqual(
            set(self.contract["independent_review"]["strict_rejections"]),
            {
                "same-provider-and-model-as-implementation",
                "unresolved-model-alias",
                "implementation-execution-reuse",
                "inline-execution",
            },
        )
        for phrase in (
            "Actual provider and model equal",
            "modelResolution` is `unresolved",
            "executionId` equals the implementation execution ID",
            "mechanism` is `inline",
        ):
            self.assertIn(phrase, self.guidance)

        review = (SKILL_DIR / "references" / "review.md").read_text()
        capabilities = (SKILL_DIR / "references" / "capabilities.md").read_text()
        fallbacks = (SKILL_DIR / "references" / "fallbacks.md").read_text()
        self.assertIn("block under strict independence", review)
        self.assertIn("fell back inline", review)
        self.assertIn("Strict independence blocks", capabilities)
        self.assertIn("does not authorize a role route", capabilities)
        self.assertIn("Strict review blocks without a subagent", fallbacks)
        for content in (review, capabilities, fallbacks):
            self.assertIn("degraded", content)

    def test_degraded_routes_remain_visible(self) -> None:
        requirements = set(
            self.contract["independent_review"]["degraded_mode_requires"]
        )
        self.assertEqual(
            requirements,
            {
                "explicit-policy-authorization",
                "degraded-independence-value",
                "non-empty-degradation-reasons",
            },
        )
        self.assertIn("independence: degraded", self.guidance)
        self.assertIn("non-empty `degradationReasons`", self.evidence)

    def test_evidence_example_records_requested_and_actual_selectors(self) -> None:
        example_match = re.search(
            r"```json\n(?P<document>.*?)\n```", self.evidence, re.DOTALL
        )
        self.assertIsNotNone(example_match)
        example = json.loads(example_match["document"])
        route = example["roleRoutes"][0]
        self.assertEqual(route["sourceRevision"], example["revision"])
        self.assertEqual(set(route["requested"]), set(SELECTOR_FIELDS))
        self.assertEqual(set(route["actual"]), set(SELECTOR_FIELDS))
        for field in self.contract["route_record"]["required_fields"]:
                self.assertIn(field, route)

    def test_revision_rollover_preserves_only_active_build_routes(self) -> None:
        for expected in (
            "Bind pre-commit exploration and implementation routes",
            "Never carry a review, testing or CI-triage route forward",
        ):
            self.assertIn(expected, self.guidance)
        for expected in (
            "Carry still-active exploration and implementation routes",
            "Drop old review, testing and CI-triage routes",
        ):
            self.assertIn(expected, self.evidence)

    def test_execution_phases_record_their_routes(self) -> None:
        expected = {
            "explore.md": "exploration role",
            "implementation.md": "implementation role",
            "review.md": "review invocation",
            "test.md": "testing role",
            "pr-loop.md": "ci-triage role",
        }
        for reference, phrase in expected.items():
            with self.subTest(reference=reference):
                content = (SKILL_DIR / "references" / reference).read_text().lower()
                self.assertIn(phrase, content)
                self.assertIn("record", content)

    def test_contract_contains_no_commercial_model_pin(self) -> None:
        serialized = json.dumps(self.contract).lower()
        guidance = self.guidance.lower()
        commercial_pin = re.compile(
            r"(?:claude-(?:opus|sonnet|haiku)-\d|gpt-\d|gemini-\d)"
        )
        self.assertIsNone(commercial_pin.search(serialized))
        self.assertIsNone(commercial_pin.search(guidance))


if __name__ == "__main__":
    unittest.main()
