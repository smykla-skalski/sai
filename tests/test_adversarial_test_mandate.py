"""Keep the adversarial-test Claude agent and its portable mandate in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "adversarial-test"
AGENT_FILE = PLUGIN_DIR / "agents" / "test-adversary.md"
MANDATE_FILE = (
    PLUGIN_DIR / "skills" / "adversarial-test" / "references" / "test-adversary.md"
)
WORKFLOW_FILE = (
    PLUGIN_DIR / "skills" / "adversarial-test" / "references" / "workflow.md"
)
SHIP_IT_REFERENCES = PLUGIN_DIR.parent / "ship-it" / "skills" / "ship-it" / "references"
SHIP_IT_TEST_GATE = SHIP_IT_REFERENCES / "test.md"
SHIP_IT_EVIDENCE = SHIP_IT_REFERENCES / "evidence.md"
SHIP_IT_PR_LOOP = SHIP_IT_REFERENCES / "pr-loop.md"
FRONTMATTER_FENCE = "---\n"
VERDICT_LINE = "TEST_ADVERSARY_VERDICT: <PASS | PASS (partial) | FAIL (N) | BLOCKED>"
VERDICTS = ("PASS", "PASS (partial)", "FAIL", "BLOCKED")
UNTESTED_STATUS_LIST = "A result status is `pending`, `passed`, `untested`, `failed`, `blocked` or `stale`."
UNTESTED_RECORDING_RULE = "`ac-<n>` result as `untested`"
UNTESTED_PR_SECTION = "## Untested criteria"


def strip_frontmatter(text: str) -> str:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    return text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")


class MandateSyncTest(unittest.TestCase):
    def test_agent_body_matches_reference_mandate(self) -> None:
        agent_body = strip_frontmatter(AGENT_FILE.read_text(encoding="utf-8"))
        mandate = MANDATE_FILE.read_text(encoding="utf-8")
        self.assertEqual(
            agent_body,
            mandate,
            f"edit {AGENT_FILE.name} body and {MANDATE_FILE} together",
        )

    def test_agent_frontmatter_names_test_adversary(self) -> None:
        head = AGENT_FILE.read_text(encoding="utf-8").split("\n", 2)[1]
        self.assertEqual(head, "name: test-adversary")


class VerdictVocabularyTest(unittest.TestCase):
    """The tester's verdicts and what the callers parse must stay in step."""

    def test_mandate_lists_every_verdict(self) -> None:
        self.assertIn(VERDICT_LINE, MANDATE_FILE.read_text(encoding="utf-8"))

    def test_callers_accept_every_verdict(self) -> None:
        for path in (WORKFLOW_FILE, SHIP_IT_TEST_GATE):
            text = path.read_text(encoding="utf-8")
            for verdict in VERDICTS:
                pattern = rf"Test Verdict: {re.escape(verdict)}(?!\w| \()"
                with self.subTest(file=path.name, verdict=verdict):
                    self.assertRegex(text, pattern)


class UntestedCriterionEvidenceTest(unittest.TestCase):
    """A PASS (partial) verdict needs an evidence state the PR gate accepts."""

    def test_evidence_contract_has_untested_result_state(self) -> None:
        evidence = SHIP_IT_EVIDENCE.read_text(encoding="utf-8")
        self.assertIn(UNTESTED_STATUS_LIST, evidence)
        self.assertIn("`PASS (partial)`", evidence)
        self.assertIn(UNTESTED_PR_SECTION, evidence)

    def test_test_gate_records_untested_criteria(self) -> None:
        gate = SHIP_IT_TEST_GATE.read_text(encoding="utf-8")
        self.assertIn(UNTESTED_RECORDING_RULE, gate)

    def test_pr_loop_lists_untested_criteria(self) -> None:
        pr_loop = SHIP_IT_PR_LOOP.read_text(encoding="utf-8")
        self.assertIn(UNTESTED_PR_SECTION, pr_loop)
        self.assertIn("`untested`", pr_loop)

    def test_partial_pass_survives_evidence_recovery(self) -> None:
        evidence = SHIP_IT_EVIDENCE.read_text(encoding="utf-8")
        self.assertIn(
            "`passed` or `untested` evidence valid under the partial-pass rule",
            evidence,
        )
        self.assertNotIn("complete record contains non-passing evidence", evidence)

    def test_tester_noncompliance_is_not_blocked(self) -> None:
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        gate = SHIP_IT_TEST_GATE.read_text(encoding="utf-8")
        self.assertIn("run the inline fallback", workflow)
        self.assertIn("only for a product precondition", gate)
        self.assertNotIn("tester twice declined", workflow)
        self.assertNotIn("tester that twice declined", gate)

    def test_partial_pass_pr_body_is_verified_after_creation(self) -> None:
        evidence = SHIP_IT_EVIDENCE.read_text(encoding="utf-8")
        pr_loop = SHIP_IT_PR_LOOP.read_text(encoding="utf-8")
        self.assertIn("PR-body state is not a prerequisite", evidence)
        self.assertIn("Read the created PR body back from GitHub", pr_loop)

    def test_ui_evidence_proves_viewport_not_only_pixels(self) -> None:
        mandate = MANDATE_FILE.read_text(encoding="utf-8")
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        for text in (mandate, workflow):
            self.assertIn("viewport dimensions", text)
            self.assertIn("device scaling", text)
            self.assertIn("capture command", text)


if __name__ == "__main__":
    unittest.main()
