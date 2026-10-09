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
WORKFLOW_FILE = PLUGIN_DIR / "skills" / "adversarial-test" / "references" / "workflow.md"
SHIP_IT_TEST_GATE = (
    PLUGIN_DIR.parent / "ship-it" / "skills" / "ship-it" / "references" / "test.md"
)
FRONTMATTER_FENCE = "---\n"
VERDICT_LINE = "TEST_ADVERSARY_VERDICT: <PASS | PASS (partial) | FAIL (N) | BLOCKED>"
VERDICTS = ("PASS", "PASS (partial)", "FAIL", "BLOCKED")


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


if __name__ == "__main__":
    unittest.main()
