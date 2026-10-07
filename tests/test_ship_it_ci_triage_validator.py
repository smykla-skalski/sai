"""Behavior tests for the ship-it CI triage semantic validator.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT: Final[Path] = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "ship-it"
    / "skills"
    / "ship-it"
    / "scripts"
    / "ci_triage.py"
)


def load_validator() -> ModuleType:
    """Load the validator without modifying the import path."""
    spec = importlib.util.spec_from_file_location("ci_triage", SCRIPT)
    if spec is None or spec.loader is None:
        message = "cannot load ci_triage validator"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator()


def record() -> dict[str, Any]:
    """Return one semantically valid open code-failure record."""
    key = {
        "revision": "a" * 40,
        "workflow": "build",
        "job": "test",
        "attempt": 1,
    }
    group = {name: key[name] for name in ("job", "revision", "workflow")}
    return {
        "schemaVersion": 1,
        "failureId": VALIDATOR.digest("cif_", key),
        "key": key,
        "recurrenceKey": None,
        "recurrenceOf": None,
        "recurrenceCount": 0,
        "rerunGroupId": VALIDATOR.digest("cig_", group),
        "rerunsUsed": 0,
        "rerunRequest": None,
        "classification": "code",
        "status": "open",
        "supportingEvidence": ["test failed"],
        "logSections": [],
        "failedAcceptanceEvidence": ["AC1 failed"],
        "rerunAuthorization": None,
        "resolution": None,
        "nextAction": "return to owner",
        "firstObservedAt": "2026-10-07T09:00:00Z",
        "lastObservedAt": "2026-10-07T09:00:00Z",
    }


class ShipItCiTriageValidatorTest(unittest.TestCase):
    def test_valid_record_passes(self) -> None:
        self.assertEqual(VALIDATOR.validate_record(record()), [])
        self.assertEqual(VALIDATOR.validate({"failures": [record()]}), [])

    def test_identity_hashes_are_bound_to_keys(self) -> None:
        value = record()
        value["failureId"] = "cif_" + "0" * 64
        value["rerunGroupId"] = "cig_" + "b" * 64
        self.assertEqual(
            VALIDATOR.validate_record(value),
            [
                "failureId does not match the canonical key",
                "rerunGroupId does not match revision, workflow and job",
            ],
        )

    def test_rerun_usage_needs_authorization_and_stays_within_limit(self) -> None:
        value = record()
        value["classification"] = "infrastructure"
        value["failedAcceptanceEvidence"] = []
        value["rerunsUsed"] = 1
        self.assertIn(
            "rerunsUsed requires rerunAuthorization",
            VALIDATOR.validate_record(value),
        )

        value["rerunsUsed"] = 2
        value["rerunAuthorization"] = {
            "source": "explicit-approval",
            "reference": "approved once",
            "maxAttempts": 1,
            "authorizedAt": "2026-10-07T09:00:00Z",
        }
        self.assertIn(
            "rerunsUsed exceeds the authorized maximum",
            VALIDATOR.validate_record(value),
        )

    def test_recurrence_cannot_refer_to_itself(self) -> None:
        value = record()
        value["classification"] = "unknown"
        value["failedAcceptanceEvidence"] = []
        value["recurrenceKey"] = "cir_" + "c" * 64
        value["recurrenceOf"] = value["failureId"]
        value["recurrenceCount"] = 1
        self.assertIn(
            "recurrenceOf cannot refer to the same failureId",
            VALIDATOR.validate_record(value),
        )

    def test_utf8_byte_limit_is_enforced(self) -> None:
        value = record()
        value["logSections"] = [{"label": "error", "lines": ["😀" * 126]}]
        self.assertIn(
            "exceeds 500 UTF-8 bytes",
            " ".join(VALIDATOR.validate_record(value)),
        )

    def test_group_usage_cannot_reset_on_a_new_attempt(self) -> None:
        first = record()
        first["classification"] = "infrastructure"
        first["failedAcceptanceEvidence"] = []
        first["rerunsUsed"] = 1
        first["rerunAuthorization"] = {
            "source": "explicit-approval",
            "reference": "approved once",
            "maxAttempts": 1,
            "authorizedAt": "2026-10-07T09:00:00Z",
        }
        second = json.loads(json.dumps(first))
        second["key"]["attempt"] = 2
        second["failureId"] = VALIDATOR.digest("cif_", second["key"])
        second["rerunsUsed"] = 0
        second["rerunAuthorization"] = None
        self.assertIn(
            "inconsistent rerunsUsed",
            " ".join(VALIDATOR.validate({"failures": [first, second]})),
        )

    def test_pending_rerun_is_durable_and_group_consistent(self) -> None:
        first = record()
        first["classification"] = "infrastructure"
        first["failedAcceptanceEvidence"] = []
        first["rerunAuthorization"] = {
            "source": "explicit-approval",
            "reference": "approved once",
            "maxAttempts": 1,
            "authorizedAt": "2026-10-07T09:00:00Z",
        }
        first["rerunRequest"] = {
            "requestedAttempt": 1,
            "recordedAt": "2026-10-07T09:01:00Z",
        }
        self.assertEqual(VALIDATOR.validate({"failures": [first]}), [])

        second = json.loads(json.dumps(first))
        second["key"]["attempt"] = 2
        second["failureId"] = VALIDATOR.digest("cif_", second["key"])
        second["rerunRequest"] = None
        self.assertIn(
            "inconsistent rerunRequest",
            " ".join(VALIDATOR.validate({"failures": [first, second]})),
        )

        first["rerunsUsed"] = 1
        first["rerunRequest"]["requestedAttempt"] = 2
        self.assertIn(
            "rerunRequest exceeds the authorized maximum",
            VALIDATOR.validate_record(first),
        )

    def test_recurrence_target_must_be_same_identity_and_sequential(self) -> None:
        first = record()
        first["classification"] = "unknown"
        first["failedAcceptanceEvidence"] = []
        first["recurrenceKey"] = "cir_" + "c" * 64
        second = json.loads(json.dumps(first))
        second["key"]["attempt"] = 2
        second["failureId"] = VALIDATOR.digest("cif_", second["key"])
        second["recurrenceOf"] = first["failureId"]
        second["recurrenceCount"] = 1
        self.assertEqual(VALIDATOR.validate({"failures": [first, second]}), [])

        second["recurrenceCount"] = 3
        self.assertIn(
            "recurrenceCount is not sequential",
            " ".join(VALIDATOR.validate({"failures": [first, second]})),
        )

        second["recurrenceCount"] = 1
        second["recurrenceKey"] = "cir_" + "d" * 64
        self.assertIn(
            "recurrence target key differs",
            " ".join(VALIDATOR.validate({"failures": [first, second]})),
        )

    def test_recurrence_targets_most_recent_matching_attempt(self) -> None:
        first = record()
        first["classification"] = "unknown"
        first["failedAcceptanceEvidence"] = []
        first["recurrenceKey"] = "cir_" + "c" * 64
        second = json.loads(json.dumps(first))
        second["key"]["attempt"] = 2
        second["failureId"] = VALIDATOR.digest("cif_", second["key"])
        second["recurrenceOf"] = first["failureId"]
        second["recurrenceCount"] = 1
        third = json.loads(json.dumps(second))
        third["key"]["attempt"] = 3
        third["failureId"] = VALIDATOR.digest("cif_", third["key"])
        third["recurrenceOf"] = first["failureId"]
        self.assertIn(
            "recurrence target is not most recent",
            " ".join(VALIDATOR.validate({"failures": [first, second, third]})),
        )

    def test_surrogate_is_reported_without_crashing(self) -> None:
        value = record()
        value["logSections"] = [{"label": "error", "lines": ["\ud800"]}]
        self.assertIn(
            "contains a non-scalar Unicode surrogate",
            " ".join(VALIDATOR.validate_record(value)),
        )

    def test_identity_surrogate_is_reported_without_crashing(self) -> None:
        value = record()
        value["key"]["workflow"] = "\ud800"
        self.assertIn(
            "identity fields contain non-scalar Unicode: workflow",
            VALIDATOR.validate_record(value),
        )

    def test_cli_returns_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text(json.dumps({"failures": [record()]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {"errors": [], "valid": True})


if __name__ == "__main__":
    unittest.main()
