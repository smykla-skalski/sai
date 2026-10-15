"""Keep invocation arguments reaching skills whose procedure lives in a reference.

No client substitutes `$ARGUMENTS` in a file the agent reads with a tool, so each
skill carries the placeholder once in SKILL.md and its workflow reads the values
from there.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"
ARGUMENT_PLACEHOLDER = "$ARGUMENTS"
INVOCATION_LINE = "Invocation arguments: `$ARGUMENTS`"
ARGUMENTS_SECTION = "Arguments section of SKILL.md"
REQUEST_FALLBACK = "the user's request"
SKILL_ARGUMENTS = {
    "council": ("core-eng", "debate"),
    "plan-critic": ("--from-conversation",),
    "refactor-council": ("--no-scan", "--personas"),
    "review-claude-md": ("--score-only", "--fix"),
    "staff-code-review": ("--no-adversary",),
    "technical-debt-manager": ("--focus", "--label"),
}


def skill_dir(name: str) -> Path:
    return PLUGINS_DIR / name / "skills" / name


class ArgumentDeliveryTest(unittest.TestCase):
    def test_skill_entry_carries_the_substituted_placeholder(self) -> None:
        for name in SKILL_ARGUMENTS:
            with self.subTest(skill=name):
                skill = (skill_dir(name) / "SKILL.md").read_text(encoding="utf-8")
                self.assertEqual(skill.count(ARGUMENT_PLACEHOLDER), 1)
                self.assertIn(INVOCATION_LINE, skill)

    def test_references_hold_no_placeholder_no_client_substitutes(self) -> None:
        for name in SKILL_ARGUMENTS:
            for reference in sorted((skill_dir(name) / "references").rglob("*.md")):
                with self.subTest(
                    reference=reference.relative_to(PLUGINS_DIR).as_posix()
                ):
                    text = reference.read_text(encoding="utf-8")
                    self.assertNotIn(ARGUMENT_PLACEHOLDER, text)

    def test_workflow_reads_arguments_from_skill_entry_or_request(self) -> None:
        for name in SKILL_ARGUMENTS:
            with self.subTest(skill=name):
                workflow = (skill_dir(name) / "references" / "workflow.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn(ARGUMENTS_SECTION, workflow)
                self.assertIn(REQUEST_FALLBACK, workflow)

    def test_workflow_documents_every_argument(self) -> None:
        for name, arguments in SKILL_ARGUMENTS.items():
            workflow = (skill_dir(name) / "references" / "workflow.md").read_text(
                encoding="utf-8"
            )
            for argument in arguments:
                with self.subTest(skill=name, argument=argument):
                    self.assertIn(argument, workflow)


if __name__ == "__main__":
    unittest.main()
