"""Keep portable skill validation passing while Claude-only keys stay in SKILL.md.

'agentskills validate' rejects keys that Claude Code reads at the top level of
the frontmatter. scripts/validate_skills.py drops those keys, then applies the
skills-ref checks, so a real spec violation must still fail.

The tests run the script through 'uv run --script' (it pins skills-ref) and skip
when uv is not installed.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "validate_skills.py"
UV = shutil.which("uv")
RUN_TIMEOUT_SECONDS = 300
VALID_DESCRIPTION = "Does one thing. Use when testing validation."
CLAUDE_ONLY_FRONTMATTER = (
    'argument-hint: "[--flag]"\n'
    "user-invocable: true\n"
    "disable-model-invocation: true\n"
    "context: fork\n"
    "agent: general-purpose\n"
)


@unittest.skipIf(UV is None, "uv is not installed")
class ValidateSkillsCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)

    def run_script(self, *paths: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [UV, "run", "--quiet", "--script", str(SCRIPT), *map(str, paths)],
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SECONDS,
        )

    def write_skill(self, directory: str, frontmatter: str) -> Path:
        skill_dir = self.scratch / directory
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\n{frontmatter}---\n\n# Body\n", encoding="utf-8"
        )
        return skill_dir

    def test_accepts_skill_with_claude_only_keys(self) -> None:
        skill_dir = self.write_skill(
            "demo",
            f"name: demo\ndescription: {VALID_DESCRIPTION}\n{CLAUDE_ONLY_FRONTMATTER}",
        )

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Valid skill", result.stdout)

    def test_accepts_skill_md_path(self) -> None:
        skill_dir = self.write_skill(
            "demo", f"name: demo\ndescription: {VALID_DESCRIPTION}\n"
        )

        result = self.run_script(skill_dir / "SKILL.md")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_unknown_key_outside_claude_only_set(self) -> None:
        skill_dir = self.write_skill(
            "demo",
            f"name: demo\ndescription: {VALID_DESCRIPTION}\n"
            f"{CLAUDE_ONLY_FRONTMATTER}bogus: value\n",
        )

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn("Unexpected fields in frontmatter: bogus.", result.stderr)
        self.assertNotIn("argument-hint", result.stderr)

    def test_rejects_name_that_differs_from_directory(self) -> None:
        skill_dir = self.write_skill(
            "demo",
            f"name: other\ndescription: {VALID_DESCRIPTION}\n{CLAUDE_ONLY_FRONTMATTER}",
        )

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn("must match skill name", result.stderr)

    def test_rejects_invalid_name(self) -> None:
        skill_dir = self.write_skill(
            "Demo", f"name: Demo\ndescription: {VALID_DESCRIPTION}\n"
        )

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn("must be lowercase", result.stderr)

    def test_rejects_over_long_description(self) -> None:
        skill_dir = self.write_skill("demo", f"name: demo\ndescription: {'x' * 1025}\n")

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn("exceeds 1024 character limit", result.stderr)

    def test_rejects_missing_description(self) -> None:
        skill_dir = self.write_skill("demo", f"name: demo\n{CLAUDE_ONLY_FRONTMATTER}")

        result = self.run_script(skill_dir)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "Missing required field in frontmatter: description", result.stderr
        )

    def test_reports_every_failing_skill_and_keeps_going(self) -> None:
        good = self.write_skill(
            "good", f"name: good\ndescription: {VALID_DESCRIPTION}\n"
        )
        bad = self.write_skill("bad", "name: bad\n")

        result = self.run_script(bad, good)

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Validation failed for {bad}", result.stderr)
        self.assertIn(f"Valid skill: {good}", result.stdout)

    def test_validates_every_repository_skill(self) -> None:
        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        validated = result.stdout.count("Valid skill:")
        expected = len(list(REPO_ROOT.glob("plugins/*/skills/*/SKILL.md")))
        self.assertEqual(validated, expected)


if __name__ == "__main__":
    unittest.main()
