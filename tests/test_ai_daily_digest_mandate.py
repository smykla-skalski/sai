"""Keep the ai-daily-digest research agent and its portable mandate in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "ai-daily-digest"
AGENT_FILE = PLUGIN_DIR / "agents" / "digest-research-agent.md"
MANDATE_FILE = (
    PLUGIN_DIR
    / "skills"
    / "ai-daily-digest"
    / "references"
    / "digest-research-agent.md"
)
FRONTMATTER_FENCE = "---\n"


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

    def test_agent_frontmatter_names_digest_research_agent(self) -> None:
        head = AGENT_FILE.read_text(encoding="utf-8").split("\n", 2)[1]
        self.assertEqual(head, "name: digest-research-agent")


if __name__ == "__main__":
    unittest.main()
