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
REFERENCES: Final[Path] = SKILL_DIR / "references"


def reference(name: str) -> str:
    return (REFERENCES / name).read_text(encoding="utf-8")


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
        self.assertEqual(
            self.bounded["fixes"],
            {
                "max_passes": 1,
                "validation": "focused-tests",
                "verification": "diff-since-reviewed-revision-against-findings",
            },
        )
        self.assertEqual(self.bounded["full_quality_gate_runs"], 1)

    def test_only_severity_exceptions_allow_the_second_cycle(self) -> None:
        review = self.bounded["review"]
        blockers = set(self.bounded["delivery_blockers"])
        self.assertEqual(
            set(review["rereview_triggers"]),
            {"security", "data-loss", "destructive-concurrency"},
        )
        self.assertNotIn("unresolved-acceptance", review["rereview_triggers"])
        self.assertIn("unresolved-acceptance", blockers)
        self.assertEqual(self.bounded["cycle_limit_counters"], ["reviewCycles", "elapsed"])
        self.assertEqual(self.bounded["fix_limit_counters"], ["fixPasses"])

        def decision(finding: str, *, cycles: int, fix_passes: int, elapsed: int) -> str:
            exhausted = {
                "reviewCycles": cycles >= review["max_cycles"],
                "elapsed": elapsed >= self.bounded["max_elapsed_minutes"],
                "fixPasses": fix_passes >= self.bounded["fixes"]["max_passes"],
            }
            if not any(exhausted[name] for name in self.bounded["fix_limit_counters"]):
                return "fix"
            cycle_limit = any(exhausted[name] for name in self.bounded["cycle_limit_counters"])
            if finding in review["rereview_triggers"] and not cycle_limit:
                return "rereview"
            if finding in blockers or f"{finding}-defect" in blockers:
                return "stop"
            return self.bounded["later_non_blocking_findings"]

        self.assertEqual(decision("style", cycles=1, fix_passes=0, elapsed=20), "fix")
        self.assertEqual(decision("style", cycles=1, fix_passes=1, elapsed=20), "follow-up-issue")
        self.assertEqual(decision("style", cycles=2, fix_passes=1, elapsed=95), "follow-up-issue")
        self.assertEqual(decision("security", cycles=1, fix_passes=1, elapsed=20), "rereview")
        self.assertEqual(decision("security", cycles=2, fix_passes=1, elapsed=20), "stop")
        self.assertEqual(decision("security", cycles=1, fix_passes=1, elapsed=90), "stop")
        self.assertEqual(
            decision("unresolved-acceptance", cycles=1, fix_passes=1, elapsed=20), "stop"
        )
        self.assertEqual(
            decision("repository-required-check", cycles=1, fix_passes=1, elapsed=20), "stop"
        )

        convergence = reference("convergence.md")
        self.assertIn(
            "When `reviewCycles` equals `max_cycles` or the elapsed budget is spent, "
            "start no further review cycle.",
            convergence,
        )
        self.assertIn("When `fixPasses` equals `max_passes`, start no further fix pass.", convergence)
        self.assertIn("The cycle limit does not depend on `fixPasses`", convergence)
        self.assertIn(
            "Reaching the cycle or elapsed limit starts no further cycle; "
            "reaching the fix-pass limit starts no further fix pass.",
            reference("review.md"),
        )

    def test_clean_verdict_ends_the_gate_without_a_findings_challenge(self) -> None:
        self.assertEqual(
            self.bounded["review"]["findings_challenge_when"],
            "blocking-or-issue-finding",
        )
        review = reference("review.md")
        self.assertIn("never dispatch the Findings Adversary for a CLEAN result", review)
        self.assertIn(
            "dispatches the Findings Adversary only after a `blocking:` or `issue:` finding",
            review,
        )
        self.assertIn(
            "never send a CLEAN result to the Findings Adversary", reference("convergence.md")
        )

    def test_fix_pass_is_verified_from_the_diff_since_the_reviewed_revision(self) -> None:
        review = reference("review.md")
        self.assertIn("`git diff <reviewedRevision>..HEAD`", review)
        self.assertIn("Dispatch no Code Adversary and no Findings Adversary", review)
        self.assertIn("only while `reviewCycles` is below `max_cycles`", review)
        self.assertIn(
            "an unresolved acceptance criterion blocks delivery", reference("evidence.md")
        )
        self.assertIn("never starts another review cycle", reference("test.md"))

    def test_default_branch_merge_with_unchanged_reviewed_files_needs_no_review(self) -> None:
        self.assertEqual(
            self.bounded["review"]["default_branch_merge"],
            "no-review-when-reviewed-files-unchanged",
        )
        convergence = reference("convergence.md")
        self.assertIn("git diff --quiet HEAD^1 HEAD -- <branch files>", convergence)
        self.assertIn("including files the fix pass added", convergence)
        self.assertIn("triggers no review", convergence)
        self.assertIn("naming the first-parent comparison", reference("evidence.md"))
        self.assertIn(
            "leaves the reviewed files unchanged triggers no review", reference("pr-loop.md")
        )

    def test_reaching_the_limit_delivers_with_follow_up_issues_unless_blocked(self) -> None:
        self.assertEqual(self.bounded["at_limit"], "follow-up-issues-then-deliver")
        self.assertEqual(
            set(self.bounded["delivery_blockers"]),
            {
                "security-defect",
                "data-loss",
                "destructive-concurrency",
                "unresolved-acceptance",
                "repository-required-check",
                "mandatory-human-review",
            },
        )
        convergence = reference("convergence.md")
        self.assertIn("## Reaching the limit", convergence)
        self.assertIn("Once no fix pass remains, classify every finding still `open`", convergence)
        self.assertIn("Never defer a delivery blocker to a follow-up issue", convergence)
        self.assertIn(
            "re-attest the review evidence for the current revision from the follow-up list",
            convergence,
        )
        self.assertIn("leaves no failed evidence", reference("review.md"))
        self.assertIn(
            "after every remaining finding has become a follow-up issue under the limit rule",
            reference("evidence.md"),
        )
        self.assertIn(
            "a delivery blocker survives the convergence budget",
            SKILL_FILE.read_text(encoding="utf-8"),
        )

    def test_exhaustive_mode_requires_explicit_current_request(self) -> None:
        exhaustive = self.policy["modes"]["exhaustive"]
        self.assertEqual(exhaustive["activation"], "explicit-user-request")
        self.assertEqual(exhaustive["limits"], "user-directed")
        self.assertNotEqual(self.policy["default_mode"], "exhaustive")
        self.assertEqual(exhaustive["authorization"]["accepted"], ["user-current-request"])
        self.assertLessEqual(
            {"coordinator", "worker-rules", "spawn-prompt", "compaction-summary"},
            set(exhaustive["authorization"]["rejected"]),
        )
        convergence = reference("convergence.md")
        for source in ("coordinator", "worker-rules file", "compaction summary"):
            with self.subTest(source=source):
                self.assertIn(source, convergence)
        self.assertIn(
            "The coordinator never authorizes another review cycle or fix pass",
            reference("orchestration.md"),
        )

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
            '"reviewedRevision": null',
            '"findings": []',
        ):
            self.assertIn(field, checkpoint)
        self.assertIn("Review, test, CI and hosted feedback update the same counters", checkpoint)
        self.assertIn("gets `reviewedRevision: null` and `findings: []`", checkpoint)
        self.assertIn("`fixPasses` counts fix passes spent before their first edit", checkpoint)
        convergence = reference("convergence.md")
        self.assertIn("`reviewCycles` | A Code Adversary is dispatched", convergence)
        self.assertIn("`fixPasses` | A fix pass starts, before its first edit", convergence)
        self.assertIn(
            "Spend a review cycle or fix pass in the checkpoint before it starts", convergence
        )
        self.assertIn(
            "increment and persist `fixPasses` before the first edit", reference("review.md")
        )


if __name__ == "__main__":
    unittest.main()
