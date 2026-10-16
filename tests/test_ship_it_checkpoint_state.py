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
            ("issueClosure", []),
            ("branchCleanup", {}),
            ("merge", {"method": [], "strategy": "squash", "botComment": None}),
            ("merge", {"method": "github", "strategy": {}, "botComment": None}),
            ("requiredReviewers", [{**reviewer, "kind": []}]),
            (
                "requiredReviewers",
                [{**reviewer, "request": "team-reviewer", "actor": "alice"}],
            ),
            ("requiredReviewers", [{**reviewer, "request_target": None}]),
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

    def add_grant(self, grant: dict) -> subprocess.CompletedProcess[str]:
        return self.command("add-grant", "--grant-json", grant)

    def test_add_grant_appends_to_an_existing_checkpoint(self) -> None:
        reply = {
            "id": "more-review",
            "source": {
                "kind": "user-reply",
                "message": "yes, one more review cycle",
                "reference": "user:2",
                "request": "run a third review cycle?",
            },
            "scope": ["reviewCycles"],
            "limits": [{"resource": "review cycles", "maximum": 1, "used": 0}],
            "status": "active",
        }
        output = self.assert_ok(self.add_grant(reply))
        self.assertEqual(output["grant"], "more-review")
        self.assertEqual(output["grants"], 2)
        self.assertEqual(self.read()["authorization"]["grants"], [GRANT, reply])

    def test_add_grant_leaves_revoked_and_exhausted_grants_unchanged(self) -> None:
        revoked = {**GRANT, "id": "old", "status": "revoked"}
        exhausted = {
            **GRANT,
            "id": "spent",
            "status": "exhausted",
            "limits": [{"resource": "review cycles", "maximum": 2, "used": 2}],
        }
        self.document["authorization"] = {"grants": [GRANT, revoked, exhausted]}
        self.write(self.document)
        self.assert_ok(self.add_grant({**GRANT, "id": "fresh"}))
        grants = self.read()["authorization"]["grants"]
        self.assertEqual(grants, [GRANT, revoked, exhausted, {**GRANT, "id": "fresh"}])

    def test_add_grant_creates_the_authorization_section_for_a_legacy_file(
        self,
    ) -> None:
        del self.document["authorization"]
        self.write(self.document)
        self.assert_ok(self.add_grant(GRANT))
        self.assertEqual(self.read()["authorization"], {"grants": [GRANT]})

    def test_add_grant_refuses_a_recorded_id_even_when_revoked(self) -> None:
        self.assert_refused(
            self.add_grant({**GRANT, "scope": ["other"]}),
            "grant ID already recorded: ship",
        )
        self.document["authorization"] = {
            "grants": [{**GRANT, "status": "revoked"}],
        }
        self.write(self.document)
        self.assert_refused(self.add_grant(GRANT), "grant ID already recorded: ship")

    def test_add_grant_refuses_an_empty_source_message(self) -> None:
        for source in (
            {**GRANT["source"], "message": ""},
            {**GRANT["source"], "message": "  "},
            {**GRANT["source"], "message": None},
            {key: value for key, value in GRANT["source"].items() if key != "message"},
            "ship this",
            None,
        ):
            with self.subTest(source=source):
                self.assert_refused(
                    self.add_grant({**GRANT, "id": "new", "source": source}),
                    "grant source",
                )

    def test_add_grant_names_the_required_scope_shape(self) -> None:
        shape = "grant scope must be a non-empty array of non-empty strings"
        for scope in ("reviewCycles", [], [""], ["ok", " "], ["ok", 3], None, {"a": 1}):
            with self.subTest(scope=scope):
                self.assert_refused(
                    self.add_grant({**GRANT, "id": "new", "scope": scope}), shape
                )
        self.assert_refused(
            self.add_grant(
                {
                    key: value
                    for key, value in GRANT.items()
                    if key not in ("id", "scope")
                }
            ),
            "grant id must be a non-empty string",
        )

    def test_add_grant_applies_the_full_grant_validation(self) -> None:
        for field, value, text in (
            ("status", "pending", "invalid authorization grant status"),
            ("limits", "none", "authorization limits must be an array"),
            (
                "limits",
                [{"resource": "cycles", "maximum": 1, "used": 2}],
                "within its limit",
            ),
            (
                "source",
                {**GRANT["source"], "reference": ""},
                "authorization source requires reference",
            ),
            (
                "source",
                {**GRANT["source"], "kind": "user-reply", "request": None},
                "concrete pending request",
            ),
        ):
            with self.subTest(field=field, value=value):
                self.assert_refused(
                    self.add_grant({**GRANT, "id": "new", field: value}), text
                )

    def test_add_grant_rejects_a_non_object_value(self) -> None:
        for value in ([GRANT], "grant", 3):
            with self.subTest(value=value):
                self.assert_refused(self.add_grant(value), "--grant-json")

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
            (
                "unhashable disposition",
                {"F1": {"disposition": []}},
                "invalid disposition",
            ),
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

    def decide(
        self, status: str, reason: str = "configured reviewer", **extra: object
    ) -> subprocess.CompletedProcess[str]:
        return self.command(
            "set-hosted-review-decision",
            "--decision-json",
            {"status": status, "reason": reason, **extra},
        )

    def refuse_unchanged(
        self, result: subprocess.CompletedProcess[str], text: str
    ) -> None:
        before = self.path.read_bytes()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(text, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_first_hosted_review_decision_accepts_any_status(self) -> None:
        for status in ("not-required", "serviceable", "fallback", "blocked"):
            with self.subTest(status=status):
                self.write(self.document)
                result = self.assert_ok(self.decide(status, "policy named no reviewer"))
                self.assertEqual(result["hostedReviewDecision"], status)
                self.assertIsNone(result["previous"])
                decision = self.read()["hostedReviewDecision"]
                self.assertEqual(set(decision), {"status", "reason", "decidedAt"})
                self.assertEqual(decision["status"], status)
                self.assertEqual(decision["reason"], "policy named no reviewer")
                self.assertTrue(decision["decidedAt"].endswith("Z"))

    def test_hosted_review_decision_keeps_an_explicit_timestamp(self) -> None:
        stamp = "2026-01-01T00:00:00Z"
        self.assert_ok(self.decide("serviceable", decidedAt=stamp))
        self.assertEqual(self.read()["hostedReviewDecision"]["decidedAt"], stamp)

    def test_serviceable_may_change_once_to_fallback_or_blocked(self) -> None:
        for status in ("fallback", "blocked"):
            with self.subTest(status=status):
                self.write(self.document)
                self.assert_ok(self.decide("serviceable", "copilot configured"))
                result = self.assert_ok(self.decide(status, "quota exhausted"))
                self.assertEqual(result["previous"], "serviceable")
                decision = self.read()["hostedReviewDecision"]
                self.assertEqual(decision["status"], status)
                self.assertEqual(decision["reason"], "quota exhausted")
                self.refuse_unchanged(self.decide(status, "again"), "already set")
                self.refuse_unchanged(self.decide("serviceable"), "already set")

    def test_every_other_hosted_review_change_is_refused(self) -> None:
        statuses = ("not-required", "serviceable", "fallback", "blocked")
        allowed = {("serviceable", "fallback"), ("serviceable", "blocked")}
        for first in statuses:
            for second in statuses:
                if (first, second) in allowed:
                    continue
                with self.subTest(first=first, second=second):
                    self.write(self.document)
                    self.assert_ok(self.decide(first))
                    self.refuse_unchanged(self.decide(second), "already set")

    def test_invalid_hosted_review_decision_writes_nothing(self) -> None:
        for name, payload, text in (
            ("status", {"status": "maybe", "reason": "r"}, "status must be"),
            ("status type", {"status": [], "reason": "r"}, "status must be"),
            ("blank reason", {"status": "blocked", "reason": " "}, "reason"),
            ("long reason", {"status": "blocked", "reason": "x" * 501}, "exceeds"),
            ("missing reason", {"status": "blocked"}, "takes status"),
            ("missing status", {"reason": "r"}, "takes status"),
            ("unknown field", {"status": "blocked", "reason": "r", "x": 1}, "takes"),
            (
                "timestamp",
                {"status": "blocked", "reason": "r", "decidedAt": "yesterday"},
                "decidedAt",
            ),
            (
                "offset",
                {
                    "status": "blocked",
                    "reason": "r",
                    "decidedAt": "2026-01-01T00:00:00+02:00",
                },
                "decidedAt",
            ),
        ):
            with self.subTest(name=name):
                self.refuse_unchanged(
                    self.command(
                        "set-hosted-review-decision", "--decision-json", payload
                    ),
                    text,
                )
                self.assertIsNone(self.read()["hostedReviewDecision"])

    def test_non_object_hosted_review_decision_is_a_usage_error(self) -> None:
        self.refuse_unchanged(
            run(
                "set-hosted-review-decision",
                "--checkpoint",
                str(self.path),
                "--decision-json",
                "[1]",
            ),
            "must contain an object",
        )

    def test_hosted_review_decision_refuses_an_unrecognized_stored_value(self) -> None:
        self.document["hostedReviewDecision"] = "serviceable"
        self.write(self.document)
        self.refuse_unchanged(self.decide("fallback"), "already set")

    def test_hosted_review_decision_leaves_other_state_untouched(self) -> None:
        self.assert_ok(self.decide("serviceable"))
        after = self.read()
        for key in ("workflow", "risk", "releasePolicy", "gateVerdicts", "task"):
            self.assertEqual(after[key], self.document[key], key)

    def recover(self, update: dict) -> subprocess.CompletedProcess[str]:
        return self.command("record-acceptance-recovery", "--recovery-json", update)

    def new_recovery(self, **changes: object) -> dict:
        return {
            "id": "R1",
            "failure": "criterion 2 failed after the fix pass",
            "criterion": "A command refuses an inactive grant",
            "grantId": "ship",
            "revision": REVISION,
            "correction": "reject revoked grants",
            "verification": "python3 -m unittest tests.test_x",
            **changes,
        }

    def attempt(self, result: str = "failed", revision: str = REVISION) -> dict:
        return {"result": result, "revision": revision, "summary": f"{result} run"}

    def test_acceptance_recovery_records_an_entry_with_its_first_attempt(
        self,
    ) -> None:
        update = self.new_recovery(attempt=self.attempt("failed"))
        output = self.assert_ok(self.recover(update))
        self.assertEqual(output["recovery"], "R1")
        self.assertEqual(output["attempts"], 1)
        (entry,) = self.read()["convergence"]["acceptanceRecovery"]
        self.assertEqual(entry["grantId"], "ship")
        self.assertEqual(entry["verification"], update["verification"])
        (attempt,) = entry["attempts"]
        self.assertEqual(attempt["result"], "failed")
        self.assertEqual(attempt["revision"], REVISION)
        self.assertTrue(attempt["recordedAt"].endswith("Z"))

    def test_acceptance_recovery_entry_can_precede_its_first_attempt(self) -> None:
        self.assert_ok(self.recover(self.new_recovery()))
        (entry,) = self.read()["convergence"]["acceptanceRecovery"]
        self.assertEqual(entry["attempts"], [])

    def test_further_attempt_appends_and_never_touches_counters(self) -> None:
        self.document["convergence"].update(
            reviewCycles=2, fixPasses=1, fullQualityGateRuns=1, broadTestRuns=1
        )
        self.document["convergence"]["reviewedRevision"] = REVISION
        self.document["convergence"]["findings"] = []
        self.document["convergence"]["startedAt"] = "2026-01-01T00:00:00Z"
        self.write(self.document)
        before = self.read()["convergence"]
        self.assert_ok(self.recover(self.new_recovery(attempt=self.attempt("failed"))))
        later = "b" * 40
        output = self.assert_ok(
            self.recover({"id": "R1", "attempt": self.attempt("passed", later)})
        )
        self.assertEqual(output["attempts"], 2)
        after = self.read()["convergence"]
        entry = after.pop("acceptanceRecovery")[0]
        self.assertEqual(
            [item["result"] for item in entry["attempts"]], ["failed", "passed"]
        )
        self.assertEqual(entry["attempts"][1]["revision"], later)
        for key in (
            "reviewCycles",
            "fixPasses",
            "fullQualityGateRuns",
            "reviewedRevision",
            "startedAt",
            "findings",
        ):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(after["broadTestRuns"], 1)
        self.assertEqual(after["reservations"], [])

    def test_acceptance_recovery_keeps_separate_entries(self) -> None:
        self.assert_ok(self.recover(self.new_recovery()))
        self.assert_ok(self.recover(self.new_recovery(id="R2")))
        ids = [item["id"] for item in self.read()["convergence"]["acceptanceRecovery"]]
        self.assertEqual(ids, ["R1", "R2"])

    def test_acceptance_recovery_refuses_a_grant_that_is_not_active(self) -> None:
        self.document["authorization"]["grants"] = [
            GRANT,
            {**GRANT, "id": "old", "status": "revoked"},
            {**GRANT, "id": "spent", "status": "exhausted"},
            {**GRANT, "id": "vague", "status": "ambiguous"},
        ]
        self.write(self.document)
        for grant in ("old", "spent", "vague", "missing"):
            with self.subTest(grant=grant):
                self.assert_refused(
                    self.recover(self.new_recovery(grantId=grant)),
                    f"acceptance recovery requires an active grant: {grant}",
                )

    def test_attempt_is_refused_once_the_recorded_grant_is_revoked(self) -> None:
        self.assert_ok(self.recover(self.new_recovery()))
        document = self.read()
        document["authorization"]["grants"][0]["status"] = "revoked"
        self.write(document)
        self.assert_refused(
            self.recover({"id": "R1", "attempt": self.attempt()}),
            "requires an active grant: ship",
        )

    def test_acceptance_recovery_refuses_malformed_input(self) -> None:
        full = self.new_recovery()
        cases = (
            ({**full, "id": " "}, "recovery id"),
            ({k: v for k, v in full.items() if k != "criterion"}, "new recovery"),
            ({**full, "extra": 1}, "new recovery"),
            ({**full, "failure": ""}, "recovery failure"),
            ({**full, "revision": "abc"}, "recovery revision"),
            ({**full, "attempt": {"result": "passed"}}, "recovery attempt requires"),
            (
                {**full, "attempt": {**self.attempt(), "result": "maybe"}},
                "result must be",
            ),
            (
                {**full, "attempt": {**self.attempt(), "revision": "abc"}},
                "attempt revision",
            ),
            (
                {**full, "attempt": {**self.attempt(), "summary": "x" * 501}},
                "exceeds 500",
            ),
            ({**full, "attempt": "passed"}, "attempt must be an object"),
        )
        for update, text in cases:
            with self.subTest(text=text):
                self.assert_refused(self.recover(update), text)

    def test_recorded_entry_is_immutable_apart_from_attempts(self) -> None:
        self.assert_ok(self.recover(self.new_recovery()))
        for update in (
            self.new_recovery(attempt=self.attempt()),
            {"id": "R1", "attempt": self.attempt(), "correction": "other"},
            {"id": "R1"},
        ):
            with self.subTest(keys=sorted(update)):
                self.assert_refused(self.recover(update), "a further attempt takes")

    def test_acceptance_recovery_leaves_other_state_untouched(self) -> None:
        self.assert_ok(self.recover(self.new_recovery(attempt=self.attempt())))
        after = self.read()
        for key in ("workflow", "risk", "authorization", "gateVerdicts", "task"):
            self.assertEqual(after[key], self.document[key], key)

    def test_acceptance_recovery_refuses_a_whitespace_padded_id(self) -> None:
        self.assert_ok(self.recover(self.new_recovery()))
        self.assert_refused(
            self.recover(self.new_recovery(id="R1 ")), "must not have outer spaces"
        )
        self.assert_refused(
            self.recover({"id": "\nR1", "attempt": self.attempt()}),
            "must not have outer spaces",
        )

    def test_attempt_on_a_hand_recorded_entry_is_refused_not_a_crash(self) -> None:
        for entry, text in (
            ({"id": "R1"}, "lacks an attempts array"),
            ({"id": "R1", "grantId": "ship"}, "lacks an attempts array"),
            ({"id": "R1", "grantId": "ship", "attempts": "x"}, "lacks an attempts"),
            ({"id": "R1", "grantId": "ship", "attempts": {}}, "lacks an attempts"),
            ({"id": "R1", "attempts": []}, "requires an active grant: None"),
        ):
            with self.subTest(entry=entry):
                document = self.read()
                document["convergence"]["acceptanceRecovery"] = [entry]
                self.write(document)
                self.assert_refused(
                    self.recover({"id": "R1", "attempt": self.attempt()}), text
                )

    def test_acceptance_recovery_rejects_a_non_object_value(self) -> None:
        for value in ([], "text", 1):
            with self.subTest(value=value):
                self.assert_refused(self.recover(value), "--recovery-json")


if __name__ == "__main__":
    unittest.main()
