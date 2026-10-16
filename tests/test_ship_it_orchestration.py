"""Behavior tests for durable ship-it orchestration and recovery commands.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins/ship-it/skills/ship-it/scripts"
sys.path.insert(0, str(SCRIPTS))

bookkeeping = importlib.import_module("bookkeeping")

UMBRELLA = "https://github.com/o/r/issues/1"
FIRST = "https://github.com/o/r/issues/2"
SECOND = "https://github.com/o/r/issues/3"
REVISION = "a" * 40


class OrchestrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = {**os.environ, "XDG_DATA_HOME": str(self.root / "durable")}
        grant = {
            "id": "user-grant",
            "source": {
                "kind": "user-request",
                "message": "ship the umbrella",
                "reference": "message-1",
                "request": None,
            },
            "scope": ["Implement and ship all children"],
            "limits": [],
            "status": "active",
        }
        result = self.run_cli(
            "create",
            "--repository",
            str(ROOT),
            "--identity",
            "github.com/o/r",
            "--source-json",
            json.dumps(
                {"sourceType": "github", "repository": "github.com/o/r", "issue": 1}
            ),
            "--source-url",
            UMBRELLA,
            "--title",
            "Umbrella",
            "--objective",
            "Ship children",
            "--criteria-json",
            '["Children are delivered"]',
            "--grant-json",
            json.dumps(grant),
            "--checkpoint-dir",
            str(self.root / "scratch"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.checkpoint = Path(json.loads(result.stdout)["checkpoint"])

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "bookkeeping.py"), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            env=self.environment,
        )

    def document(self) -> dict:
        return json.loads(self.checkpoint.read_text())

    def command(
        self, name: str, option: str, value: dict, *, success: bool = True
    ) -> subprocess.CompletedProcess[str]:
        before = self.checkpoint.read_bytes()
        result = self.run_cli(
            name, "--checkpoint", str(self.checkpoint), option, json.dumps(value)
        )
        self.assertEqual(result.returncode, 0 if success else 2, result.stderr)
        if not success:
            self.assertEqual(before, self.checkpoint.read_bytes())
        return result

    def graph(self, *, dependencies: bool = False) -> dict:
        return {
            "umbrellaUrl": UMBRELLA,
            "children": [
                {"issueUrl": FIRST, "dependencies": []},
                {"issueUrl": SECOND, "dependencies": [FIRST] if dependencies else []},
            ],
            "nextAction": "Dispatch eligible children",
        }

    def event(
        self,
        event_id: str,
        kind: str,
        data: dict,
        *,
        issue: str = FIRST,
        revision: str | None = REVISION,
        dispatch: str = "dispatch-1",
        success: bool = True,
    ) -> dict:
        event = {
            "eventId": event_id,
            "kind": kind,
            "issueUrl": issue,
            "dispatchId": dispatch,
            "expectedRevision": revision,
            "data": data,
            "nextAction": "Reconcile next event",
        }
        self.command(
            "record-orchestration-event", "--event-json", event, success=success
        )
        return event

    def initialize(self, *, dependencies: bool = False) -> None:
        self.command(
            "set-orchestration",
            "--orchestration-json",
            self.graph(dependencies=dependencies),
        )
        self.event(
            "dispatch-event",
            "dispatch",
            {
                "worker": "worker-1",
                "worktree": str(self.root / "worktree"),
                "branch": "feat/child",
                "revision": REVISION,
            },
            revision=None,
        )

    def test_dispatch_retry_preserves_authority_and_allowances(self) -> None:
        before = self.document()
        self.initialize()
        event = self.document()["orchestration"]["events"][0]
        result = self.command("record-orchestration-event", "--event-json", event)
        self.assertFalse(json.loads(result.stdout)["applied"])
        after = self.document()
        self.assertEqual(before["authorization"], after["authorization"])
        self.assertEqual(before["convergence"], after["convergence"])
        event["data"]["worker"] = "replacement"
        self.command("record-orchestration-event", "--event-json", event, success=False)

    def test_missing_cyclic_and_changed_dispatched_dependencies_rejected(self) -> None:
        for dependencies in (["https://github.com/o/r/issues/99"], [FIRST], [SECOND]):
            graph = self.graph()
            graph["children"][0]["dependencies"] = dependencies
            if dependencies == [SECOND]:
                graph["children"][1]["dependencies"] = [FIRST]
            self.command(
                "set-orchestration", "--orchestration-json", graph, success=False
            )
        self.initialize()
        graph = self.graph()
        graph["children"][0]["dependencies"] = [SECOND]
        self.command("set-orchestration", "--orchestration-json", graph, success=False)

    def test_prerequisites_and_stale_dispatch_or_revision_rejected(self) -> None:
        self.initialize(dependencies=True)
        self.event(
            "dispatch-dependent",
            "dispatch",
            {
                "worker": "worker-2",
                "worktree": str(self.root / "second"),
                "branch": "feat/second",
                "revision": REVISION,
            },
            issue=SECOND,
            dispatch="dispatch-2",
            revision=None,
            success=False,
        )
        for revision, dispatch in (
            ("b" * 40, "dispatch-1"),
            (REVISION, "old-dispatch"),
        ):
            self.event(
                f"stale-{dispatch}",
                "child-update",
                {"nextAction": "progress"},
                revision=revision,
                dispatch=dispatch,
                success=False,
            )

    def test_terminal_requires_current_gates_release_and_delivery(self) -> None:
        self.initialize()
        terminal = {"status": "completed", "nextAction": "Done"}
        self.event("premature", "terminal", terminal, success=False)
        self.event(
            "update",
            "child-update",
            {
                "requiredGates": ["review"],
                "gatedHead": REVISION,
                "pullRequestUrl": "https://github.com/o/r/pull/4",
                "mergeCommit": "c" * 40,
                "unresolvedThreadCount": 0,
                "issueState": "closed",
            },
        )
        lease = {"leaseId": "lease-1", "gate": "review"}
        self.event("request", "capacity-request", lease)
        gate = {**lease, "status": "passed", "revision": REVISION}
        self.event("ungranted-gate", "gate", gate, success=False)
        self.event("grant", "capacity-grant", lease)
        self.event("gate", "gate", gate)
        self.event("active-lease", "terminal", terminal, success=False)
        self.event("release", "capacity-release", lease)
        event = self.event("done", "terminal", terminal)
        result = self.command("record-orchestration-event", "--event-json", event)
        self.assertFalse(json.loads(result.stdout)["applied"])
        self.event("late-update", "child-update", {"nextAction": "Late"}, success=False)
        self.assertEqual(
            len(self.document()["orchestration"]["children"][0]["gateVerdicts"]), 1
        )

    def test_revision_change_invalidates_gates(self) -> None:
        self.initialize()
        lease = {"leaseId": "lease-1", "gate": "review"}
        self.event("request", "capacity-request", lease)
        self.event("grant", "capacity-grant", lease)
        self.event("gate", "gate", {**lease, "status": "passed", "revision": REVISION})
        self.event("update", "child-update", {"revision": "b" * 40})
        child = self.document()["orchestration"]["children"][0]
        self.assertEqual(child["gateVerdicts"], [])
        self.assertIsNone(child["gatedHead"])

    def test_investigated_child_completes_without_fake_delivery(self) -> None:
        self.initialize()
        self.event(
            "investigation",
            "child-update",
            {
                "gatedHead": REVISION,
                "issueState": "closed",
                "unresolvedThreadCount": 0,
                "requiredGates": ["local-checks"],
                "investigation": {
                    "reason": "Already implemented",
                    "evidence": ["Focused reproduction passed"],
                    "verifiedRevision": REVISION,
                },
            },
        )
        self.event(
            "checks",
            "gate",
            {
                "gate": "local-checks",
                "status": "passed",
                "revision": REVISION,
                "leaseId": None,
            },
        )
        self.event(
            "done",
            "terminal",
            {"status": "completed", "nextAction": "Report investigation"},
        )
        child = self.document()["orchestration"]["children"][0]
        self.assertIsNone(child["pullRequestUrl"])
        self.assertIsNone(child["mergeCommit"])
        self.assertEqual(child["status"], "completed")

    def test_scoped_recovery_is_idempotent_and_preserves_counters(self) -> None:
        result = self.run_cli(
            "transition",
            "--checkpoint",
            str(self.checkpoint),
            "--phase",
            "implement",
            "--status",
            "active",
            "--revision",
            REVISION,
            "--next-action",
            "Fix acceptance failure",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.document()
        recovery = {
            "eventId": "recovery-1",
            "failure": "Dispatch lost",
            "criterion": "Children are delivered",
            "grantId": "user-grant",
            "revision": REVISION,
            "correction": "Persist event before delivery",
            "verification": "python3 focused_repro.py",
            "result": "passed",
        }
        self.command("record-acceptance-recovery", "--recovery-json", recovery)
        result = self.command("record-acceptance-recovery", "--recovery-json", recovery)
        self.assertFalse(json.loads(result.stdout)["applied"])
        after = self.document()
        self.assertEqual(before["authorization"], after["authorization"])
        del after["convergence"]["acceptanceRecovery"]
        self.assertEqual(before["convergence"], after["convergence"])
        for field, value in (
            ("criterion", "Unrelated improvement"),
            ("grantId", "invented"),
            ("revision", "b" * 40),
        ):
            invalid = {**recovery, "eventId": "invalid", field: value}
            self.command(
                "record-acceptance-recovery", "--recovery-json", invalid, success=False
            )

        grant = self.document()["authorization"]["grants"][0]
        for status, limits in (
            ("revoked", []),
            ("active", [{"resource": "attempts", "maximum": 1, "used": 1}]),
        ):
            invalid_grant = {
                **grant,
                "id": f"grant-{status}",
                "status": status,
                "limits": limits,
            }
            self.command("add-grant", "--grant-json", invalid_grant)
            self.command(
                "record-acceptance-recovery",
                "--recovery-json",
                {
                    **recovery,
                    "eventId": f"recovery-{status}",
                    "grantId": invalid_grant["id"],
                },
                success=False,
            )

    def test_relocation_preserves_full_state_and_retries(self) -> None:
        self.initialize()
        before = self.document()
        original = self.checkpoint
        result = self.run_cli("relocate-checkpoint", "--checkpoint", str(original))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.checkpoint = Path(json.loads(result.stdout)["checkpoint"])
        self.assertEqual(self.document(), before)
        self.assertFalse(original.exists())
        result = self.run_cli("relocate-checkpoint", "--checkpoint", str(original))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["relocated"])

    def test_atomic_failure_preserves_previous_graph(self) -> None:
        self.initialize()
        before = self.checkpoint.read_bytes()
        original = bookkeeping.atomic_write

        def fail_write(_path: Path, _document: dict) -> None:
            message = "injected write failure"
            raise OSError(message)

        bookkeeping.atomic_write = fail_write
        self.addCleanup(setattr, bookkeeping, "atomic_write", original)
        with self.assertRaises(OSError):
            bookkeeping.mutate_checkpoint(
                self.checkpoint,
                lambda document: document["orchestration"].update({"events": []}) or {},
            )
        self.assertEqual(before, self.checkpoint.read_bytes())

    def test_already_satisfied_requires_closed_source_and_revision_bound_gates(
        self,
    ) -> None:
        result = self.run_cli(
            "transition",
            "--checkpoint",
            str(self.checkpoint),
            "--phase",
            "implement",
            "--status",
            "active",
            "--revision",
            REVISION,
            "--next-action",
            "Verify existing behavior",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.command(
            "set-risk",
            "--risk-json",
            {
                "level": "low",
                "diffClass": "docs",
                "policySource": "test",
                "matchedRules": [],
                "requiredGates": ["investigation-audit"],
            },
        )
        outcome = {
            "result": "already-satisfied",
            "reason": "Existing implementation meets every acceptance criterion",
            "verifiedRevision": REVISION,
            "evidence": ["Independent audit and focused reproduction passed"],
            "sourceState": "closed",
            "branchCleanup": "preserved",
            "completedAt": "2026-10-16T12:00:00Z",
            "pullRequestUrl": None,
            "pullRequestHead": None,
            "mergeCommit": None,
        }

        def complete(value: dict) -> subprocess.CompletedProcess[str]:
            return self.run_cli(
                "transition",
                "--checkpoint",
                str(self.checkpoint),
                "--phase",
                "complete",
                "--status",
                "completed",
                "--next-action",
                "Report investigation",
                "--outcome-json",
                json.dumps(value),
            )

        before = self.checkpoint.read_bytes()
        self.assertEqual(complete(outcome).returncode, 2)
        self.assertEqual(before, self.checkpoint.read_bytes())
        self.command(
            "record-gate",
            "--verdict-json",
            {
                "gate": "investigation-audit",
                "status": "passed",
                "revision": REVISION,
                "provider": "independent-auditor",
                "summary": "Existing behavior meets all criteria",
            },
        )
        for field, value in (
            ("verifiedRevision", "b" * 40),
            ("sourceState", "unchanged"),
            ("evidence", []),
            ("mergeCommit", "c" * 40),
        ):
            before = self.checkpoint.read_bytes()
            self.assertEqual(complete({**outcome, field: value}).returncode, 2)
            self.assertEqual(before, self.checkpoint.read_bytes())
        result = complete(outcome)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.document()["outcome"], outcome)


if __name__ == "__main__":
    unittest.main()
