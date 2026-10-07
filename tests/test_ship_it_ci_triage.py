"""Validate ship-it's CI failure triage contract.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
TRIAGE_REFERENCE: Final[Path] = SKILL_DIR / "references" / "ci-triage.md"
TRIAGE_SCHEMA: Final[Path] = SKILL_DIR / "references" / "ci-triage.schema.json"
CHECKPOINT_REFERENCE: Final[Path] = SKILL_DIR / "references" / "checkpoint.md"
EVIDENCE_REFERENCE: Final[Path] = SKILL_DIR / "references" / "evidence.md"
PR_LOOP_REFERENCE: Final[Path] = SKILL_DIR / "references" / "pr-loop.md"
TELEMETRY_REFERENCE: Final[Path] = SKILL_DIR / "references" / "telemetry.md"
TELEMETRY_SCHEMA: Final[Path] = SKILL_DIR / "references" / "telemetry.schema.json"
TELEMETRY_V1_SCHEMA: Final[Path] = (
    SKILL_DIR / "references" / "telemetry-v1.schema.json"
)
RISK_REFERENCE: Final[Path] = SKILL_DIR / "references" / "risk.md"


class ShipItCiTriageContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.guidance = TRIAGE_REFERENCE.read_text(encoding="utf-8")
        self.schema: dict[str, Any] = json.loads(TRIAGE_SCHEMA.read_text(encoding="utf-8"))

    def test_failure_identity_is_exact_and_deduplicated_before_logs(self) -> None:
        required_key = set(self.schema["properties"]["key"]["required"])
        self.assertEqual(required_key, {"revision", "workflow", "job", "attempt"})
        self.assertEqual(
            self.schema["properties"]["failureId"]["pattern"],
            "^cif_[0-9a-f]{64}$",
        )
        for expected in (
            "Before retrieving logs",
            "do not retrieve or send its logs again",
            "Never deduplicate across revisions, workflows, jobs or attempts",
            "reconcile it into the matching evidence result by failure ID",
            "cumulative telemetry snapshot derived from checkpoint records",
        ):
            self.assertIn(expected, self.guidance)
        self.assertTrue(self.schema["additionalProperties"])

    def test_logs_and_classification_are_bounded(self) -> None:
        sections = self.schema["properties"]["logSections"]
        self.assertEqual(sections["maxItems"], 3)
        lines = sections["items"]["properties"]["lines"]
        self.assertEqual(lines["maxItems"], 40)
        self.assertEqual(lines["items"]["maxLength"], 125)
        self.assertLessEqual(len(("😀" * 125).encode("utf-8")), 500)
        self.assertGreater(len(("😀" * 126).encode("utf-8")), 500)
        self.assertEqual(
            set(self.schema["properties"]["classification"]["enum"]),
            {"code", "flaky", "infrastructure", "unknown"},
        )
        self.assertEqual(
            self.schema["properties"]["supportingEvidence"]["minItems"], 1
        )
        self.assertIn("owner-only temporary file", self.guidance)
        self.assertIn("Do not send an entire workflow or job log", self.guidance)

    def test_code_failures_route_acceptance_evidence_to_owner(self) -> None:
        self.assertIn("failedAcceptanceEvidence", self.schema["required"])
        for expected in (
            "route it to the checkpoint's owning implementation role",
            "sets the checkpoint to `phase: implement`",
            "owner, failure ID and failed acceptance evidence",
        ):
            self.assertIn(expected, self.guidance)
        condition = self.schema["allOf"][0]
        self.assertEqual(
            condition["if"]["properties"]["classification"]["const"], "code"
        )
        self.assertEqual(
            condition["then"]["properties"]["failedAcceptanceEvidence"][
                "minItems"
            ],
            1,
        )

    def test_reruns_need_bounded_authorization(self) -> None:
        authorization = self.schema["properties"]["rerunAuthorization"]["oneOf"][1]
        self.assertEqual(
            set(authorization["properties"]["source"]["enum"]),
            {"repository-policy", "explicit-approval"},
        )
        self.assertEqual(authorization["properties"]["maxAttempts"]["minimum"], 1)
        self.assertIn("rerunGroupId", self.schema["required"])
        self.assertIn("rerunsUsed", self.schema["required"])
        self.assertIn("maximum value across the group", self.guidance)
        self.assertIn("prevents each new attempt from resetting the limit", self.guidance)
        risk = RISK_REFERENCE.read_text(encoding="utf-8")
        self.assertIn("ci_reruns", risk)
        self.assertIn("Absence authorizes no reruns", risk)
        self.assertIn("The bundled policy authorizes no reruns", self.guidance)

    def test_recurrence_and_resolution_reach_all_state_stores(self) -> None:
        checkpoint = CHECKPOINT_REFERENCE.read_text(encoding="utf-8")
        evidence = EVIDENCE_REFERENCE.read_text(encoding="utf-8")
        pr_loop = PR_LOOP_REFERENCE.read_text(encoding="utf-8")
        telemetry = TELEMETRY_REFERENCE.read_text(encoding="utf-8")
        telemetry_schema = json.loads(TELEMETRY_SCHEMA.read_text(encoding="utf-8"))
        telemetry_v1_schema = json.loads(
            TELEMETRY_V1_SCHEMA.read_text(encoding="utf-8")
        )

        self.assertIn('"ciTriage"', checkpoint)
        self.assertIn("resolution and recurrence", checkpoint)
        self.assertIn("may lack any subset", checkpoint)
        self.assertIn("including only `ciTriage`", checkpoint)
        self.assertIn('"ciTriage"', evidence)
        self.assertIn("recurrence and resolution history", evidence)
        self.assertIn("schema-v1 legacy record", evidence)
        self.assertIn('ciTriage: {"failureIds": [], "resolution": null}', evidence)
        self.assertIn("[ci-triage.md](ci-triage.md)", pr_loop)
        self.assertIn("Checkpoint, evidence and append-only telemetry", self.guidance)
        self.assertIn("resume from the checkpoint", self.guidance)
        self.assertIn("consumers take the latest value per run", self.guidance)
        for counter in ("ci_failures", "ci_recurrences", "ci_resolutions"):
            with self.subTest(counter=counter):
                self.assertIn(counter, telemetry)
                self.assertIn(
                    counter,
                    telemetry_schema["properties"]["metrics"]["properties"],
                )
                self.assertNotIn(
                    counter,
                    telemetry_v1_schema["properties"]["metrics"]["properties"],
                )
        self.assertEqual(telemetry_schema["properties"]["schema_version"]["const"], 2)
        self.assertEqual(
            telemetry_v1_schema["properties"]["schema_version"]["const"], 1
        )


if __name__ == "__main__":
    unittest.main()
