"""Keep the humanize skill in the caller's conversation.

A forked skill gets no conversation history, so pasted text never reaches it,
and it cannot ask the user for a missing target. The plugin evals in
plugins/humanize/evals/ check this behavior, but they are paid model runs and
CI does not run them.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

SKILL = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "humanize"
    / "skills"
    / "humanize"
    / "SKILL.md"
)


def frontmatter(text: str) -> dict[str, str]:
    block = text.split("---\n", 2)[1]
    fields = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            fields[key] = value.strip()
    return fields


class HumanizeSkillTest(unittest.TestCase):
    def test_skill_runs_inline_without_subagents(self) -> None:
        fields = frontmatter(SKILL.read_text(encoding="utf-8"))
        self.assertNotIn("context", fields)
        self.assertNotIn("agent", fields)
        self.assertNotIn("Agent", fields["allowed-tools"].split())


if __name__ == "__main__":
    unittest.main()
