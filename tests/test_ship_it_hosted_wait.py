"""Behavior checks for the blocking hosted waiter.

Copyright 2026 Smykla Skalski, MIT License.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins/ship-it/skills/ship-it/scripts/hosted_wait.py"
)
spec = importlib.util.spec_from_file_location("hosted_wait", PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
HEAD = "a" * 40


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
            {"id": 1, "name": "build", "status": "completed", "conclusion": "failure"},
            {"id": 2, "name": "build", "status": "completed", "conclusion": "success"},
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
            self.evaluate(state, reviewers={"alice": "approval"})["status"], "satisfied"
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


if __name__ == "__main__":
    unittest.main()
