"""Keep the council persona agents and their portable mandates in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "council"
AGENTS_DIR = PLUGIN_DIR / "agents"
SKILL_DIR = PLUGIN_DIR / "skills" / "council"
MANDATES_DIR = SKILL_DIR / "references" / "agents"
REGISTRY_FILE = SKILL_DIR / "references" / "personas.md"
FRONTMATTER_FENCE = "---\n"
PERSONA_COUNT = 27
REGISTRY_SLUG = re.compile(r"^\| `(?P<slug>[a-z0-9-]+)` \|", re.MULTILINE)
DISPLAY_NAME_ENTRY = re.compile(r"=`(?P<slug>[a-z0-9-]+)`/(?P<name>[^;.\n]+(?:\. [^;.\n]+)?)[;.]")
TEMPLATE_HEADING = re.compile(r"^## .*\b(?:review|advisory)\b.*$", re.MULTILINE)
DOSSIER_NAME =re.compile(r"`(?P<file>[a-z0-9-]+-deep\.md)` in the council skill's `references/`")


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    frontmatter = text[len(FRONTMATTER_FENCE) : end]
    body = text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")
    return frontmatter, body


def agent_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.md"))


class PersonaMandateSyncTest(unittest.TestCase):
    def test_every_agent_has_identical_mandate(self) -> None:
        for agent in agent_files():
            with self.subTest(agent=agent.name):
                _, body = split_frontmatter(agent.read_text(encoding="utf-8"))
                mandate = MANDATES_DIR / agent.name
                self.assertTrue(mandate.is_file(), f"missing {mandate}")
                self.assertEqual(
                    body,
                    mandate.read_text(encoding="utf-8"),
                    f"edit agents/{agent.name} body and {mandate} together",
                )

    def test_no_orphan_mandates(self) -> None:
        agents = {path.name for path in agent_files()}
        mandates = {path.name for path in MANDATES_DIR.glob("*.md")}
        self.assertEqual(mandates, agents)

    def test_roster_size(self) -> None:
        self.assertEqual(len(agent_files()), PERSONA_COUNT)

    def test_frontmatter_name_matches_file(self) -> None:
        for agent in agent_files():
            with self.subTest(agent=agent.name):
                frontmatter, _ = split_frontmatter(agent.read_text(encoding="utf-8"))
                self.assertIn(f"name: {agent.stem}\n", frontmatter + "\n")
                self.assertIn("model_reasoning_effort: high", frontmatter)
                self.assertRegex(frontmatter, r"(?m)^tools: .*\bRead\b")

    def test_registry_lists_every_agent(self) -> None:
        registry = set(REGISTRY_SLUG.findall(REGISTRY_FILE.read_text(encoding="utf-8")))
        self.assertEqual(registry, {path.stem for path in agent_files()})

    def test_named_dossier_exists(self) -> None:
        for agent in agent_files():
            with self.subTest(agent=agent.name):
                match = DOSSIER_NAME.search(agent.read_text(encoding="utf-8"))
                self.assertIsNotNone(match, "dossier sentence missing")
                if match:
                    self.assertTrue((SKILL_DIR / "references" / match["file"]).is_file())

    def test_template_heading_matches_display_name(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        display_names = dict(DISPLAY_NAME_ENTRY.findall(skill))
        self.assertEqual(set(display_names), {path.stem for path in agent_files()})
        for agent in agent_files():
            with self.subTest(agent=agent.name):
                _, body = split_frontmatter(agent.read_text(encoding="utf-8"))
                headings = TEMPLATE_HEADING.findall(body)
                self.assertEqual(headings, [f"## {display_names[agent.stem]} review"])

    def test_root_manifest_has_no_schema(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn("$schema", manifest, "$schema stops Copilot CLI registering agents/")


if __name__ == "__main__":
    unittest.main()
