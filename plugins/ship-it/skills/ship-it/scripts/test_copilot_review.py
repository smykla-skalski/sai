#!/usr/bin/env python3
# Copyright 2026 Marcin Skalski
"""Behavior tests for submitted Copilot quota refusals."""

from __future__ import annotations

import unittest

from copilot_review import classify_reviews


def review(
    body: str, *, actor: str = "copilot-pull-request-reviewer[bot]", identity: int = 1
) -> dict:
    return {
        "id": identity,
        "user": {"login": actor},
        "body": body,
        "state": "COMMENTED",
        "html_url": f"https://github.com/o/r/pull/1#pullrequestreview-{identity}",
    }


class CopilotReviewTest(unittest.TestCase):
    def test_submitted_refusals_never_satisfy_review(self) -> None:
        for body in (
            "Copilot cannot review this pull request because you have exceeded your quota.",
            "You've reached your monthly limit for Copilot code reviews.",
            "Unable to review: premium request allowance exhausted.",
            "Copilot couldn't review because the review request limit was reached.",
        ):
            with self.subTest(body=body):
                result = classify_reviews([review(body)])
                self.assertTrue(result["unserviceable"])
                self.assertFalse(result["requestAllowed"])
                self.assertEqual(result["reviews"], [])
                self.assertEqual(
                    result["refusalEvidence"][0]["reason"], "copilot-quota-refusal"
                )

    def test_real_reviews_survive_refusal_and_repeated_snapshots(self) -> None:
        refusal = review("Unable to review because the quota was exceeded.")
        real = review("Found an unchecked error.", identity=2)
        state = classify_reviews([refusal, real])
        self.assertEqual(state["reviews"], [real])
        state = classify_reviews([refusal, real], state)
        self.assertEqual(len(state["refusalEvidence"]), 1)
        state = classify_reviews([real], state)
        self.assertTrue(state["unserviceable"])
        self.assertFalse(state["requestAllowed"])
        self.assertEqual(state["reviews"], [real])

    def test_quota_code_feedback_and_other_actors_are_real_reviews(self) -> None:
        for item in (
            review("The API quota limit is exceeded here; handle the error."),
            review("The quota check cannot review the account permissions."),
            review("Unable to review because quota exceeded.", actor="human"),
            review("Unable to review because quota exceeded.", actor="copilot-spoof"),
            review(""),
        ):
            with self.subTest(item=item):
                result = classify_reviews([item])
                self.assertFalse(result["unserviceable"])
                self.assertEqual(result["reviews"], [item])

    def test_graphql_and_pending_reviews(self) -> None:
        item = {
            "id": "R1",
            "author": {"login": "Copilot"},
            "body": "You have exceeded your quota. Unable to review.",
            "state": "COMMENTED",
            "url": "https://github.com/o/r/pull/1#pullrequestreview-1",
        }
        self.assertTrue(classify_reviews([item])["unserviceable"])
        item["state"] = "PENDING"
        self.assertFalse(classify_reviews([item])["unserviceable"])


if __name__ == "__main__":
    unittest.main()
