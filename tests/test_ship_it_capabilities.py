"""Validate ship-it's portable per-phase capability contract.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import itertools
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
    "publish",
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
    "coordinator",
    "create_issue",
    "github_issue_tracking",
    "github_source",
    "inspect_remote_work",
    "jira_source",
    "owns_cleanup",
    "review_gate_required",
    "sail",
    "test_gate_required",
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

        def matches(condition: dict[str, Any], facts: dict[str, bool]) -> bool:
            if "all" in condition:
                return all(matches(child, facts) for child in condition["all"])
            return facts[condition["fact"]] is condition["equals"]

        for phase in self.contract["phases"]:
            self.assertTrue(phase["requirements"])
            self.assertIn("side_effects", phase)
            for values in itertools.product((False, True), repeat=len(CONDITION_FACTS)):
                facts = dict(zip(sorted(CONDITION_FACTS), values, strict=True))
                matching_overrides = {
                    override["profile"]
                    for override in phase.get("profile_overrides", ())
                    if matches(override["when"], facts)
                }
                self.assertLessEqual(
                    len(matching_overrides),
                    1,
                    f"{phase['id']} selects conflicting profile overrides",
                )
                selected_profile = next(iter(matching_overrides), phase["profile"])
                allowed = set(profiles[selected_profile]["allows"])
                for requirement in phase["requirements"]:
                    if "when" in requirement and not matches(requirement["when"], facts):
                        continue
                    declared = set(requirement.get("all_of", ())) | set(
                        requirement.get("any_of", ())
                    )
                    with self.subTest(
                        phase=phase["id"], profile=selected_profile, facts=facts
                    ):
                        self.assertTrue(
                            declared <= allowed,
                            f"{phase['id']} requires capabilities outside "
                            f"{selected_profile}: {sorted(declared - allowed)}",
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
                if "when" not in requirement
                for capability in requirement.get("all_of", ())
            }

        self.assertIn("filesystem.write", required("branch"))
        self.assertIn("state.write", required("review"))
        test_conditional = {
            capability
            for requirement in phases["test"]["requirements"]
            if requirement.get("when")
            == {"fact": "test_gate_required", "equals": True}
            for capability in requirement.get("all_of", ())
        }
        self.assertIn("filesystem.transient-write", test_conditional)
        self.assertIn("merge.execute", required("pr-loop"))
        for phase in EXPECTED_PHASES:
            with self.subTest(checkpoint_phase=phase):
                self.assertIn("state.write", required(phase))

        def conditional(phase: str, fact: str) -> set[str]:
            return {
                capability
                for requirement in phases[phase]["requirements"]
                if requirement.get("when") == {"fact": fact, "equals": True}
                for capability in requirement.get("all_of", ())
            }

        self.assertTrue(
            {
                "filesystem.write",
                "github.write",
                "issue.write",
                "subagent.worker",
                "subagent.review",
                "subagent.test",
            }
            <= conditional("resolve", "coordinator")
        )
        self.assertTrue(
            {"github.read", "issue.read", "network.read"}
            <= conditional("resolve", "create_issue")
        )
        self.assertTrue(
            {
                "github.read",
                "github.write",
                "issue.read",
                "issue.write",
                "network.read",
                "network.write",
            }
            <= conditional("resolve", "github_source")
        )
        self.assertNotIn("issue.read", required("complete"))
        self.assertTrue(
            {"github.write", "issue.read", "issue.write", "network.write"}
            <= conditional("complete", "github_issue_tracking")
        )

    def test_high_risk_actions_remain_interactive(self) -> None:
        interactive = " ".join(
            self.contract["protected_actions"]["always_interactive"]
        ).lower()
        for risk in PROTECTED_RISKS:
            with self.subTest(risk=risk):
                self.assertIn(risk, interactive)

    def test_github_phases_can_maintain_the_work_claim(self) -> None:
        phases = {phase["id"]: phase for phase in self.contract["phases"]}
        claim_capabilities = {
            "github.read",
            "github.write",
            "issue.read",
            "issue.write",
            "network.read",
            "network.write",
        }

        for phase_id in (
            "resolve",
            "explore",
            "branch",
            "implement",
            "review",
            "test",
            "pr-loop",
        ):
            with self.subTest(phase=phase_id):
                phase = phases[phase_id]
                required = {
                    capability
                    for requirement in phase["requirements"]
                    if requirement.get("when")
                    == {"fact": "github_source", "equals": True}
                    for capability in requirement.get("all_of", ())
                }
                self.assertTrue(claim_capabilities <= required)
                profile = self.contract["profiles"][phase["profile"]]
                self.assertTrue(claim_capabilities <= set(profile["allows"]))

        for phase_id in ("resolve", "explore", "branch", "implement", "review", "test"):
            with self.subTest(no_release_override=phase_id):
                phase = phases[phase_id]
                self.assertFalse(
                    any(
                        override["profile"] == "release"
                        and override.get("when")
                        == {"fact": "github_source", "equals": True}
                        for override in phase.get("profile_overrides", ())
                    )
                )

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
