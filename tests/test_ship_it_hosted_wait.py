"""Behavior checks for the blocking hosted waiter.

Copyright 2026 Smykla Skalski, MIT License.
"""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins/ship-it/skills/ship-it/scripts/hosted_wait.py"
)
sys.path.insert(0, str(PATH.parent))
spec = importlib.util.spec_from_file_location("hosted_wait", PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
HEAD = "a" * 40


def ruleset() -> tuple[list[dict], dict]:
    detail = {
        "databaseId": 123,
        "enforcement": "ACTIVE",
        "target": "BRANCH",
        "updatedAt": "2026-10-16T00:00:00Z",
        "bypassActors": {
            "nodes": [
                {
                    "bypassMode": "EXEMPT",
                    "actor": {
                        "__typename": "App",
                        "databaseId": 1197525,
                    },
                }
            ],
            "pageInfo": {"hasNextPage": False},
        },
    }
    return [{"type": "PULL_REQUEST"}], detail


def read_exemption(
    applicable: list[dict],
    detail: dict,
    *,
    integration: int | None = 1197525,
    protection: dict | None = None,
) -> dict:
    pr = {
        "headRefOid": HEAD,
        "baseRefName": "release/stable",
        "state": "OPEN",
        "merged": False,
        "reviewDecision": "REVIEW_REQUIRED",
        "baseRef": {
            "branchProtectionRule": protection,
            "rules": {
                "nodes": [{"repositoryRuleset": detail, **r} for r in applicable],
                "pageInfo": {"hasNextPage": False},
            },
        },
        "commits": {"nodes": [{"commit": {"statusCheckRollup": None}}]},
        "reviews": {"nodes": [], "pageInfo": {"hasNextPage": False}},
        "reviewThreads": {"nodes": [], "pageInfo": {"hasNextPage": False}},
    }
    completed = module.subprocess.CompletedProcess(
        [],
        0,
        json.dumps({"data": {"repository": {"pullRequest": pr}}}),
        "",
    )
    forge = module.GitHub("owner/repo", 1, float("inf"), merge_integration=integration)
    with patch.object(module.subprocess, "run", return_value=completed):
        return forge.read()


def snapshot(**changes: object) -> dict:
    result = {
        "head": HEAD,
        "state": "OPEN",
        "merged": False,
        "reviewDecision": None,
        "threads": [],
        "checks": [],
        "statuses": [],
        "reviews": [],
        "required": [],
    }
    result.update(changes)
    return result


class WaitTests(unittest.TestCase):
    def evaluate(
        self, state: dict, checks: tuple | list = (), reviewers: dict | None = None
    ) -> dict:
        return module.evaluate(state, HEAD, list(checks), reviewers or {}, [])

    def test_missing_check_never_passes(self) -> None:
        result = self.evaluate(snapshot(), ["build"])
        self.assertEqual(result["pending"], ["check:build:missing"])

    def test_explicit_live_same_app_exemption_satisfies_platform_approval(self) -> None:
        applicable, detail = ruleset()

        state = read_exemption(applicable, detail)

        self.assertEqual(self.evaluate(state)["status"], "satisfied")

    def test_absent_ambiguous_stale_and_different_actor_exemptions_block(self) -> None:
        applicable, detail = ruleset()
        cases = [
            ("no resolved actor", {"integration": None}),
            ("different actor", {"integration": 2740}),
            ("no applicable rule", {"applicable": []}),
            ("classic approval", {"protection": {"requiresApprovingReviews": True}}),
        ]
        for name, changes in cases:
            with self.subTest(name=name):
                arguments = {"applicable": applicable, "detail": detail, **changes}

                state = read_exemption(**arguments)

                self.assertEqual(
                    self.evaluate(state)["pending"], ["platform:review-required"]
                )

    def test_non_exempt_or_stale_ruleset_details_block(self) -> None:
        applicable, detail = ruleset()
        cases = [
            (
                "no actor",
                {"bypassActors": {"nodes": [], "pageInfo": {"hasNextPage": False}}},
            ),
            (
                "admin",
                {
                    "bypassActors": {
                        "nodes": [{"bypassMode": "EXEMPT", "actor": None}],
                        "pageInfo": {"hasNextPage": False},
                    },
                },
            ),
            (
                "ordinary bypass",
                {
                    "bypassActors": {
                        "nodes": [
                            {
                                "bypassMode": "ALWAYS",
                                "actor": {"__typename": "App", "databaseId": 1197525},
                            }
                        ],
                        "pageInfo": {"hasNextPage": False},
                    },
                },
            ),
            ("missing ruleset", {"databaseId": None}),
            ("inactive", {"enforcement": "EVALUATE"}),
            ("wrong target", {"target": "TAG"}),
            ("missing freshness", {"updatedAt": None}),
            (
                "incomplete actors",
                {"bypassActors": {"nodes": [], "pageInfo": {"hasNextPage": True}}},
            ),
        ]
        for name, changes in cases:
            with self.subTest(name=name):
                state = read_exemption(applicable, {**detail, **changes})

                self.assertEqual(
                    self.evaluate(state)["pending"], ["platform:review-required"]
                )

    def test_one_non_exempt_applicable_ruleset_keeps_approval_blocking(self) -> None:
        applicable, detail = ruleset()
        other = copy.deepcopy(applicable[0])
        other["repositoryRuleset"] = {**detail, "databaseId": 456, "bypassActors": None}

        state = read_exemption([*applicable, other], detail)

        self.assertEqual(self.evaluate(state)["pending"], ["platform:review-required"])

    def test_exempt_actor_does_not_waive_other_release_requirements(self) -> None:
        cases = [
            (
                "required check",
                {"required": [{"name": "ci", "bucket": "fail"}]},
                {},
                "failed",
            ),
            ("named reviewer", {}, {"alice": "approval"}, "pending"),
            (
                "changes requested",
                {"reviewDecision": "CHANGES_REQUESTED"},
                {},
                "failed",
            ),
            (
                "thread",
                {
                    "threads": [
                        {
                            "id": "T1",
                            "isResolved": False,
                            "isOutdated": False,
                            "comments": {"nodes": []},
                        }
                    ]
                },
                {},
                "pending",
            ),
        ]
        for name, changes, reviewers, expected in cases:
            with self.subTest(name=name):
                state = snapshot(
                    reviewDecision="REVIEW_REQUIRED", mergeActorReviewExempt=True
                )
                state.update(changes)

                result = self.evaluate(state, reviewers=reviewers)

                self.assertEqual(result["status"], expected)

    def test_comment_does_not_erase_changes_requested_for_exempt_actor(self) -> None:
        state = snapshot(
            reviewDecision="REVIEW_REQUIRED",
            mergeActorReviewExempt=True,
            reviews=[
                {"id": 1, "user": {"login": "alice"}, "state": "CHANGES_REQUESTED"},
                {"id": 2, "user": {"login": "alice"}, "state": "COMMENTED"},
            ],
        )

        self.assertEqual(self.evaluate(state)["failed"], ["platform:changes-requested"])

    def test_api_errors_cannot_establish_exemption(self) -> None:
        forge = module.GitHub("owner/repo", 1, float("inf"), merge_integration=1197525)
        response = module.subprocess.CompletedProcess(
            [], 0, '{"errors":[{"message":"denied"}]}', ""
        )

        with (
            patch.object(module.subprocess, "run", return_value=response),
            self.assertRaises(module.ForgeError),
        ):
            forge.read()

    def test_failed_cancelled_and_pending_platform_checks(self) -> None:
        for bucket in ["fail", "cancel", "pending"]:
            result = self.evaluate(
                snapshot(required=[{"name": "build", "bucket": bucket}])
            )
            self.assertEqual(
                result["status"], "pending" if bucket == "pending" else "failed"
            )
            self.assertIn("build", str(result))

    def test_check_rerun_uses_latest_attempt(self) -> None:
        checks = [
            {
                "id": 1,
                "suite": "s1",
                "name": "build",
                "status": "completed",
                "conclusion": "failure",
            },
            {
                "id": 2,
                "suite": "s1",
                "name": "build",
                "status": "completed",
                "conclusion": "success",
            },
        ]
        self.assertEqual(
            self.evaluate(snapshot(checks=checks), ["build"])["status"], "satisfied"
        )

    def test_required_review_and_threads_bind(self) -> None:
        reviews = [{"id": 1, "user": {"login": "alice"}, "state": "APPROVED"}]
        state = snapshot(
            reviews=reviews,
            threads=[
                {
                    "id": "T1",
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {"nodes": [{"author": {"login": "alice"}}]},
                }
            ],
        )
        self.assertEqual(
            self.evaluate(state, reviewers={"alice": "approval"})["pending"],
            ["thread:T1"],
        )
        state["threads"][0]["isOutdated"] = True
        self.assertEqual(
            self.evaluate(state, reviewers={"Alice": "approval"})["status"], "satisfied"
        )

    def test_comment_does_not_revoke_approval(self) -> None:
        reviews = [
            {"id": 1, "user": {"login": "alice"}, "state": "APPROVED"},
            {"id": 2, "user": {"login": "alice"}, "state": "COMMENTED"},
        ]
        self.assertEqual(
            self.evaluate(snapshot(reviews=reviews), reviewers={"alice": "approval"})[
                "status"
            ],
            "satisfied",
        )

    def test_head_change_cannot_pass(self) -> None:
        self.assertEqual(
            self.evaluate(snapshot(head="b" * 40))["status"], "head-changed"
        )

    def test_wait_returns_once_after_requirement_changes(self) -> None:
        forge = unittest.mock.Mock(deadline=100)
        forge.read.side_effect = [
            snapshot(required=[{"name": "ci", "bucket": "pending"}]),
            snapshot(),
        ]
        with (
            patch.object(module.time, "monotonic", return_value=1),
            patch.object(module.time, "sleep") as sleep,
        ):
            result = module.wait(forge, HEAD, ([], {}, []), interval=5)
        self.assertEqual(result["status"], "satisfied")
        self.assertEqual(result["changed"], ["check:ci:pending"])
        sleep.assert_called_once_with(5)

    def test_deadline_preserves_pending_requirement(self) -> None:
        forge = unittest.mock.Mock(deadline=1)
        forge.read.return_value = snapshot(reviewDecision="REVIEW_REQUIRED")
        with patch.object(module.time, "monotonic", return_value=2):
            result = module.wait(forge, HEAD, ([], {}, []))
        self.assertEqual(result["status"], "deadline")
        self.assertEqual(result["pending"], ["platform:review-required"])

    def test_check_failure_returns_without_sleep(self) -> None:
        forge = unittest.mock.Mock(deadline=100)
        forge.read.return_value = snapshot(
            required=[{"name": "ci", "bucket": "cancel"}]
        )
        with patch.object(module.time, "sleep") as sleep:
            result = module.wait(forge, HEAD, ([], {}, []))
        self.assertEqual(result["status"], "failed")
        sleep.assert_not_called()

    def test_independent_same_name_failure_survives_normalization(self) -> None:
        pr = {
            "headRefOid": HEAD,
            "state": "OPEN",
            "merged": False,
            "reviewDecision": None,
            "baseRef": None,
        }
        items = [
            {
                "__typename": "CheckRun",
                "databaseId": 1,
                "name": "build",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "isRequired": True,
                "checkSuite": {"id": "required-suite"},
            },
            {
                "__typename": "CheckRun",
                "databaseId": 2,
                "name": "build",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
                "isRequired": False,
                "checkSuite": {"id": "other-suite"},
            },
        ]
        state = module._normalize(pr, {"checks": items, "reviews": [], "threads": []})
        result = self.evaluate(state, ["build"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("check:build:fail", result["failed"])

    def test_deadline_during_gh_preserves_previous_pending(self) -> None:
        forge = module.GitHub("owner/repo", 1, 10)
        state = snapshot(required=[{"name": "build", "bucket": "pending"}])
        with (
            patch.object(forge, "read", side_effect=[state, TimeoutError]),
            patch.object(module.time, "monotonic", return_value=1),
            patch.object(module.time, "sleep"),
        ):
            result = module.wait(forge, HEAD, ([], {}, []))
        self.assertEqual(result["status"], "deadline")
        self.assertEqual(result["pending"], ["check:build:pending"])
        with (
            patch.object(
                module.subprocess,
                "run",
                side_effect=module.subprocess.TimeoutExpired("gh", 1),
            ),
            self.assertRaises(TimeoutError),
        ):
            module._gh_json({}, 1)
        with (
            patch.object(module, "_gh_json", side_effect=TimeoutError),
            patch.object(module.time, "monotonic", side_effect=[9, 10]),
            self.assertRaises(TimeoutError),
        ):
            forge._request({})

    def test_review_requirement_login_is_case_insensitive(self) -> None:
        reviews = [
            {"id": 1, "user": {"login": "alice"}, "state": "APPROVED"},
            {"id": 2, "user": {"login": "alice"}, "state": "COMMENTED"},
        ]
        result = self.evaluate(
            snapshot(reviews=reviews), reviewers={"Alice": "approval"}
        )
        self.assertEqual(result["status"], "satisfied")

    def test_refusal_never_satisfies_required_copilot(self) -> None:
        state = snapshot(copilotUnserviceable=True)
        result = self.evaluate(
            state, reviewers={"copilot-pull-request-reviewer[bot]": "review"}
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("unserviceable", str(result["failed"]))
        self.assertEqual(self.evaluate(state)["status"], "satisfied")


if __name__ == "__main__":
    unittest.main()
