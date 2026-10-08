"""Validate ship-it's cross-harness convergence contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
POLICY_FILE: Final[Path] = SKILL_DIR / "references" / "convergence-policy.json"
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"


class ShipItConvergenceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy: dict[str, Any] = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        self.bounded = self.policy["modes"]["bounded"]

    def test_bounded_mode_has_one_routine_review_and_fix_pass(self) -> None:
        self.assertEqual(self.policy["default_mode"], "bounded")
        self.assertEqual(self.bounded["activation"], "default")
        self.assertEqual(self.bounded["max_elapsed_minutes"], 90)
        self.assertEqual(self.bounded["review"]["code_adversary_passes"], 1)
        self.assertEqual(self.bounded["review"]["findings_challenge_passes"], 1)
        self.assertEqual(self.bounded["review"]["max_cycles"], 2)
        self.assertEqual(self.bounded["fixes"], {"max_passes": 1, "validation": "focused-tests"})
        self.assertEqual(self.bounded["full_quality_gate_runs"], 1)

    def test_only_severity_exceptions_allow_the_second_cycle(self) -> None:
        self.assertEqual(
            set(self.bounded["review"]["rereview_triggers"]),
            {"security", "data-loss", "destructive-concurrency", "unresolved-acceptance"},
        )

        def decision(trigger: str, cycles: int, elapsed_minutes: int) -> str:
            if elapsed_minutes >= self.bounded["max_elapsed_minutes"]:
                return "stop"
            if trigger not in self.bounded["review"]["rereview_triggers"]:
                return self.bounded["later_non_blocking_findings"]
            if cycles >= self.bounded["review"]["max_cycles"]:
                return "stop"
            return "rereview"

        self.assertEqual(decision("style", 1, 20), "follow-up-issue")
        self.assertEqual(decision("security", 1, 20), "rereview")
        self.assertEqual(decision("unresolved-acceptance", 2, 20), "stop")
        self.assertEqual(decision("security", 1, 90), "stop")

    def test_exhaustive_mode_requires_explicit_current_request(self) -> None:
        exhaustive = self.policy["modes"]["exhaustive"]
        self.assertEqual(exhaustive["activation"], "explicit-user-request")
        self.assertEqual(exhaustive["limits"], "user-directed")
        self.assertNotEqual(self.policy["default_mode"], "exhaustive")

    def test_budget_preserves_delivery_controls_and_ignores_copilot_waits(self) -> None:
        self.assertEqual(
            set(self.policy["mandatory_controls"]),
            {
                "repository-required-checks",
                "permissions",
                "signatures",
                "mandatory-human-review",
            },
        )
        self.assertFalse(self.policy["copilot"]["wait"])
        self.assertEqual(
            self.policy["copilot"]["required_policy"],
            "activate-configured-fallback-or-hard-stop",
        )
        self.assertEqual(
            set(self.policy["completion_metrics"]),
            {"merged-pull-request", "closed-issue"},
        )
        self.assertEqual(self.policy["diagnostic_metrics"], ["review-iterations"])

    def test_every_harness_consumes_one_contract(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        guidance = (SKILL_DIR / "references" / "convergence.md").read_text(encoding="utf-8")
        fallbacks = (SKILL_DIR / "references" / "fallbacks.md").read_text(encoding="utf-8")
        self.assertEqual(skill.count("[references/convergence-policy.json]"), 1)
        for harness in ("Claude Code", "Codex", "OpenCode", "Sail"):
            with self.subTest(harness=harness):
                self.assertIn(harness, guidance)
        self.assertIn("reads `convergence-policy.json` directly", fallbacks)
        self.assertIn("never widen or reset the budget", fallbacks)

    def test_all_validation_phases_share_checkpoint_counters(self) -> None:
        checkpoint = (SKILL_DIR / "references" / "checkpoint.md").read_text(encoding="utf-8")
        for field in (
            '"mode": "bounded"',
            '"startedAt": null',
            '"reviewCycles": 0',
            '"fixPasses": 0',
            '"fullQualityGateRuns": 0',
        ):
            self.assertIn(field, checkpoint)
        self.assertIn("Review, test, CI and hosted feedback update the same counters", checkpoint)


if __name__ == "__main__":
    unittest.main()
