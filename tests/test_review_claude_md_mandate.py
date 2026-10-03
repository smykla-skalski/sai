"""Keep the review-claude-md evaluator agent and its portable mandate in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "review-claude-md"
AGENT_FILE = PLUGIN_DIR / "agents" / "claude-md-evaluator.md"
MANDATE_FILE = (
    PLUGIN_DIR / "skills" / "review-claude-md" / "references" / "claude-md-evaluator.md"
)
ROOT_MANIFEST = PLUGIN_DIR / "plugin.json"
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

    def test_agent_frontmatter_names_claude_md_evaluator(self) -> None:
        head = AGENT_FILE.read_text(encoding="utf-8").split("\n", 2)[1]
        self.assertEqual(head, "name: claude-md-evaluator")

    def test_root_manifest_has_no_schema(self) -> None:
        manifest = json.loads(ROOT_MANIFEST.read_text(encoding="utf-8"))
        self.assertNotIn(
            "$schema",
            manifest,
            "$schema stops Copilot CLI from registering agents/",
        )


if __name__ == "__main__":
    unittest.main()
