from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = (
    REPO_ROOT / "claude" / "review-skill" / "skills" / "review-skill" / "scripts"
)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate  # noqa: E402
from skill_check_common import SkillDocument, SkillLoadError  # noqa: E402


class ValidateScriptTests(unittest.TestCase):
    def test_frontmatter_missing_fields_emits_all_nine_checks(self) -> None:
        doc = SkillDocument(
            skill_dir=Path("/virtual/fake-skill"),
            skill_md_path=Path("/virtual/fake-skill/SKILL.md"),
            content="",
            frontmatter={},
            body="",
            prose_body="",
            body_start_line=1,
            resource_files=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []

        with patch.object(validate, "emit_record", side_effect=records.append):
            validate.run_frontmatter(doc, collector)

        self.assertEqual(collector.total, 9)
        self.assertEqual(len(records), 9)
        self.assertEqual(
            sum(1 for record in records if record["check"] == "name-format"), 1
        )
        self.assertEqual(
            sum(
                1 for record in records if record["check"] == "description-third-person"
            ),
            1,
        )

    def test_missing_structure_delegate_emits_runtime_failure(self) -> None:
        config = validate.DelegateConfig(script="does-not-exist.py")
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []

        with patch.object(validate, "emit_record", side_effect=records.append):
            validate._run_structure_delegate(
                config,
                SCRIPT_DIR,
                Path("/virtual/skill"),
                collector,
            )

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "delegate-does-not-exist-runtime")
        self.assertIn("Script not found", str(records[0]["detail"]))

    def test_lint_malformed_summary_fails_script_lint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_dir = tmp_path / "scripts-bin"
            script_dir.mkdir()
            lint_script = script_dir / "lint-scripts.py"
            lint_script.write_text("#!/bin/sh\n", encoding="utf-8")
            lint_script.chmod(0o755)

            skill_dir = tmp_path / "skill"
            (skill_dir / "scripts").mkdir(parents=True)

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            fake_run = validate.ScriptRunResult(
                ok=True,
                returncode=0,
                stdout='{"summary": true, "findings": "bad"}\n',
                stderr="",
            )

            with (
                patch.object(validate, "emit_record", side_effect=records.append),
                patch.object(validate, "_run_lint_script", return_value=fake_run),
            ):
                validate._handle_lint_scripts(script_dir, skill_dir, collector)

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "script-lint")
        self.assertIs(records[0]["pass"], False)
        self.assertIn("Summary missing integer 'findings'", str(records[0]["detail"]))

    def test_load_error_preserves_detail_and_usage_exit_code(self) -> None:
        records: list[dict[str, object]] = []

        with (
            patch.object(validate, "emit_record", side_effect=records.append),
            patch.object(
                validate,
                "load_skill_document",
                side_effect=SkillLoadError("custom load failure"),
            ),
        ):
            exit_code = validate.main(["/virtual/missing"])

        self.assertEqual(exit_code, validate.EXIT_USAGE_ERROR)
        self.assertEqual(records[0]["check"], "skill-md-exists")
        self.assertIn("custom load failure", str(records[0]["detail"]))
        self.assertTrue(bool(records[-1]["summary"]))

    def test_invalid_guard_field_emits_runtime_failure(self) -> None:
        parsed = validate.ParsedDelegateOutput(
            checks=(),
            summary={
                "summary": True,
                "total": 0,
                "passed": 0,
                "failed": 0,
                "directives": "not-a-number",
            },
            invalid_lines=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []

        with patch.object(validate, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed,
                collector,
                script="check-preprocessing.py",
                guard_field="directives",
            )

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "delegate-check-preprocessing-runtime")
        self.assertIn("not an integer", str(records[0]["detail"]))


if __name__ == "__main__":
    unittest.main()
