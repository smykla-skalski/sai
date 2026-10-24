"""Exercise the CI triage state commands through the real bookkeeping CLI.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Final

from test_ship_it_bookkeeping import SCRIPT, checkpoint_document, checkpoint_path
from test_ship_it_ci_triage_validator import VALIDATOR

SKILL: Final[Path] = Path(__file__).resolve().parent.parent / (
    "plugins/ship-it/skills/ship-it"
)
AUTHORIZATION: Final[dict[str, Any]] = {
    "source": "explicit-approval",
    "reference": "user approved two reruns of build/test",
    "maxAttempts": 2,
    "authorizedAt": "2026-10-07T09:00:00Z",
}


def make_record(attempt: int = 1, **overrides: object) -> dict[str, Any]:
    key = {
        "revision": "a" * 40,
        "workflow": "build",
        "job": "test",
        "attempt": attempt,
    }
    group = {name: key[name] for name in ("job", "revision", "workflow")}
    value: dict[str, Any] = {
        "schemaVersion": 1,
        "failureId": VALIDATOR.digest("cif_", key),
        "key": key,
        "recurrenceKey": None,
        "recurrenceOf": None,
        "recurrenceCount": 0,
        "rerunGroupId": VALIDATOR.digest("cig_", group),
        "rerunsUsed": 0,
        "rerunRequest": None,
        "classification": "flaky",
        "status": "open",
        "supportingEvidence": ["same job passed on this revision"],
        "logSections": [{"label": "failing command", "lines": ["make test"]}],
        "failedAcceptanceEvidence": [],
        "rerunAuthorization": dict(AUTHORIZATION),
        "resolution": None,
        "nextAction": "rerun once",
        "firstObservedAt": "2026-10-07T09:00:00Z",
        "lastObservedAt": "2026-10-07T09:00:00Z",
    }
    return {**value, **overrides}


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class CiTriageStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.document = checkpoint_document()
        self.path = checkpoint_path(self.directory.name, self.document)
        self.write(self.document)
        self.group = make_record()["rerunGroupId"]

    def write(self, document: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def failures(self) -> list[dict[str, Any]]:
        return self.read()["ciTriage"]["failures"]

    def command(self, name: str, option: str, value: object) -> dict[str, Any]:
        result = run(name, "--checkpoint", str(self.path), option, json.dumps(value))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def record(self, record: dict[str, Any]) -> dict[str, Any]:
        return self.command("record-ci-failure", "--failure-json", record)

    def request(self, recorded_at: str | None = None) -> dict[str, Any]:
        value = {"rerunGroupId": self.group}
        if recorded_at is not None:
            value["recordedAt"] = recorded_at
        return self.command("request-ci-rerun", "--request-json", value)

    def settle(self, outcome: str) -> dict[str, Any]:
        return self.command(
            "settle-ci-rerun",
            "--settlement-json",
            {"rerunGroupId": self.group, "outcome": outcome},
        )

    def refused(self, name: str, option: str, value: object, text: str) -> None:
        before = self.path.read_bytes()
        result = run(name, "--checkpoint", str(self.path), option, json.dumps(value))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(text, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)

    def test_record_appends_and_leaves_other_state_untouched(self) -> None:
        result = self.record(make_record())
        self.assertEqual(result["recorded"], "created")
        self.assertEqual(self.failures(), [make_record()])
        after = self.read()
        for key in ("workflow", "task", "gateVerdicts"):
            self.assertEqual(after[key], self.document[key], key)

    def test_recording_the_same_failure_replaces_it_and_keeps_first_seen(self) -> None:
        self.record(make_record())
        later = make_record(
            lastObservedAt="2026-10-07T10:00:00Z",
            firstObservedAt="2026-10-07T10:00:00Z",
            nextAction="wait for the rerun",
        )
        self.assertEqual(self.record(later)["recorded"], "updated")
        (stored,) = self.failures()
        self.assertEqual(stored["nextAction"], "wait for the rerun")
        self.assertEqual(stored["firstObservedAt"], "2026-10-07T09:00:00Z")
        self.assertEqual(stored["lastObservedAt"], "2026-10-07T10:00:00Z")

    def test_resolved_failure_is_kept_and_never_reopened(self) -> None:
        self.record(make_record())
        resolved = make_record(
            status="resolved",
            resolution={
                "kind": "provider-recovered",
                "evidence": "provider status page reports recovery",
                "resolvedAt": "2026-10-07T11:00:00Z",
            },
        )
        self.record(resolved)
        self.assertEqual(self.failures()[0]["status"], "resolved")
        self.refused(
            "record-ci-failure",
            "--failure-json",
            make_record(),
            "stays resolved",
        )

    def test_invalid_records_are_refused_without_writing(self) -> None:
        missing = make_record()
        del missing["nextAction"]
        for name, value, text in (
            ("missing field", missing, "missing required fields: nextAction"),
            (
                "classification",
                make_record(classification="bug"),
                "classification must be one of",
            ),
            ("status", make_record(status=[]), "status must be one of"),
            (
                "failure id",
                make_record(failureId="cif_" + "0" * 64),
                "failureId does not match",
            ),
            (
                "code without evidence",
                make_record(classification="code"),
                "failed acceptance evidence",
            ),
            (
                "no supporting evidence",
                make_record(supportingEvidence=[]),
                "supportingEvidence",
            ),
            (
                "too many log lines",
                make_record(logSections=[{"label": "x", "lines": ["a"] * 41}]),
                "logSections[0]",
            ),
            (
                "long log line",
                make_record(logSections=[{"label": "x", "lines": ["a" * 126]}]),
                "logSections[0]",
            ),
            (
                "timestamp",
                make_record(lastObservedAt="yesterday"),
                "lastObservedAt must be an RFC 3339 UTC timestamp",
            ),
            (
                "authorization",
                make_record(rerunAuthorization={"maxAttempts": 1}),
                "rerunAuthorization needs",
            ),
            (
                "resolved without resolution",
                make_record(status="resolved"),
                "resolved status requires a resolution",
            ),
        ):
            with self.subTest(name=name):
                self.refused("record-ci-failure", "--failure-json", value, text)

    def test_records_must_meet_the_schema_bounds(self) -> None:
        key = make_record()["key"]
        for name, value, text in (
            ("revision", make_record(key={**key, "revision": "main"}), "key needs"),
            (
                "workflow length",
                make_record(key={**key, "workflow": "w" * 201}),
                "key needs",
            ),
            ("extra key field", make_record(key={**key, "extra": 1}), "key needs"),
            ("recurrence key", make_record(recurrenceKey="junk"), "recurrenceKey"),
            ("recurrence key type", make_record(recurrenceKey=5), "recurrenceKey"),
            ("recurrence of", make_record(recurrenceOf="x"), "recurrenceOf"),
            ("acceptance string", make_record(failedAcceptanceEvidence="a"), "failed"),
            ("acceptance int", make_record(failedAcceptanceEvidence=5), "failed"),
            (
                "acceptance count",
                make_record(failedAcceptanceEvidence=["a"] * 21),
                "failedAcceptanceEvidence needs 0 to 20",
            ),
            (
                "acceptance length",
                make_record(failedAcceptanceEvidence=["a" * 513]),
                "failedAcceptanceEvidence needs 0 to 20",
            ),
            (
                "authorization extra",
                make_record(rerunAuthorization={**AUTHORIZATION, "extra": 1}),
                "rerunAuthorization needs exactly",
            ),
            (
                "authorization limit",
                make_record(rerunAuthorization={**AUTHORIZATION, "maxAttempts": 0}),
                "rerunAuthorization needs exactly",
            ),
            (
                "section extra",
                make_record(logSections=[{"label": "x", "lines": [], "extra": 1}]),
                "logSections[0] needs exactly",
            ),
            (
                "basic timestamp",
                make_record(lastObservedAt="20261007T090000Z"),
                "lastObservedAt must be an RFC 3339 UTC timestamp",
            ),
            (
                "timestamp without seconds",
                make_record(lastObservedAt="2026-10-07T09:00Z"),
                "lastObservedAt must be an RFC 3339 UTC timestamp",
            ),
            ("recurrence count", make_record(recurrenceCount=-1), "recurrenceCount"),
        ):
            with self.subTest(name=name):
                self.refused("record-ci-failure", "--failure-json", value, text)

    def test_unencodable_text_is_a_usage_error_not_a_crash(self) -> None:
        for name, value, text in (
            ("next action", make_record(nextAction="\ud800"), "nextAction"),
            (
                "supporting evidence",
                make_record(supportingEvidence=["\ud800"]),
                "supportingEvidence",
            ),
            (
                "section label",
                make_record(logSections=[{"label": "\ud800", "lines": []}]),
                "logSections[0]",
            ),
            (
                "authorization reference",
                make_record(
                    rerunAuthorization={**AUTHORIZATION, "reference": "\ud800"},
                ),
                "rerunAuthorization",
            ),
        ):
            with self.subTest(name=name):
                self.refused("record-ci-failure", "--failure-json", value, text)

    def test_a_new_group_cannot_start_with_spent_reruns(self) -> None:
        for name, value in (
            ("used", make_record(rerunsUsed=1)),
            (
                "request",
                make_record(
                    rerunRequest={
                        "requestedAttempt": 1,
                        "recordedAt": "2026-10-07T09:00:00Z",
                    },
                ),
            ),
        ):
            with self.subTest(name=name):
                self.refused(
                    "record-ci-failure",
                    "--failure-json",
                    value,
                    "new rerun group starts with rerunsUsed 0",
                )

    def test_rerun_cycle_spends_budget_only_when_accepted(self) -> None:
        self.record(make_record())
        pending = self.request("2026-10-07T09:30:00Z")
        self.assertEqual(pending["requestedAttempt"], 1)
        self.assertEqual(
            self.failures()[0]["rerunRequest"],
            {"requestedAttempt": 1, "recordedAt": "2026-10-07T09:30:00Z"},
        )
        self.assertEqual(self.settle("not-accepted")["rerunsUsed"], 0)
        self.assertIsNone(self.failures()[0]["rerunRequest"])

        self.assertEqual(self.request()["requestedAttempt"], 1)
        self.assertEqual(self.settle("accepted")["rerunsUsed"], 1)
        self.assertEqual(self.failures()[0]["rerunsUsed"], 1)
        self.assertIsNone(self.failures()[0]["rerunRequest"])

        self.assertEqual(self.request()["requestedAttempt"], 2)
        self.assertEqual(self.settle("accepted")["rerunsUsed"], 2)
        self.refused(
            "request-ci-rerun",
            "--request-json",
            {"rerunGroupId": self.group},
            "rerun budget exhausted: 2 of 2 used",
        )

    def test_a_new_attempt_inherits_the_group_state(self) -> None:
        self.record(make_record())
        self.request()
        self.settle("accepted")
        self.record(make_record(attempt=2, rerunAuthorization=None))
        first, second = self.failures()
        self.assertEqual(first["rerunsUsed"], 1)
        self.assertEqual(second["rerunsUsed"], 1)
        self.assertEqual(second["rerunAuthorization"], AUTHORIZATION)
        self.request()
        self.assertEqual(
            [f["rerunRequest"]["requestedAttempt"] for f in self.failures()],
            [2, 2],
        )
        self.record(make_record(attempt=2, rerunsUsed=0, rerunRequest=None))
        self.assertEqual(self.failures()[1]["rerunsUsed"], 1)
        self.assertEqual(self.failures()[1]["rerunRequest"]["requestedAttempt"], 2)
        self.settle("accepted")
        self.assertEqual({f["rerunsUsed"] for f in self.failures()}, {2})

    def test_rerun_requests_are_refused_without_authority_or_when_pending(self) -> None:
        self.record(make_record(rerunAuthorization=None))
        self.refused(
            "request-ci-rerun",
            "--request-json",
            {"rerunGroupId": self.group},
            "needs rerunAuthorization",
        )
        self.refused(
            "request-ci-rerun",
            "--request-json",
            {"rerunGroupId": "cig_" + "0" * 64},
            "no failure is recorded",
        )
        self.record(make_record())
        self.request()
        self.refused(
            "request-ci-rerun",
            "--request-json",
            {"rerunGroupId": self.group},
            "already pending",
        )

    def test_request_keeps_each_valid_authorization_and_fills_the_rest(self) -> None:
        first_approval = {**AUTHORIZATION, "reference": "first approval"}
        self.record(make_record(rerunAuthorization=first_approval))
        self.record(
            make_record(
                status="resolved",
                resolution={
                    "kind": "provider-recovered",
                    "evidence": "provider recovered",
                    "resolvedAt": "2026-10-07T11:00:00Z",
                },
                rerunAuthorization=first_approval,
            ),
        )
        second = {**AUTHORIZATION, "reference": "second approval", "maxAttempts": 3}
        self.record(make_record(attempt=2, rerunAuthorization=second))
        self.request()
        first, latest = self.failures()
        self.assertEqual(first["rerunAuthorization"], first_approval)
        self.assertEqual(latest["rerunAuthorization"], second)

    def test_request_gives_a_record_that_cannot_cover_it_the_latest_authorization(
        self,
    ) -> None:
        self.record(make_record(rerunAuthorization={**AUTHORIZATION, "maxAttempts": 1}))
        self.request()
        self.settle("accepted")
        second = {**AUTHORIZATION, "reference": "second approval", "maxAttempts": 3}
        self.record(make_record(attempt=2, rerunAuthorization=second))
        self.request()
        first, latest = self.failures()
        self.assertEqual(first["rerunAuthorization"], second)
        self.assertEqual(latest["rerunAuthorization"], second)

    def test_present_but_falsy_recorded_at_is_refused(self) -> None:
        self.record(make_record())
        value: object
        for value in ("", 0, False, []):
            with self.subTest(value=value):
                self.refused(
                    "request-ci-rerun",
                    "--request-json",
                    {"rerunGroupId": self.group, "recordedAt": value},
                    "RFC 3339 UTC",
                )

    def test_resolved_group_cannot_be_rerun(self) -> None:
        self.record(make_record())
        self.record(
            make_record(
                status="resolved",
                resolution={
                    "kind": "superseded-by-revision",
                    "evidence": "fixed in a newer revision",
                    "resolvedAt": "2026-10-07T11:00:00Z",
                },
            ),
        )
        self.refused(
            "request-ci-rerun",
            "--request-json",
            {"rerunGroupId": self.group},
            "latest failure of this rerun group is resolved",
        )

    def test_settlement_needs_a_pending_request_and_a_known_outcome(self) -> None:
        self.record(make_record())
        self.refused(
            "settle-ci-rerun",
            "--settlement-json",
            {"rerunGroupId": self.group, "outcome": "accepted"},
            "no rerun request is pending",
        )
        self.request()
        for value in (
            {"rerunGroupId": self.group, "outcome": "maybe"},
            {"rerunGroupId": self.group},
            {"rerunGroupId": self.group, "outcome": []},
        ):
            with self.subTest(value=value):
                self.refused(
                    "settle-ci-rerun",
                    "--settlement-json",
                    value,
                    "outcome accepted|not-accepted",
                )

    def test_request_rejects_unknown_fields_and_bad_timestamps(self) -> None:
        self.record(make_record())
        for value, text in (
            ({"rerunGroupId": self.group, "extra": 1}, "takes rerunGroupId"),
            ({}, "takes rerunGroupId"),
            (
                {"rerunGroupId": self.group, "recordedAt": "2026-10-07T09:00:00+02:00"},
                "RFC 3339 UTC",
            ),
        ):
            with self.subTest(value=value):
                self.refused("request-ci-rerun", "--request-json", value, text)

    def test_invalid_stored_state_is_never_extended(self) -> None:
        self.document["ciTriage"] = {"failures": [make_record(rerunsUsed=1)]}
        self.document["ciTriage"]["failures"][0]["rerunAuthorization"] = None
        self.write(self.document)
        self.refused(
            "record-ci-failure",
            "--failure-json",
            make_record(attempt=2),
            "stored ciTriage is invalid",
        )

    def test_non_object_values_are_usage_errors(self) -> None:
        for name, option in (
            ("record-ci-failure", "--failure-json"),
            ("request-ci-rerun", "--request-json"),
            ("settle-ci-rerun", "--settlement-json"),
        ):
            with self.subTest(name=name):
                result = run(name, "--checkpoint", str(self.path), option, "[1]")
                self.assertEqual(result.returncode, 2)
                self.assertIn("must contain an object", result.stderr)


class CiTriageContractTest(unittest.TestCase):
    def test_required_fields_match_the_schema(self) -> None:
        schema = json.loads(
            (SKILL / "references/ci-triage.schema.json").read_text(encoding="utf-8"),
        )
        self.assertEqual(set(VALIDATOR.REQUIRED_FIELDS), set(schema["required"]))
        properties = schema["properties"]
        self.assertEqual(
            set(VALIDATOR.CLASSIFICATIONS),
            set(properties["classification"]["enum"]),
        )
        self.assertEqual(set(VALIDATOR.STATUSES), set(properties["status"]["enum"]))

    def test_guidance_names_the_commands_and_the_helper_bundle(self) -> None:
        guidance = (SKILL / "references/ci-triage.md").read_text(encoding="utf-8")
        checkpoint = (SKILL / "references/checkpoint.md").read_text(encoding="utf-8")
        loading = (SKILL / "references/helper-loading.md").read_text(encoding="utf-8")
        for command in ("record-ci-failure", "request-ci-rerun", "settle-ci-rerun"):
            with self.subTest(command=command):
                self.assertIn(f"bookkeeping.py {command}", guidance)
                self.assertIn(f"bookkeeping.py {command}", checkpoint)
        bookkeeping_row = next(
            line
            for line in loading.splitlines()
            if line.startswith("| `scripts/bookkeeping.py`")
        )
        self.assertIn("`scripts/ci_triage.py`", bookkeeping_row)


if __name__ == "__main__":
    unittest.main()
