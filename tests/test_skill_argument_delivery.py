"""Keep invocation arguments reaching skills, including those whose procedure lives in a reference.

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
INVOCATION_SECTION = "\n## Arguments\n\nInvocation arguments: `$ARGUMENTS`\n"
ARGUMENTS_SECTION = "Arguments section of SKILL.md"
REQUEST_FALLBACK = "the user's request"
FALLBACK_ROW_PREFIXES = ("| Argument substitution |", "| Arguments |")
SKILL_ARGUMENTS = {
    "agent-issues": ("--draft", "--brief"),
    "ai-daily-digest": ("--focus", "--no-notion"),
    "council": ("core-eng", "debate"),
    "generate-agents-md": ("--output", "--update"),
    "gh-review-comments": ("--author", "--resolve"),
    "git-stage-hunk": ("--hunk", "--verify"),
    "humanize": ("--score-only", "--dry-run"),
    "kubecon-cfp": ("--track", "--format"),
    "plan-critic": ("--from-conversation",),
    "promptgen": ("--for", "--research"),
    "refactor-council": ("--no-scan", "--personas"),
    "review-agents-md": ("--score-only", "--fix"),
    "rightsize": ("audit", "write", "rewrite", "--dry-run"),
    "smallsteps": ("resume", "board"),
    "staff-code-review": ("--no-adversary",),
    "staff-resume": ("--job-url", "--mode"),
    "technical-debt-manager": ("--focus", "--label"),
    "test-writer": ("--review", "--lang"),
}


def skill_dir(name: str) -> Path:
    return PLUGINS_DIR / name / "skills" / name


def procedure_path(name: str) -> Path:
    workflow = skill_dir(name) / "references" / "workflow.md"
    return workflow if workflow.exists() else skill_dir(name) / "SKILL.md"


class ArgumentDeliveryTest(unittest.TestCase):
    def test_skill_entry_carries_the_substituted_placeholder(self) -> None:
        for name in SKILL_ARGUMENTS:
            with self.subTest(skill=name):
                skill = (skill_dir(name) / "SKILL.md").read_text(encoding="utf-8")
                self.assertEqual(skill.count(ARGUMENT_PLACEHOLDER), 1)
                self.assertIn(INVOCATION_SECTION, skill)

    def test_references_hold_no_placeholder_no_client_substitutes(self) -> None:
        for name in SKILL_ARGUMENTS:
            for reference in sorted((skill_dir(name) / "references").rglob("*.md")):
                with self.subTest(
                    reference=reference.relative_to(PLUGINS_DIR).as_posix()
                ):
                    text = reference.read_text(encoding="utf-8")
                    self.assertNotIn(ARGUMENT_PLACEHOLDER, text)

    def test_no_skill_reference_holds_a_placeholder(self) -> None:
        for reference in sorted(PLUGINS_DIR.glob("*/skills/*/references/**/*.md")):
            with self.subTest(reference=reference.relative_to(PLUGINS_DIR).as_posix()):
                text = reference.read_text(encoding="utf-8")
                self.assertNotIn(ARGUMENT_PLACEHOLDER, text)

    def test_workflow_reads_arguments_from_skill_entry_or_request(self) -> None:
        for name in SKILL_ARGUMENTS:
            with self.subTest(skill=name):
                procedure = procedure_path(name)
                workflow = procedure.read_text(encoding="utf-8")
                self.assertIn(REQUEST_FALLBACK, workflow)
                if procedure.name == "SKILL.md":
                    continue
                rows = [
                    line
                    for line in workflow.splitlines()
                    if line.startswith(FALLBACK_ROW_PREFIXES)
                ]
                self.assertEqual(len(rows), 1)
                self.assertIn(ARGUMENTS_SECTION, rows[0])
                self.assertGreaterEqual(workflow.count(ARGUMENTS_SECTION), 2)
                self.assertIn(REQUEST_FALLBACK, workflow)

    def test_workflow_documents_every_argument(self) -> None:
        for name, arguments in SKILL_ARGUMENTS.items():
            workflow = procedure_path(name).read_text(encoding="utf-8")
            for argument in arguments:
                with self.subTest(skill=name, argument=argument):
                    self.assertIn(argument, workflow)


if __name__ == "__main__":
    unittest.main()
