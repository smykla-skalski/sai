"""Keep the ship-it SKILL.md under the Codex skill prompt limit.

Codex truncates a plugin skill's SKILL.md past MAX_SKILL_PROMPT_BYTES
(openai/codex codex-rs/ext/skills/src/render.rs), hiding later phases.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"
CHECKPOINT_REFERENCE: Final[Path] = SKILL_DIR / "references" / "checkpoint.md"
EVIDENCE_REFERENCE: Final[Path] = SKILL_DIR / "references" / "evidence.md"
CLAIMS_REFERENCE: Final[Path] = SKILL_DIR / "references" / "claims.md"
CODEX_MAX_SKILL_PROMPT_BYTES: Final[int] = 8000
SKILL_BUDGET_BYTES: Final[int] = 6000
REFERENCE_LINK: Final[re.Pattern[str]] = re.compile(r"\]\((references/[^)]+\.md)\)")
CROSS_REF: Final[re.Pattern[str]] = re.compile(r"SKILL\.md|Phase \d")
PHASE_REFERENCE_ROWS: Final[tuple[tuple[str, str], ...]] = (
    ("1 — Resolve", "inputs.md"),
    ("2 — Explore", "explore.md"),
    ("3 — Branch", "branch.md"),
    ("4 — Implement", "implementation.md"),
    ("5 — Review", "review.md"),
    ("6 — Test", "test.md"),
    ("7–10 — PR loop", "pr-loop.md"),
    ("11 — Complete", "completion.md"),
)
PHASE_REFERENCE_ROW: Final[re.Pattern[str]] = re.compile(
    r"^\| (?P<phase>[^|]+?) \| "
    r"\[references/(?P<reference>[^]]+\.md)\]"
    r"\(references/(?P=reference)\) \|$",
    re.MULTILINE,
)


class ShipItSkillSizeTest(unittest.TestCase):
    def test_skill_fits_codex_prompt_limit(self) -> None:
        size = len(SKILL_FILE.read_bytes())
        self.assertLessEqual(
            size,
            CODEX_MAX_SKILL_PROMPT_BYTES,
            f"{SKILL_FILE} is {size} bytes; Codex truncates it",
        )
        self.assertLessEqual(
            size,
            SKILL_BUDGET_BYTES,
            f"{SKILL_FILE} is {size} bytes; move detail into references/",
        )

    def test_linked_references_exist_and_stand_alone(self) -> None:
        links = REFERENCE_LINK.findall(SKILL_FILE.read_text(encoding="utf-8"))
        self.assertTrue(links, "SKILL.md links no references")
        for link in sorted(set(links)):
            with self.subTest(reference=link):
                path = SKILL_DIR / link
                self.assertTrue(path.is_file(), f"missing {path}")
                self.assertIsNone(
                    CROSS_REF.search(path.read_text(encoding="utf-8")),
                    f"{link} must not cross-reference SKILL.md or its phases",
                )

    def test_every_phase_loads_its_guidance_on_demand(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        phase_index = skill.split("## Phase reference index", 1)[1].split("\n## ", 1)[0]
        actual_rows = tuple(
            (match["phase"], match["reference"])
            for match in PHASE_REFERENCE_ROW.finditer(phase_index)
        )
        self.assertEqual(actual_rows, PHASE_REFERENCE_ROWS)

        for _, reference in PHASE_REFERENCE_ROWS:
            with self.subTest(reference=reference):
                link = f"[references/{reference}](references/{reference})"
                self.assertEqual(
                    skill.count(link),
                    1,
                    f"{reference} must appear once in the phase reference index",
                )

    def test_checkpoint_contract_is_portable_and_recoverable(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        checkpoint = CHECKPOINT_REFERENCE.read_text(encoding="utf-8")

        self.assertEqual(
            skill.count("[references/checkpoint.md](references/checkpoint.md)"),
            1,
        )
        for expected in (
            "${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/checkpoints/",
            '"schemaVersion": 1',
            '"acceptanceCriteria"',
            '"unresolvedQuestions"',
            '"nextAction"',
            '"pullRequestHead"',
            '"orchestration": null',
            '"outcome": null',
            "Reconcile Git before edits",
            "known legacy shape",
            "may lack any subset of `risk`, `claim` and `ciTriage`",
            "Invalid JSON",
            "Different canonical source or repository identity",
            "status: completed",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, checkpoint)

        example_match = re.search(r"```json\n(?P<document>.*?)\n```", checkpoint, re.DOTALL)
        self.assertIsNotNone(example_match)
        example = json.loads(example_match["document"])
        self.assertEqual(example["schemaVersion"], 1)
        self.assertEqual(example["workflow"]["phase"].split("|")[-1], "complete")

    def test_every_execution_phase_updates_the_checkpoint(self) -> None:
        for reference in (
            "explore.md",
            "branch.md",
            "implementation.md",
            "review.md",
            "test.md",
            "pr-loop.md",
            "completion.md",
            "orchestration.md",
        ):
            with self.subTest(reference=reference):
                content = (SKILL_DIR / "references" / reference).read_text(
                    encoding="utf-8"
                )
                self.assertIn("checkpoint", content.lower())

    def test_github_claim_contract_is_visible_expiring_and_auditable(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        claims = CLAIMS_REFERENCE.read_text(encoding="utf-8")
        checkpoint = CHECKPOINT_REFERENCE.read_text(encoding="utf-8")
        evidence = EVIDENCE_REFERENCE.read_text(encoding="utf-8")

        self.assertEqual(
            skill.count("[references/claims.md](references/claims.md)"),
            1,
        )
        for expected in (
            "<!-- sai:ship-it-claim:v1 -->",
            '"holder"',
            '"acquiredAt"',
            '"renewedAt"',
            '"expiresAt"',
            "30-minute lease",
            "lowest numeric GitHub comment database ID",
            "status: pending",
            "release its own duplicates",
            "previousCommentUrl",
            "openPullRequestsChecked",
            "recentMergesChecked",
            "lost acquisition race",
            "terminal failure",
            "pending after claim takeover",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, claims)

        self.assertIn('"claim": null', checkpoint)
        self.assertIn('"claim": null', evidence)
        self.assertIn("authoritative issue comment", checkpoint)
        self.assertIn('"status": "active|blocked|completed|cancelled|failed"', checkpoint)
        self.assertIn("explicit restart instruction", checkpoint)
        self.assertIn("active, unexpired", evidence)

    def test_completion_evidence_is_revision_bound_and_portable(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        evidence = EVIDENCE_REFERENCE.read_text(encoding="utf-8")
        checkpoint = CHECKPOINT_REFERENCE.read_text(encoding="utf-8")

        self.assertEqual(
            skill.count("[references/evidence.md](references/evidence.md)"),
            1,
        )
        for expected in (
            "${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/evidence/<checkpoint-id>/",
            '"sourceRevision"',
            '"provider"',
            '"model"',
            '"requiredBy"',
            '"timestamp"',
            '"outputReference"',
            "acceptance-criterion",
            "local-check",
            '"review"',
            "manual-test",
            '"ci"',
            "Missing, pending, failed, blocked or stale required evidence",
            "non-stale current record",
            "its `headRefOid`",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, evidence)

        example_match = re.search(r"```json\n(?P<document>.*?)\n```", evidence, re.DOTALL)
        self.assertIsNotNone(example_match)
        example = json.loads(example_match["document"])
        self.assertEqual(example["schemaVersion"], 1)
        self.assertEqual(example["status"], "complete")
        self.assertEqual(
            {result["category"] for result in example["results"]},
            {"acceptance-criterion", "local-check", "review", "manual-test", "ci"},
        )
        for result in example["results"]:
            self.assertTrue(result["required"])
            self.assertEqual(result["status"], "passed")
            self.assertIn(result["requiredBy"], {"pr", "merge"})
            for field in (
                "sourceRevision",
                "provider",
                "model",
                "timestamp",
                "outputReference",
            ):
                self.assertIn(field, result)

        self.assertIn('"evidence": {', checkpoint)
        self.assertIn('"recordPath"', checkpoint)
        self.assertIn('"risk": {', checkpoint)
        self.assertIn('"requiredGates"', checkpoint)

    def test_evidence_gates_every_revision_sensitive_phase(self) -> None:
        expectations = {
            "implementation.md": (
                "mark the previous record stale",
                "run every selected local gate against the committed revision",
            ),
            "review.md": (
                "provider, model, timestamp and bounded output reference",
                "any later source change marks the entire record stale",
            ),
            "test.md": (
                "provider, model, timestamp and bounded output reference",
                "reproduced failure marks the evidence failed",
            ),
            "pr-loop.md": (
                "requiredby: pr",
                "requiredby: merge",
                "local `head` and the pr `headrefoid`",
            ),
            "completion.md": ("complete record for the gated pr head",),
            "orchestration.md": (
                "evidence record is complete for the final pr head",
            ),
        }
        for reference, required_text in expectations.items():
            with self.subTest(reference=reference):
                content = (SKILL_DIR / "references" / reference).read_text(
                    encoding="utf-8"
                ).lower()
                for expected in required_text:
                    self.assertIn(expected, content)


if __name__ == "__main__":
    unittest.main()
