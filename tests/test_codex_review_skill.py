"""Tests for the Codex review-skill validators."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "codex" / "review-skill" / "scripts"
SELF_SKILL_DIR = REPO_ROOT / "codex" / "review-skill"


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_skill_md(frontmatter: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {_yaml_quote(value)}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


class CodexReviewSkillTests(unittest.TestCase):
    def create_skill(
        self,
        tmp_dir: Path,
        *,
        dir_name: str = "sample-skill",
        frontmatter_overrides: dict[str, str] | None = None,
        body: str = "# Sample\n\n## Use this skill\n\n- Use when auditing sample skills.\n",
        files: dict[str, str] | None = None,
        executable_paths: set[str] | None = None,
    ) -> Path:
        skill_dir = tmp_dir / dir_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "name": dir_name,
            "description": "Audit sample skills. Use when validating Codex skill checks.",
        }
        if frontmatter_overrides:
            frontmatter.update(frontmatter_overrides)

        (skill_dir / "SKILL.md").write_text(
            _build_skill_md(frontmatter, body),
            encoding="utf-8",
        )

        for rel_path, content in (files or {}).items():
            path = skill_dir / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        for rel_path in executable_paths or set():
            path = skill_dir / rel_path
            path.chmod(0o755)

        return skill_dir

    def run_ndjson(
        self,
        command: list[str],
    ) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        records: list[dict[str, object]] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            self.assertIsInstance(payload, dict)
            records.append(payload)

        self.assertTrue(records, f"No NDJSON output for command: {command}")
        self.assertEqual(records[-1].get("kind"), "summary")
        return result, records

    def run_validate(
        self,
        skill_dir: Path,
        *,
        mode: str = "all",
    ) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
        command = [str(SCRIPTS_DIR / "validate.py"), str(skill_dir)]
        if mode != "all":
            command.append(mode)
        return self.run_ndjson(command)

    def run_checker(
        self,
        script_name: str,
        skill_dir: Path,
        *,
        checks: tuple[str, ...] = (),
    ) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
        command = [str(SCRIPTS_DIR / script_name), str(skill_dir)]
        for check in checks:
            command.extend(["--check", check])
        return self.run_ndjson(command)

    def one_check(
        self,
        records: list[dict[str, object]],
        check_id: str,
    ) -> dict[str, object]:
        matches = [
            record
            for record in records
            if record.get("kind") == "check" and record.get("check") == check_id
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_self_skill_passes_full_validation(self) -> None:
        result, records = self.run_validate(SELF_SKILL_DIR)

        blocking_failures = [
            record
            for record in records
            if record.get("kind") == "check"
            and record.get("pass") is False
            and record.get("level") != "info"
        ]
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(blocking_failures)

    def test_malformed_openai_yaml_fails_metadata_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "agents/openai.yaml": (
                        "interface:\n"
                        '  display_name: "Broken"\n'
                        '  short_description: Broken quote"\n'
                        '  default_prompt: "Use $sample-skill to audit this skill."\n'
                    )
                },
            )
            result, records = self.run_checker(
                "check_agents_metadata.py",
                skill_dir,
                checks=("AM-short-description",),
            )

        record = self.one_check(records, "AM-short-description")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_claude_only_surface_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"allowed-tools": "Read"},
                body=(
                    "# Sample\n\n"
                    "Use `$ARGUMENTS` to decide what to review.\n"
                ),
            )
            result, records = self.run_checker(
                "check_prompts.py",
                skill_dir,
                checks=("PR-claude-only-surface",),
            )

        record = self.one_check(records, "PR-claude-only-surface")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_risky_command_without_approval_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Sample\n\n"
                    "## Use this skill\n\n"
                    "- Use when finishing the release.\n\n"
                    "```bash\n"
                    "gh pr merge 42 --squash\n"
                    "```\n"
                ),
            )
            result, records = self.run_checker(
                "check_shell_safety.py",
                skill_dir,
                checks=("SH-risky-command-flow",),
            )

        record = self.one_check(records, "SH-risky-command-flow")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_startup_cost_language_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Sample\n\n"
                    "At startup, list every installed skill before answering.\n"
                ),
            )
            result, records = self.run_checker(
                "check_prompts.py",
                skill_dir,
                checks=("PR-startup-cost",),
            )

        record = self.one_check(records, "PR-startup-cost")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_shell_non_boolean_truthy_value_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "scripts/unsafe.py": "import subprocess\nsubprocess.run('ls', shell=1)\n",
                },
            )
            result, records = self.run_checker(
                "check_shell_safety.py",
                skill_dir,
                checks=("SH-python-subprocess-safe",),
            )
        record = self.one_check(records, "SH-python-subprocess-safe")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_os_system_import_alias_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "scripts/unsafe.py": "from os import system\nsystem('ls')\n",
                },
            )
            result, records = self.run_checker(
                "check_shell_safety.py",
                skill_dir,
                checks=("SH-python-subprocess-safe",),
            )
        record = self.one_check(records, "SH-python-subprocess-safe")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_dependencies_shape_requires_nested_tools_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_content = (
                "dependencies:\n"
                "  tools:\n"
                "other_block:\n"
                '    - type: "fake"\n'
                '      value: "fake"\n'
            )
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "agents/openai.yaml": yaml_content,
                },
            )
            result, records = self.run_checker(
                "check_agents_metadata.py",
                skill_dir,
                checks=("AM-dependencies-shape",),
            )
        record = self.one_check(records, "AM-dependencies-shape")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_quoted_field_accepts_escaped_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_content = (
                "interface:\n"
                '  display_name: "name"\n'
                '  short_description: "This is a \\"very\\" valid string"\n'
                '  default_prompt: "prompt"\n'
            )
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "agents/openai.yaml": yaml_content,
                },
            )
            result, records = self.run_checker(
                "check_agents_metadata.py",
                skill_dir,
                checks=("AM-short-description",),
            )
        record = self.one_check(records, "AM-short-description")
        self.assertEqual(result.returncode, 0)
        self.assertIs(record.get("pass"), True)

    def test_claude_only_terms_with_trailing_negative_context_still_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body="use when auditing\n\n$ARGUMENTS $CLAUDE_SKILL_DIR AskUserQuestion context: fork (but do not use)\n",
            )
            result, records = self.run_checker(
                "check_prompts.py",
                skill_dir,
                checks=("PR-claude-only-surface",),
            )
        record = self.one_check(records, "PR-claude-only-surface")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)

    def test_claude_only_prohibition_line_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Sample\n\n"
                    "## Do not use this skill\n\n"
                    "- Do not apply Claude-only checks such as `$ARGUMENTS`, "
                    "`$CLAUDE_SKILL_DIR`, or `context: fork`.\n"
                ),
            )
            result, records = self.run_checker(
                "check_prompts.py",
                skill_dir,
                checks=("PR-claude-only-surface",),
            )
        record = self.one_check(records, "PR-claude-only-surface")
        self.assertEqual(result.returncode, 0)
        self.assertIs(record.get("pass"), True)

    def test_slash_prefixed_links_fail_with_bundle_relative_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body="use when auditing\n\n[Broken link](/references/does_not_exist.md)\n",
            )
            result, records = self.run_checker(
                "check_structure.py",
                skill_dir,
                checks=("ST-links-resolve",),
            )
        record = self.one_check(records, "ST-links-resolve")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)
        self.assertIn("bundle-relative", str(record.get("detail")))

    def test_structure_flags_missing_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Sample\n\n"
                    "Read [references/checklist.md](references/checklist.md) before review.\n"
                ),
            )
            result, records = self.run_checker(
                "check_structure.py",
                skill_dir,
                checks=("ST-links-resolve",),
            )

        record = self.one_check(records, "ST-links-resolve")
        self.assertEqual(result.returncode, 1)
        self.assertIs(record.get("pass"), False)
