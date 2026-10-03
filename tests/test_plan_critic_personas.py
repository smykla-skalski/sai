"""Keep the plan-critic persona agents and their portable mandates in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "plan-critic"
AGENTS_DIR = PLUGIN_DIR / "agents"
REFERENCES_DIR = PLUGIN_DIR / "skills" / "plan-critic" / "references"
PERSONAS = ("skeptic-reviewer", "architect-reviewer", "verifier-reviewer")
FRONTMATTER_FENCE = "---\n"


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    head = text[len(FRONTMATTER_FENCE) : end + 1]
    body = text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")
    return head, body


class PersonaSyncTest(unittest.TestCase):
    def test_agent_body_matches_reference_mandate(self) -> None:
        for persona in PERSONAS:
            with self.subTest(persona=persona):
                agent_file = AGENTS_DIR / f"{persona}.md"
                mandate_file = REFERENCES_DIR / f"{persona}.md"
                _, body = split_frontmatter(agent_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    body,
                    mandate_file.read_text(encoding="utf-8"),
                    f"edit {agent_file.name} body and {mandate_file} together",
                )

    def test_agent_frontmatter_names_persona(self) -> None:
        for persona in PERSONAS:
            with self.subTest(persona=persona):
                text = (AGENTS_DIR / f"{persona}.md").read_text(encoding="utf-8")
                head, _ = split_frontmatter(text)
                self.assertEqual(head.splitlines()[0], f"name: {persona}")

    def test_agent_frontmatter_values_are_plain_yaml(self) -> None:
        for persona in PERSONAS:
            with self.subTest(persona=persona):
                text = (AGENTS_DIR / f"{persona}.md").read_text(encoding="utf-8")
                head, _ = split_frontmatter(text)
                for line in head.splitlines():
                    _, _, value = line.partition(": ")
                    self.assertNotIn(
                        ": ",
                        value,
                        f"unquoted ': ' breaks the YAML and Copilot CLI drops the agent: {line}",
                    )

    def test_agents_dir_holds_only_the_personas(self) -> None:
        names = sorted(path.stem for path in AGENTS_DIR.glob("*.md"))
        self.assertEqual(names, sorted(PERSONAS))

    def test_skill_description_does_not_promise_parallel_everywhere(self) -> None:
        skill = (PLUGIN_DIR / "skills" / "plan-critic" / "SKILL.md").read_text(
            encoding="utf-8",
        )
        head, _ = split_frontmatter(skill)
        description = next(
            line for line in head.splitlines() if line.startswith("description: ")
        )
        self.assertNotIn("Spawns parallel", description)
        self.assertIn("one at a time on other agents", description)

    def test_root_manifest_has_no_schema(self) -> None:
        manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
        self.assertNotIn(
            "$schema",
            manifest,
            "Copilot CLI stops registering agents/ when $schema is set",
        )


if __name__ == "__main__":
    unittest.main()
