"""Exercise checkpoint creation and section commands through the real CLI.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_ship_it_bookkeeping import SCRIPT, checkpoint_document, checkpoint_path

REVISION = "a" * 40
GITHUB_SOURCE = {
    "sourceType": "github",
    "repository": "github.com/smykla-skalski/sai",
    "issue": 277,
}
GRANT = {
    "id": "ship",
    "source": {
        "kind": "user-request",
        "message": "ship this",
        "reference": "user:1",
        "request": None,
    },
    "scope": ["reviewCycles"],
    "limits": [],
    "status": "active",
}
RELEASE_POLICY = {
    "schemaVersion": 1,
    "sources": ["bundled default"],
    "requiredReviewers": [],
    "requiredChecks": ["test"],
    "merge": {"method": "github", "strategy": "squash", "botComment": None},
    "issueClosure": "pull-request-keyword",
    "branchCleanup": "delete",
    "activatedFallbacks": [],
    "resolvedAt": "2026-01-01T00:00:00Z",
}
RISK = {
    "level": "medium",
    "diffClass": "code",
    "policySource": "bundled default",
    "matchedRules": [],
    "requiredGates": ["local-checks", "adversarial-review", "ci"],
}


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class CheckpointCreationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def create(
        self,
        source: dict | None = None,
        criteria: list | None = None,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return run(
            "create",
            "--repository",
            str(self.root),
            "--identity",
            "github.com/smykla-skalski/sai",
            "--source-json",
            json.dumps(GITHUB_SOURCE if source is None else source),
            "--title",
            "Add helper commands",
            "--objective",
            "Remove hand-edited checkpoint JSON",
            "--criteria-json",
            json.dumps(["creates a checkpoint"] if criteria is None else criteria),
            "--checkpoint-dir",
            str(self.root / "checkpoints"),
            *extra,
        )

    def test_create_writes_documented_identity_and_defaults(self) -> None:
        result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        canonical = (
            '{"issue":277,"repository":"github.com/smykla-skalski/sai",'
            '"sourceType":"github"}'
        )
        identity = hashlib.sha256(canonical.encode()).hexdigest()
        path = self.root / "checkpoints" / f"{identity}.json"
        self.assertEqual(output["checkpoint"], str(path.resolve()))
        self.assertTrue(output["created"])
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["checkpointId"], identity)
        self.assertEqual(document["task"]["canonicalSource"], canonical)
        self.assertEqual(document["workflow"]["phase"], "resolve")
        self.assertEqual(document["workflow"]["status"], "active")
        self.assertIsNone(document["workflow"]["revision"])
        self.assertEqual(document["bookkeeping"]["telemetry"], True)
        self.assertEqual(document["evidence"]["status"], "disabled")
        self.assertEqual(document["authorization"], {"grants": []})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_created_checkpoint_accepts_transitions_and_grants(self) -> None:
        result = self.create(None, None, "--grant-json", json.dumps(GRANT))
        self.assertEqual(result.returncode, 0, result.stderr)
        path = json.loads(result.stdout)["checkpoint"]
        moved = run(
            "transition",
            "--checkpoint",
            path,
            "--phase",
            "explore",
            "--status",
            "active",
            "--next-action",
            "explore the repository",
        )
        self.assertEqual(moved.returncode, 0, moved.stderr)
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(document["authorization"]["grants"][0]["id"], "ship")

    def test_existing_checkpoint_is_never_overwritten(self) -> None:
        first = json.loads(self.create().stdout)
        path = Path(first["checkpoint"])
        document = json.loads(path.read_text(encoding="utf-8"))
        document["workflow"]["nextAction"] = "continue the recorded work"
        path.write_text(json.dumps(document), encoding="utf-8")
        original = path.read_bytes()
        second = self.create()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)["created"])
        self.assertEqual(path.read_bytes(), original)

    def test_foreign_file_at_the_identity_path_is_a_mismatch(self) -> None:
        path = Path(json.loads(self.create().stdout)["checkpoint"])
        document = json.loads(path.read_text(encoding="utf-8"))
        document["task"]["canonicalSource"] = "{}"
        path.write_text(json.dumps(document), encoding="utf-8")
        original = path.read_bytes()
        result = self.create()
        self.assertEqual(result.returncode, 2)
        self.assertIn("another canonical source", result.stderr)
        self.assertEqual(path.read_bytes(), original)

    def test_jira_and_description_sources_follow_the_identity_contract(self) -> None:
        jira = {"sourceType": "jira", "site": "example.atlassian.net", "key": "ABC-12"}
        description = {
            "sourceType": "description",
            "repository": "github.com/smykla-skalski/sai",
            "objective": "Remove hand-edited checkpoint JSON",
            "acceptanceCriteria": ["creates a checkpoint"],
        }
        for source in (jira, description):
            with self.subTest(source=source["sourceType"]):
                result = self.create(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                path = Path(json.loads(result.stdout)["checkpoint"])
                document = json.loads(path.read_text(encoding="utf-8"))
                canonical = json.dumps(
                    source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                self.assertEqual(document["task"]["canonicalSource"], canonical)
                self.assertEqual(
                    path.name, hashlib.sha256(canonical.encode()).hexdigest() + ".json"
                )

    def test_invalid_input_writes_nothing(self) -> None:
        cases = {
            "empty criteria": (GITHUB_SOURCE, []),
            "blank criterion": (GITHUB_SOURCE, [" "]),
            "uppercase repository": (
                {**GITHUB_SOURCE, "repository": "github.com/Smykla/Sai"},
                None,
            ),
            "string issue": ({**GITHUB_SOURCE, "issue": "277"}, None),
            "unknown type": ({"sourceType": "linear"}, None),
            "extra field": ({**GITHUB_SOURCE, "title": "x"}, None),
            "lowercase jira key": (
                {"sourceType": "jira", "site": "a.example", "key": "abc-1"},
                None,
            ),
            "description mismatch": (
                {
                    "sourceType": "description",
                    "repository": "github.com/o/r",
                    "objective": "other",
                    "acceptanceCriteria": ["creates a checkpoint"],
                },
                None,
            ),
        }
        for name, (source, criteria) in cases.items():
            with self.subTest(name):
                result = self.create(source, criteria)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse((self.root / "checkpoints").exists())

    def test_malformed_json_and_source_types_exit_with_usage_errors(self) -> None:
        for name, source, criteria in (
            ("criteria", None, "not json"),
            ("source type", {"sourceType": []}, None),
        ):
            with self.subTest(name):
                result = run(
                    "create",
                    "--repository",
                    str(self.root),
                    "--identity",
                    "github.com/smykla-skalski/sai",
                    "--source-json",
                    json.dumps(source or GITHUB_SOURCE),
                    "--title",
                    "t",
                    "--objective",
                    "o",
                    "--criteria-json",
                    criteria or '["c"]',
                    "--checkpoint-dir",
                    str(self.root / "checkpoints"),
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.root / "checkpoints").exists())

    def test_non_object_task_in_an_existing_file_is_a_mismatch(self) -> None:
        path = Path(json.loads(self.create().stdout)["checkpoint"])
        path.write_text('{"task": 5}', encoding="utf-8")
        result = self.create()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_grant_is_rejected_before_writing(self) -> None:
        result = self.create(
            None, None, "--grant-json", json.dumps({**GRANT, "scope": "x"})
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("scope must be a non-empty array of strings", result.stderr)
        self.assertFalse((self.root / "checkpoints").exists())

    def test_enabled_evidence_starts_missing(self) -> None:
        result = self.create(None, None, "--enable", "evidence")
        document = json.loads(
            Path(json.loads(result.stdout)["checkpoint"]).read_text(encoding="utf-8")
        )
        self.assertEqual(document["evidence"]["status"], "missing")
        self.assertTrue(document["bookkeeping"]["evidence"])


class SectionCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.document = checkpoint_document()
        self.document["workflow"]["revision"] = REVISION
        self.document["authorization"] = {"grants": [GRANT]}
        self.document["risk"] = {
            "level": None,
            "diffClass": None,
            "policySource": None,
            "matchedRules": [],
            "requiredGates": [],
            "overrideAuthorization": None,
        }
        self.path = checkpoint_path(self.directory.name, self.document)
        self.write(self.document)

    def write(self, document: dict) -> None:
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def command(
        self, name: str, option: str, value: object
    ) -> subprocess.CompletedProcess[str]:
        return run(name, "--checkpoint", str(self.path), option, json.dumps(value))

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_refused(
        self, result: subprocess.CompletedProcess[str], text: str
    ) -> None:
        before = self.path.read_bytes()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(text, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_set_risk_stores_the_selection(self) -> None:
        self.assert_ok(self.command("set-risk", "--risk-json", RISK))
        risk = self.read()["risk"]
        self.assertEqual(risk["level"], "medium")
        self.assertEqual(risk["requiredGates"], RISK["requiredGates"])
        self.assertIsNone(risk["overrideAuthorization"])

    def test_lowering_risk_requires_an_override_that_is_then_kept(self) -> None:
        self.assert_ok(
            self.command("set-risk", "--risk-json", {**RISK, "level": "high"})
        )
        before = self.path.read_bytes()
        self.assert_refused(
            self.command("set-risk", "--risk-json", RISK), "overrideAuthorization"
        )
        self.assertEqual(self.path.read_bytes(), before)
        override = "user: ship at medium"
        lowered = {**RISK, "overrideAuthorization": override}
        self.assert_ok(self.command("set-risk", "--risk-json", lowered))
        self.assert_ok(self.command("set-risk", "--risk-json", RISK))
        self.assertEqual(self.read()["risk"]["overrideAuthorization"], override)

    def test_explicit_null_override_keeps_the_recorded_authorization(self) -> None:
        override = "user: ship at medium"
        self.assert_ok(
            self.command(
                "set-risk",
                "--risk-json",
                {**RISK, "level": "high", "overrideAuthorization": override},
            )
        )
        self.assert_ok(
            self.command(
                "set-risk",
                "--risk-json",
                {**RISK, "overrideAuthorization": None},
            )
        )
        self.assertEqual(self.read()["risk"]["overrideAuthorization"], override)

    def test_invalid_risk_is_refused(self) -> None:
        for field, value in (
            ("level", "critical"),
            ("diffClass", "other"),
            ("requiredGates", ["ci", "ci"]),
            ("matchedRules", "none"),
        ):
            with self.subTest(field=field):
                self.assert_refused(
                    self.command("set-risk", "--risk-json", {**RISK, field: value}),
                    "risk",
                )

    def test_bot_comment_release_policy_is_accepted(self) -> None:
        policy = {
            **RELEASE_POLICY,
            "merge": {
                "method": "bot-comment",
                "strategy": "squash",
                "botComment": "squash",
            },
            "requiredReviewers": [
                {"id": "r", "kind": "human", "actor": "team:x", "request": "reviewer"}
            ],
        }
        self.assert_ok(self.command("set-release-policy", "--policy-json", policy))
        self.assertEqual(self.read()["releasePolicy"], policy)

    def test_set_release_policy_and_material_change_stales_hosted_verdicts(
        self,
    ) -> None:
        self.assert_ok(
            self.command("set-release-policy", "--policy-json", RELEASE_POLICY)
        )
        document = self.read()
        self.assertEqual(document["releasePolicy"], RELEASE_POLICY)
        document["gateVerdicts"] = [
            {"gate": "ci", "status": "passed", "revision": REVISION},
            {"gate": "adversarial-review", "status": "passed", "revision": REVISION},
        ]
        self.write(document)
        refreshed = {**RELEASE_POLICY, "resolvedAt": "2026-01-02T00:00:00Z"}
        result = self.assert_ok(
            self.command("set-release-policy", "--policy-json", refreshed)
        )
        self.assertFalse(result["materialChange"])
        self.assertEqual(self.read()["gateVerdicts"][0]["status"], "passed")
        changed = {**refreshed, "requiredChecks": ["test", "lint"]}
        result = self.assert_ok(
            self.command("set-release-policy", "--policy-json", changed)
        )
        verdicts = self.read()["gateVerdicts"]
        self.assertTrue(result["materialChange"])
        self.assertEqual(verdicts[0]["status"], "stale")
        self.assertEqual(
            verdicts[0]["invalidation"]["reason"], "release-policy-changed"
        )
        self.assertEqual(verdicts[1]["status"], "passed")

    def test_invalid_release_policy_is_refused(self) -> None:
        reviewer = {
            "id": "r",
            "kind": "human",
            "actor": "team:x",
            "request": "reviewer",
        }
        for field, value in (
            ("schemaVersion", 2),
            ("schemaVersion", True),
            ("sources", []),
            ("resolvedAt", "yesterday"),
            ("merge", "squash"),
            ("merge", {}),
            (
                "merge",
                {"method": "bot-comment", "strategy": "squash", "botComment": None},
            ),
            (
                "merge",
                {"method": "github", "strategy": "squash", "botComment": "squash"},
            ),
            ("merge", {"method": "github", "strategy": "fast", "botComment": None}),
            ("issueClosure", "typo"),
            ("branchCleanup", "maybe"),
            ("requiredChecks", ["a", "a"]),
            ("requiredReviewers", [1]),
            ("requiredReviewers", [{**reviewer, "kind": "robot"}]),
            ("requiredReviewers", [reviewer, reviewer]),
            ("unknownField", "x"),
            ("activatedFallbacks", [{"gate": "hosted-review"}]),
        ):
            with self.subTest(field=field):
                self.assert_refused(
                    self.command(
                        "set-release-policy",
                        "--policy-json",
                        {**RELEASE_POLICY, field: value},
                    ),
                    "releasePolicy",
                )

    def test_record_gate_binds_the_current_revision_and_replaces_duplicates(
        self,
    ) -> None:
        verdict = {
            "gate": "local-checks",
            "status": "passed",
            "revision": REVISION,
            "provider": "local",
            "summary": "ruff and unittest passed",
        }
        self.assert_ok(self.command("record-gate", "--verdict-json", verdict))
        self.assert_ok(
            self.command(
                "record-gate", "--verdict-json", {**verdict, "status": "failed"}
            )
        )
        verdicts = self.read()["gateVerdicts"]
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["status"], "failed")
        self.assertIn("timestamp", verdicts[0])
        self.assert_refused(
            self.command(
                "record-gate", "--verdict-json", {**verdict, "revision": "b" * 40}
            ),
            "current workflow revision",
        )
        self.assert_refused(
            self.command("record-gate", "--verdict-json", {**verdict, "status": "ok"}),
            "verdict status",
        )
        self.assert_refused(
            self.command(
                "record-gate", "--verdict-json", {**verdict, "summary": "x" * 501}
            ),
            "summary exceeds",
        )

    def test_record_gate_is_refused_when_evidence_owns_verdicts(self) -> None:
        self.document["bookkeeping"]["evidence"] = True
        self.document["evidence"] = {
            "revision": None,
            "recordPath": None,
            "status": "missing",
            "updatedAt": None,
        }
        self.write(self.document)
        verdict = {
            "gate": "ci",
            "status": "passed",
            "revision": REVISION,
            "provider": "github",
            "summary": "green",
        }
        self.assert_refused(
            self.command("record-gate", "--verdict-json", verdict), "evidence record"
        )

    def reviewed_document(self, verdict: str = "failed") -> None:
        convergence = self.document["convergence"]
        convergence.update(
            {
                "reservations": [
                    {
                        "id": "review-1",
                        "kind": "review",
                        "revision": "c" * 40,
                        "inputs": "affected:one",
                        "reservedAt": "2026-01-01T00:00:00Z",
                        "ordinal": 1,
                        "status": "completed",
                        "result": {"verdict": verdict},
                    }
                ],
                "reviewCycles": 1,
                "startedAt": "2026-01-01T00:00:00Z",
                "reviewedRevision": "c" * 40,
                "findings": [
                    {
                        "id": "F1",
                        "label": "issue",
                        "location": "a.py:1",
                        "summary": "bug",
                        "disposition": "open",
                    },
                    {
                        "id": "F2",
                        "label": "question",
                        "location": "b.py:2",
                        "summary": "naming",
                        "disposition": "open",
                    },
                ],
            }
        )
        self.write(self.document)

    def test_set_findings_records_dispositions_and_follow_up_urls(self) -> None:
        self.reviewed_document()
        url = "https://github.com/smykla-skalski/sai/issues/300"
        self.assert_ok(
            self.command(
                "set-findings",
                "--dispositions-json",
                {
                    "F1": "fixed",
                    "F2": {"disposition": "follow-up", "followUpIssue": url},
                },
            )
        )
        convergence = self.read()["convergence"]
        self.assertEqual(
            [finding["disposition"] for finding in convergence["findings"]],
            ["fixed", "follow-up"],
        )
        self.assertEqual(convergence["followUpIssues"], [url])
        self.assert_ok(
            self.command(
                "set-findings",
                "--dispositions-json",
                {"F2": {"disposition": "follow-up", "followUpIssue": url}},
            )
        )
        self.assertEqual(self.read()["convergence"]["followUpIssues"], [url])

    def test_set_findings_refuses_inconsistent_updates(self) -> None:
        self.reviewed_document()
        for name, updates, text in (
            ("unknown id", {"F9": "fixed"}, "unknown finding"),
            ("bad disposition", {"F1": "done"}, "invalid disposition"),
            ("follow-up without url", {"F1": "follow-up"}, "followUpIssue"),
            ("blocked while active", {"F1": "blocked"}, "blocked workflow"),
            ("empty", {}, "at least one finding"),
        ):
            with self.subTest(name):
                self.assert_refused(
                    self.command("set-findings", "--dispositions-json", updates), text
                )

    def attest(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run(
            "attest-review",
            "--checkpoint",
            str(self.path),
            "--revision",
            REVISION,
            "--summary",
            "fix verified against the findings",
            *extra,
        )

    def test_attest_review_requires_every_finding_resolved(self) -> None:
        self.reviewed_document()
        self.assert_refused(self.attest(), "fixed or deferred")
        self.assert_ok(
            self.command(
                "set-findings",
                "--dispositions-json",
                {
                    "F1": "fixed",
                    "F2": {
                        "disposition": "follow-up",
                        "followUpIssue": "https://x.test/1",
                    },
                },
            )
        )
        result = self.assert_ok(self.attest("--command", "python3 -m unittest"))
        self.assertEqual(result["reviewedRevision"], "c" * 40)
        verdict = self.read()["gateVerdicts"][0]
        self.assertEqual(verdict["gate"], "adversarial-review")
        self.assertEqual(verdict["provider"], "ship-it-convergence")
        self.assertEqual(verdict["revision"], REVISION)
        self.assertEqual(verdict["reviewedRevision"], "c" * 40)
        self.assertEqual(verdict["commands"], ["python3 -m unittest"])
        self.assertEqual([f["id"] for f in verdict["findings"]], ["F1", "F2"])

    def test_attest_review_requires_a_failed_review_with_findings(self) -> None:
        self.reviewed_document("passed")
        self.assert_refused(self.attest(), "failed review receipt")
        for verdict in ("failed", "blocked"):
            with self.subTest(verdict=verdict):
                self.reviewed_document(verdict)
                convergence = self.document["convergence"]
                convergence["findings"] = []
                self.write(self.document)
                self.assert_refused(self.attest(), "failed review receipt")
        self.reviewed_document("blocked")
        self.assert_refused(self.attest(), "failed review receipt")

    def test_reopening_a_finding_stales_the_re_attestation(self) -> None:
        self.reviewed_document()
        self.assert_ok(
            self.command(
                "set-findings", "--dispositions-json", {"F1": "fixed", "F2": "fixed"}
            )
        )
        self.assert_ok(self.attest())
        self.assert_ok(
            self.command("set-findings", "--dispositions-json", {"F1": "open"})
        )
        verdict = self.read()["gateVerdicts"][0]
        self.assertEqual(verdict["status"], "stale")
        self.assertEqual(verdict["invalidation"]["reason"], "finding-reopened")
        reserve = run(
            "reserve",
            "--checkpoint",
            str(self.path),
            "--id",
            "test-1",
            "--kind",
            "test",
            "--revision",
            REVISION,
            "--inputs",
            "affected:one",
        )
        self.assertEqual(reserve.returncode, 2)

    def test_blocked_finding_cannot_outlive_the_blocked_workflow(self) -> None:
        self.reviewed_document()
        self.assert_ok(
            run(
                "transition",
                "--checkpoint",
                str(self.path),
                "--phase",
                "review",
                "--status",
                "blocked",
                "--blocker",
                "human decision",
                "--next-action",
                "ask",
            )
        )
        self.assert_ok(
            self.command("set-findings", "--dispositions-json", {"F1": "blocked"})
        )
        before = self.path.read_bytes()
        result = run(
            "transition",
            "--checkpoint",
            str(self.path),
            "--phase",
            "review",
            "--status",
            "active",
            "--next-action",
            "go",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("blocked finding", result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_attested_review_unlocks_the_broad_test_reservation(self) -> None:
        self.reviewed_document()
        self.assert_ok(
            self.command(
                "set-findings", "--dispositions-json", {"F1": "fixed", "F2": "fixed"}
            )
        )
        reserve = (
            "reserve",
            "--checkpoint",
            str(self.path),
            "--id",
            "test-1",
            "--kind",
            "test",
            "--revision",
            REVISION,
            "--inputs",
            "affected:one",
        )
        self.assertEqual(run(*reserve).returncode, 2)
        self.assert_ok(self.attest())
        self.assertTrue(self.assert_ok(run(*reserve))["dispatch"])

    def test_attest_review_refuses_other_revisions_and_missing_review(self) -> None:
        self.assert_refused(self.attest(), "completed review cycle")
        self.reviewed_document()
        self.assert_ok(
            self.command(
                "set-findings", "--dispositions-json", {"F1": "fixed", "F2": "fixed"}
            )
        )
        stale = run(
            "attest-review",
            "--checkpoint",
            str(self.path),
            "--revision",
            "b" * 40,
            "--summary",
            "x",
        )
        self.assert_refused(stale, "current workflow revision")
        self.assert_refused(self.attest("--gate", "local-checks"), "gate must be")


if __name__ == "__main__":
    unittest.main()
