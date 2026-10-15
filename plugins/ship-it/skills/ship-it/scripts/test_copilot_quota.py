#!/usr/bin/env python3
# Copyright 2026 Marcin Skalski
"""Behavior tests for user-global refusal memory."""

from __future__ import annotations

import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from copilot_quota import (
    classify_and_remember,
    clear_quota,
    quota_status,
    remember_quota,
)

REFUSAL = {
    "user": {"login": "copilot"},
    "state": "COMMENTED",
    "body": "Unable to review: quota exceeded.",
    "id": 1,
}


def concurrent_writer(directory: str) -> None:
    remember_quota(directory=Path(directory))


class QuotaMemoryTest(unittest.TestCase):
    def test_cross_run_expiry_clear_and_minimal_storage(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            self.assertTrue(quota_status(directory=directory)["requestAllowed"])
            with patch("copilot_quota.time.time", return_value=100):
                result = classify_and_remember(
                    [REFUSAL], max_age=10, directory=directory
                )
            self.assertFalse(result["requestAllowed"])
            state = json.loads((directory / "copilot-quota.json").read_text())
            self.assertEqual(
                state,
                {
                    "reviewer": "copilot",
                    "reason": "copilot-quota-refusal",
                    "expiresAt": 110,
                },
            )
            self.assertEqual(
                (directory / "copilot-quota.json").stat().st_mode & 0o777, 0o600
            )
            with patch("copilot_quota.time.time", return_value=109):
                self.assertFalse(quota_status(directory=directory)["requestAllowed"])
            with patch("copilot_quota.time.time", return_value=110):
                self.assertTrue(quota_status(directory=directory)["requestAllowed"])
                repeated = classify_and_remember([REFUSAL], result, directory=directory)
                self.assertIsNone(repeated["quotaMemory"])
                self.assertFalse(repeated["requestAllowed"])
            clear_quota(directory=directory)
            self.assertFalse((directory / "copilot-quota.json").exists())

    def test_active_expiry_never_extended_and_real_reviews_survive(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            with patch("copilot_quota.time.time", return_value=100):
                first = remember_quota(max_age=10, directory=directory)
            with patch("copilot_quota.time.time", return_value=105):
                self.assertEqual(
                    remember_quota(max_age=1000, directory=directory), first
                )
                real = {"user": {"login": "copilot"}, "state": "APPROVED", "body": ""}
                result = classify_and_remember([real], directory=directory)
                self.assertEqual(result["reviews"], [real])
                self.assertFalse(quota_status(directory=directory)["requestAllowed"])

    def test_concurrent_writers_leave_valid_minimal_state(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            workers = [
                multiprocessing.Process(target=concurrent_writer, args=(root,))
                for _ in range(8)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(10)
                self.assertEqual(worker.exitcode, 0)
            state = quota_status(directory=Path(root))
            self.assertFalse(state["requestAllowed"])
            self.assertEqual(
                set(state["quotaMemory"]), {"reviewer", "reason", "expiresAt"}
            )

    def test_invalid_age_and_corrupt_state_fail_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            for age in (0, -1, True):
                with self.assertRaises(ValueError):
                    remember_quota(max_age=age, directory=directory)
            path = directory / "copilot-quota.json"
            path.write_text("{broken")
            with self.assertRaises(ValueError):
                quota_status(directory=directory)
            self.assertEqual(path.read_text(), "{broken")
            clear_quota(directory=directory)
            self.assertTrue(quota_status(directory=directory)["requestAllowed"])


if __name__ == "__main__":
    unittest.main()
