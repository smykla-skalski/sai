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
        dispatch = {role["id"]: role["dispatch"] for role in self.contract["roles"]}
        self.assertEqual(dispatch["exploration"], "current-execution")
        self.assertEqual(dispatch["implementation"], "current-execution")
        self.assertEqual(dispatch["review"], "routed-worker")

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
        self.assertIn("Rejected candidates never enter `roleRoutes`", self.guidance)

    def test_unknown_actual_selectors_are_explicit_nulls(self) -> None:
        self.assertIn("JSON `null`", self.guidance)
        self.assertIn("Any null actual selector requires", self.guidance)

    def test_rejected_routes_are_non_gating_diagnostics(self) -> None:
        diagnostics = self.contract["route_diagnostic"]
        self.assertEqual(set(diagnostics["stages"]), {"pre-dispatch", "post-dispatch"})
        self.assertIn("context-reuse", diagnostics["reasons"])
        self.assertNotIn("strict-same-model", diagnostics["reasons"])
        self.assertIn("actual", diagnostics["optional_fields"])
        self.assertIn("does not satisfy or block a gate", self.evidence)
        self.assertIn("post-dispatch diagnostics preserve", self.evidence)

    def test_skill_dispatch_requires_actual_worker_routes(self) -> None:
        review = (SKILL_DIR / "references" / "review.md").read_text()
        test = (SKILL_DIR / "references" / "test.md").read_text()
        self.assertIn("route record for every Code and Findings worker", review)
        self.assertIn("route record for every tester execution and retry", test)
        self.assertIn("With no subagent capability, block", test)
        self.assertIn("Inline testing does not satisfy this gate", test)
        capabilities = (SKILL_DIR / "references" / "capabilities.md").read_text()
        self.assertIn("fresh subagent", capabilities)
        self.assertIn("inline testing never satisfies the gate", capabilities)

    def test_portable_fallback_order_is_deterministic(self) -> None:
        skill_position = self.guidance.index("An installed skill")
        generic_position = self.guidance.index("A fresh generic subagent")
        self.assertLess(skill_position, generic_position)
        capabilities = (SKILL_DIR / "references" / "capabilities.md").read_text()
        self.assertLess(
            capabilities.index("review skill"),
            capabilities.index("fresh generic subagent"),
        )

    def test_review_and_testing_require_fresh_context_not_a_different_model(self) -> None:
        isolation = self.contract["context_isolation"]
        self.assertEqual(isolation["required_for"], ["review", "testing"])
        self.assertEqual(isolation["execution"], "fresh-subagent-per-pass-or-retry")
        self.assertFalse(isolation["model_difference_required"])
        self.assertEqual(
            set(isolation["rejections"]),
            {"execution-context-reuse", "inline-execution"},
        )
        self.assertIn("different provider or model is not required", self.guidance)
        self.assertIn("fresh subagent contexts", self.guidance)
        self.assertIn("provider and model may match implementation", self.evidence)

        review = (SKILL_DIR / "references" / "review.md").read_text()
        test = (SKILL_DIR / "references" / "test.md").read_text()
        self.assertIn("fresh subagent execution", review)
        self.assertIn("same model as implementation", test)
        self.assertNotIn("independent_review", review)
        self.assertNotIn("independent_review", test)

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
