"""Validate ship-it's portable per-phase capability contract.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
CONTRACT_FILE: Final[Path] = SKILL_DIR / "references" / "capabilities.json"
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"
EXPECTED_PROFILES: Final[set[str]] = {"explore", "build", "review", "release"}
EXPECTED_PHASES: Final[tuple[str, ...]] = (
    "resolve",
    "explore",
    "branch",
    "implement",
    "review",
    "test",
    "pr-loop",
    "complete",
)
PROTECTED_RISKS: Final[tuple[str, ...]] = (
    "destructive",
    "credential",
    "deployment",
    "outside the workspace",
    "unknown",
)
CONDITION_FACTS: Final[set[str]] = {
    "code_changed",
    "create_issue",
    "github_issue_tracking",
    "github_source",
    "inspect_remote_work",
    "jira_source",
    "owns_cleanup",
    "release_gates_passed",
    "sail",
}


class ShipItCapabilityContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract: dict[str, Any] = json.loads(
            CONTRACT_FILE.read_text(encoding="utf-8")
        )

    def test_contract_has_stable_profiles_and_phase_order(self) -> None:
        self.assertEqual(
            self.contract["schema_version"], "sai.ship-it.capabilities/v1"
        )
        self.assertEqual(set(self.contract["profiles"]), EXPECTED_PROFILES)
        self.assertEqual(
            tuple(phase["id"] for phase in self.contract["phases"]),
            EXPECTED_PHASES,
        )

    def test_phase_requirements_fit_selected_profile(self) -> None:
        profiles = self.contract["profiles"]
        for phase in self.contract["phases"]:
            with self.subTest(phase=phase["id"]):
                selected_profiles = {phase["profile"]} | {
                    override["profile"]
                    for override in phase.get("profile_overrides", ())
                }
                allowed = {
                    capability
                    for profile in selected_profiles
                    for capability in profiles[profile]["allows"]
                }
                self.assertTrue(phase["requirements"])
                self.assertIn("side_effects", phase)
                for requirement in phase["requirements"]:
                    declared = set(requirement.get("all_of", ())) | set(
                        requirement.get("any_of", ())
                    )
                    self.assertTrue(
                        declared <= allowed,
                        f"{phase['id']} requires capabilities outside "
                        f"{phase['profile']}: {sorted(declared - allowed)}",
                    )

    def test_conditions_are_machine_readable(self) -> None:
        def assert_condition(condition: dict[str, Any]) -> None:
            if "all" in condition:
                self.assertGreaterEqual(len(condition["all"]), 2)
                for child in condition["all"]:
                    assert_condition(child)
                return
            self.assertEqual(set(condition), {"fact", "equals"})
            self.assertIn(condition["fact"], CONDITION_FACTS)
            self.assertIsInstance(condition["equals"], bool)

        for phase in self.contract["phases"]:
            entries = [*phase["requirements"], *phase.get("profile_overrides", ())]
            for entry in entries:
                if "when" in entry:
                    with self.subTest(phase=phase["id"], entry=entry):
                        assert_condition(entry["when"])

    def test_preflight_failure_is_structured_and_before_side_effects(self) -> None:
        failure = self.contract["failure"]
        self.assertEqual(failure["status"], "NEEDS_CAPABILITY")
        self.assertIn("before", failure["preflight"])
        self.assertEqual(
            set(failure["report_fields"]),
            {
                "phase",
                "profile",
                "missing_requirement",
                "attempted_fallbacks",
                "required_user_action",
            },
        )

    def test_side_effecting_phases_require_their_write_capabilities(self) -> None:
        phases = {phase["id"]: phase for phase in self.contract["phases"]}

        def required(phase: str) -> set[str]:
            return {
                capability
                for requirement in phases[phase]["requirements"]
                for capability in requirement.get("all_of", ())
            }

        self.assertIn("filesystem.write", required("branch"))
        self.assertIn("state.write", required("review"))
        self.assertIn("filesystem.transient-write", required("test"))

    def test_high_risk_actions_remain_interactive(self) -> None:
        interactive = " ".join(
            self.contract["protected_actions"]["always_interactive"]
        ).lower()
        for risk in PROTECTED_RISKS:
            with self.subTest(risk=risk):
                self.assertIn(risk, interactive)

    def test_skill_progressively_loads_capability_guidance(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        links = (
            "[references/capabilities.md](references/capabilities.md)",
            "[references/capabilities.json](references/capabilities.json)",
        )
        for link in links:
            with self.subTest(link=link):
                self.assertEqual(skill.count(link), 1)
        self.assertNotIn(CONTRACT_FILE.read_text(encoding="utf-8"), skill)


if __name__ == "__main__":
    unittest.main()
