"""Behavior tests for durable phase-boundary continuation receipts.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest

from test_ship_it_bookkeeping import SCRIPT, checkpoint_document, checkpoint_path


class HandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.document = checkpoint_document()
        self.document["workflow"].update(
            phase="review", status="active", revision="a" * 40
        )
        self.document["delivery"] = {
            "pullRequestUrl": "https://github.com/o/r/pull/1",
            "pullRequestHead": "a" * 40,
            "pullRequestState": "open",
        }
        self.path = checkpoint_path(self.directory.name, self.document)
        self.path.write_text(json.dumps(self.document))
        self.pending = {
            "id": "draft-1",
            "boundary": "draft-published",
            "status": "pending",
            "brief": f"Read {self.path}; continue review in assigned worktree.",
        }

    def invoke(self, update: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "handoff",
                "--checkpoint",
                str(self.path),
                "--handoff-json",
                json.dumps(update),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def load(self) -> dict:
        return json.loads(self.path.read_text())

    def test_restart_accepts_pending_receipt_without_changing_other_state(self) -> None:
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        pending = self.load()
        accepted = {
            "id": "draft-1",
            "boundary": "draft-published",
            "status": "accepted",
            "worker": "fresh-1",
            "inputTokens": 24999,
        }
        result = self.invoke(accepted)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = self.load()
        for key in self.document:
            if key != "updatedAt":
                self.assertEqual(after[key], pending[key], key)
        self.assertEqual(after["handoffs"][0]["status"], "accepted")
        self.assertEqual(self.invoke(accepted).returncode, 0)
        self.assertEqual(self.load()["handoffs"], after["handoffs"])

    def test_fallback_and_second_boundary_are_durable(self) -> None:
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        fallback = {
            "id": "draft-1",
            "boundary": "draft-published",
            "status": "fallback",
            "reason": "Host has no fresh-agent API",
        }
        self.assertEqual(self.invoke(fallback).returncode, 0)
        state = self.load()
        state["workflow"]["phase"] = "pr"
        self.path.write_text(json.dumps(state))
        second = {**self.pending, "id": "pr-1", "boundary": "before-pr-loop"}
        self.assertEqual(self.invoke(second).returncode, 0)
        self.assertEqual(len(self.load()["handoffs"]), 2)

    def test_invalid_startup_counts_leave_pending_state_unchanged(self) -> None:
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        before = self.path.read_bytes()
        for count in (25000, 0, -1, True, "2000", None):
            with self.subTest(count=count):
                update = {
                    **self.pending,
                    "status": "accepted",
                    "worker": "fresh",
                    "inputTokens": count,
                }
                self.assertEqual(self.invoke(update).returncode, 2)
                self.assertEqual(self.path.read_bytes(), before)

    def test_oversized_unicode_brief_is_rejected(self) -> None:
        before = self.path.read_bytes()
        result = self.invoke({**self.pending, "brief": "😀" * 500})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_rejects_duplicate_boundary_changed_revision_and_wrong_phase(self) -> None:
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        self.assertEqual(self.invoke({**self.pending, "id": "other"}).returncode, 2)
        state = self.load()
        for workflow in ({"revision": "b" * 40}, {"phase": "test"}):
            changed = copy.deepcopy(state)
            changed["workflow"].update(workflow)
            self.path.write_text(json.dumps(changed))
            self.assertEqual(self.invoke(self.pending).returncode, 2)

    def test_completed_receipt_cannot_be_reassigned(self) -> None:
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        accepted = {
            **self.pending,
            "status": "accepted",
            "worker": "first",
            "inputTokens": 1000,
        }
        self.assertEqual(self.invoke(accepted).returncode, 0)
        before = self.path.read_bytes()
        self.assertEqual(self.invoke({**accepted, "worker": "second"}).returncode, 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_claim_and_evidence_survive_both_fresh_continuations(self) -> None:
        state = self.load()
        state["bookkeeping"].update(claims=True, evidence=True)
        state["claim"] = {
            "commentId": 123,
            "status": "active",
            "holder": {"id": "user/sail/original-worker", "session": "original-worker"},
            "expiresAt": "2099-01-01T00:00:00Z",
        }
        state["evidence"] = {
            "revision": "a" * 40,
            "recordPath": "/durable/evidence.json",
            "status": "complete",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
        state["gateVerdicts"] = [{"gate": "review", "status": "passed"}]
        self.path.write_text(json.dumps(state))
        for boundary, phase in (
            ("draft-published", "review"),
            ("before-pr-loop", "pr"),
        ):
            with self.subTest(boundary=boundary):
                current = self.load()
                current["workflow"]["phase"] = phase
                self.path.write_text(json.dumps(current))
                pending = {**self.pending, "id": boundary, "boundary": boundary}
                self.assertEqual(self.invoke(pending).returncode, 0)
                result = self.invoke(
                    {
                        "id": boundary,
                        "boundary": boundary,
                        "status": "accepted",
                        "worker": f"fresh-{phase}",
                        "inputTokens": 1000,
                    }
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                after = self.load()
                for key in ("claim", "evidence", "gateVerdicts", "bookkeeping"):
                    self.assertEqual(after[key], state[key], key)
                self.assertEqual(
                    after["handoffs"][-1]["claimBinding"],
                    {"commentId": 123, "holder": state["claim"]["holder"]},
                )

    def test_changed_claim_holder_blocks_pending_delegation(self) -> None:
        state = self.load()
        state["bookkeeping"]["claims"] = True
        state["claim"] = {
            "commentId": 123,
            "status": "active",
            "holder": {"id": "first"},
        }
        self.path.write_text(json.dumps(state))
        self.assertEqual(self.invoke(self.pending).returncode, 0)
        state = self.load()
        state["claim"]["holder"]["id"] = "other"
        self.path.write_text(json.dumps(state))
        result = self.invoke(
            {
                **self.pending,
                "status": "accepted",
                "worker": "fresh",
                "inputTokens": 1000,
            }
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("claim holder changed", result.stderr)
