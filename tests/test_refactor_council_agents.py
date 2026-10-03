"""Keep the refactor-council Claude agents and their portable copies in sync.

Claude Code and Copilot CLI load the persona agents from agents/; Codex and
opencode read the same bodies from the skill's references/agents/.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "refactor-council"
AGENTS_DIR = PLUGIN_DIR / "agents"
SKILL_DIR = PLUGIN_DIR / "skills" / "refactor-council"
COPIES_DIR = SKILL_DIR / "references" / "agents"
FRONTMATTER_FENCE = "---\n"
EXPECTED_AGENTS = frozenset(
    {
        "beck-tidy-first-reviewer",
        "feathers-legacy-reviewer",
        "fowler-refactoring-reviewer",
        "martin-clean-architecture-reviewer",
        "metz-abstraction-reviewer",
        "ousterhout-deep-module-reviewer",
        "refactor-adversary",
        "tornhill-hotspot-advisor",
    }
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    head = text[len(FRONTMATTER_FENCE) : end]
    body = text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")
    return head, body


def stems(directory: Path) -> frozenset[str]:
    return frozenset(path.stem for path in directory.glob("*.md"))


class AgentCopiesSyncTest(unittest.TestCase):
    def test_agent_sets_match(self) -> None:
        self.assertEqual(stems(AGENTS_DIR), EXPECTED_AGENTS)
        self.assertEqual(stems(COPIES_DIR), EXPECTED_AGENTS)

    def test_agent_bodies_match_reference_copies(self) -> None:
        for name in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=name):
                agent_file = AGENTS_DIR / f"{name}.md"
                copy_file = COPIES_DIR / f"{name}.md"
                _, body = split_frontmatter(agent_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    body,
                    copy_file.read_text(encoding="utf-8"),
                    f"edit {agent_file.name} body and {copy_file} together",
                )

    def test_agent_frontmatter_name_matches_file(self) -> None:
        for name in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=name):
                head, _ = split_frontmatter(
                    (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
                )
                self.assertEqual(head.splitlines()[0], f"name: {name}")

    def test_agent_frontmatter_loads_in_copilot(self) -> None:
        for name in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=name):
                head, _ = split_frontmatter(
                    (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
                )
                fields = dict(line.split(": ", 1) for line in head.splitlines())
                self.assertNotIn("model", fields, "Claude cannot resolve model pins")
                description = fields["description"]
                if not description.startswith(('"', "'")):
                    self.assertNotIn(
                        ": ",
                        description,
                        "unquoted ': ' in description makes Copilot drop the agent",
                    )

    def test_persona_dossiers_exist(self) -> None:
        references = SKILL_DIR / "references"
        for name in sorted(EXPECTED_AGENTS - {"refactor-adversary"}):
            dossier = references / f"{name.split('-', 1)[0]}-deep.md"
            with self.subTest(agent=name):
                self.assertTrue(dossier.is_file(), f"missing {dossier}")
                body = (COPIES_DIR / f"{name}.md").read_text(encoding="utf-8")
                self.assertIn(f"`{dossier.name}`", body)


if __name__ == "__main__":
    unittest.main()
