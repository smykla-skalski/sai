"""Validate ship-it's repository release-policy contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
POLICY_FILE: Final[Path] = SKILL_DIR / "references" / "release-policy.json"
RELEASE_REFERENCE: Final[Path] = SKILL_DIR / "references" / "release.md"
CHECKPOINT_REFERENCE: Final[Path] = SKILL_DIR / "references" / "checkpoint.md"
PR_LOOP_REFERENCE: Final[Path] = SKILL_DIR / "references" / "pr-loop.md"
COMPLETION_REFERENCE: Final[Path] = SKILL_DIR / "references" / "completion.md"
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"


class ShipItReleasePolicyContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy: dict[str, Any] = json.loads(
            POLICY_FILE.read_text(encoding="utf-8")
        )
        self.guidance = RELEASE_REFERENCE.read_text(encoding="utf-8")

    def test_default_is_conservative_without_forcing_a_reviewer(self) -> None:
        self.assertEqual(
            self.policy,
            {
                "schema_version": "sai.ship-it.release-policy/v1",
                "required_reviewers": [],
                "required_checks": [],
                "merge": {
                    "method": "github",
                    "strategy": "squash",
                    "bot_comment": None,
                },
                "issue_closure": "pull-request-keyword",
                "branch_cleanup": "delete",
            },
        )
        for expected in (
            "honor all GitHub-required approvals and checks",
            "request no reviewer that the repository did not name",
            "supports repositories with no hosted reviewer",
            "never bypassing configured controls",
        ):
            self.assertIn(expected, self.guidance)
        self.assertIn("legacy `copilot-review` normalization", self.guidance)
        self.assertIn("resume never depends on remembering", self.guidance)
        self.assertIn('"fromMechanism":"copilot-review"', self.guidance)
        self.assertIn("allow at most one entry", self.guidance)
        self.assertIn("reject it unless", self.guidance)

    def test_policy_resolves_all_release_dimensions(self) -> None:
        example = self.guidance.split("```json\n", 1)[1].split("\n```", 1)[0]
        policy = json.loads(example)
        self.assertEqual(policy["schema_version"], "sai.ship-it.release-policy/v1")
        self.assertTrue(policy["required_reviewers"])
        self.assertEqual(policy["required_checks"], ["test", "lint"])
        self.assertEqual(policy["merge"]["method"], "bot-comment")
        self.assertEqual(policy["issue_closure"], "pull-request-keyword")
        self.assertEqual(policy["branch_cleanup"], "delete")

    def test_partial_policy_inherits_omitted_fields(self) -> None:
        for expected in (
            "Only `schema_version` is required.",
            "At least one other top-level field must be present",
            "omitted fields inherit from the next source",
            "A present `merge` object has all three merge fields.",
            "validate the complete normalized result",
        ):
            self.assertIn(expected, self.guidance)

    def test_reviewer_kinds_are_harness_independent(self) -> None:
        for expected in (
            "`kind` is `human|automated`",
            "`requirement` is `review|approval`",
            "`request` is `reviewer|team-reviewer|automatic`",
            "`request_target` is the exact GitHub login or team slug",
            "names Copilot, another automated reviewer, a person or a team",
            "`no hosted review required` becomes an empty list",
            "does not mean Copilot",
        ):
            self.assertIn(expected, self.guidance)

    def test_platform_controls_are_additive_and_reconciled(self) -> None:
        for expected in (
            "always additive and cannot be weakened",
            "all rulesets applying to the default branch",
            "branch protection",
            "required approving-review count",
            "A submitted approval can satisfy at most one synthetic entry.",
            "exact PR head",
            "never assume the request target and review author use the same login",
            "current member verified through the GitHub team-membership API",
            "protected-branch review decision counts that approval",
        ):
            self.assertIn(expected, self.guidance)

    def test_pr_state_is_reconciled_only_after_pr_creation(self) -> None:
        for expected in (
            "Before opening a PR, read repository-level policy",
            "After the PR exists",
            "PR-specific state never blocks initial policy resolution or PR creation",
            "Set `resolvedAt` after successful repository-level reconciliation",
        ):
            self.assertIn(expected, self.guidance)

    def test_release_requirements_are_gate_floors(self) -> None:
        for expected in (
            "Release requirements are gate floors.",
            "Add `hosted-review`",
            "add `ci`",
            "cannot remove a repository release requirement",
            "final union in `risk.requiredGates`",
        ):
            self.assertIn(expected, self.guidance)

    def test_bot_and_protected_branch_flows_do_not_bypass_controls(self) -> None:
        for expected in (
            "Treat the comment as inert text",
            "never call `gh pr merge` as a fallback",
            "Protected-branch and merge-queue requirements remain authoritative.",
            "instead of using admin or force options",
            "explicitly binds that exact comment to the same strategy",
            "reject an opaque or mismatched command",
            "verify the merge commit topology and resulting tree",
            "never rewrite merged history",
        ):
            self.assertIn(expected, self.guidance)

    def test_checkpoint_stores_normalized_release_policy(self) -> None:
        checkpoint = CHECKPOINT_REFERENCE.read_text(encoding="utf-8")
        self.assertIn('"releasePolicy": null', checkpoint)
        self.assertIn("may also lack `releasePolicy`", checkpoint)
        self.assertIn("terminal single-change outcome may lack `branchCleanup`", checkpoint)
        self.assertIn("add `branchCleanup: not-applicable`", checkpoint)
        self.assertIn("without inventing cleanup", checkpoint)
        for expected in (
            '"requiredReviewers"',
            '"requiredChecks"',
            '"issueClosure"',
            '"branchCleanup"',
            '"activatedFallbacks"',
            '"resolvedAt"',
        ):
            self.assertIn(expected, self.guidance)

    def test_skill_and_lifecycle_use_resolved_policy(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        pr_loop = PR_LOOP_REFERENCE.read_text(encoding="utf-8")
        completion = COMPLETION_REFERENCE.read_text(encoding="utf-8")
        self.assertEqual(skill.count("[references/release.md](references/release.md)"), 1)
        self.assertIn("resolved release policy from the checkpoint", pr_loop)
        self.assertIn("Do not request Copilot unless", pr_loop)
        self.assertIn("resolved issue-closing behavior", completion)
        self.assertIn("branch cleanup are verified", completion)
        self.assertIn("emit `Closes` only for `pull-request-keyword`", self.guidance)
        self.assertIn("non-closing `Refs #<number>`", pr_loop)

    def test_ambiguity_names_an_exact_human_action(self) -> None:
        for expected in (
            "Block the checkpoint with one exact action",
            "Ask @release-engineering to approve PR <url>",
            "name the exact actor or check plus the human action needed",
        ):
            self.assertIn(expected, self.guidance)

    def test_pending_release_requirements_have_a_deadline(self) -> None:
        pr_loop = PR_LOOP_REFERENCE.read_text(encoding="utf-8")
        for content in (self.guidance, pr_loop):
            self.assertIn("remains unsatisfied", content)
            self.assertIn("continuously requested", content)
            self.assertIn("pending", content)
            self.assertIn("30 minutes", content)


if __name__ == "__main__":
    unittest.main()
