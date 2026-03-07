from __future__ import annotations

import json
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
from skill_check_common import CheckResult, SkillDocument, SkillLoadError  # noqa: E402


def _make_doc(
    *,
    frontmatter: dict[str, str] | None = None,
    skill_dir: str = "/virtual/fake-skill",
) -> SkillDocument:
    """Build a minimal SkillDocument for unit tests."""
    return SkillDocument(
        skill_dir=Path(skill_dir),
        skill_md_path=Path(f"{skill_dir}/SKILL.md"),
        content="",
        frontmatter=frontmatter or {},
        body="",
        prose_body="",
        body_start_line=1,
        resource_files=(),
    )


def _run_frontmatter(doc: SkillDocument) -> tuple[validate.ResultCollector, list[dict[str, object]]]:
    """Run frontmatter checks and return collector + emitted records."""
    collector = validate.ResultCollector()
    records: list[dict[str, object]] = []
    with patch.object(validate, "emit_record", side_effect=records.append):
        validate.run_frontmatter(doc, collector)
    return collector, records


def _find_check(records: list[dict[str, object]], check_id: str) -> dict[str, object] | None:
    """Find a record by check ID."""
    for record in records:
        if record.get("check") == check_id:
            return record
    return None


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------


class ValidateScriptTests(unittest.TestCase):
    def test_frontmatter_missing_fields_emits_all_nine_checks(self) -> None:
        doc = _make_doc()
        collector, records = _run_frontmatter(doc)

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


# ---------------------------------------------------------------------------
# Frontmatter: name checks
# ---------------------------------------------------------------------------


class NameCheckTests(unittest.TestCase):
    def test_name_valid_matches_dir(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "fake-skill"},
            skill_dir="/virtual/fake-skill",
        )
        _, records = _run_frontmatter(doc)
        present = _find_check(records, "name-present")
        fmt = _find_check(records, "name-format")
        match = _find_check(records, "name-matches-dir")
        self.assertTrue(present["pass"])
        self.assertTrue(fmt["pass"])
        self.assertTrue(match["pass"])

    def test_name_too_long(self) -> None:
        long_name = "a" * 65
        doc = _make_doc(frontmatter={"name": long_name})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("exceeds", str(fmt["detail"]))

    def test_name_invalid_chars(self) -> None:
        doc = _make_doc(frontmatter={"name": "Bad_Name"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("invalid characters", str(fmt["detail"]))

    def test_name_leading_trailing_hyphen(self) -> None:
        doc = _make_doc(frontmatter={"name": "-bad-name-"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "name-format")
        self.assertFalse(fmt["pass"])
        # The regex catches this as invalid chars first (uppercase pattern)
        # since -bad-name- does match [a-z0-9-]+, it should hit the hyphen check
        self.assertIn("hyphen", str(fmt["detail"]))

    def test_name_consecutive_hyphens(self) -> None:
        doc = _make_doc(frontmatter={"name": "bad--name"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("consecutive", str(fmt["detail"]))

    def test_name_dir_mismatch(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "other-name"},
            skill_dir="/virtual/fake-skill",
        )
        _, records = _run_frontmatter(doc)
        match = _find_check(records, "name-matches-dir")
        self.assertFalse(match["pass"])
        self.assertIn("does not match", str(match["detail"]))


# ---------------------------------------------------------------------------
# Frontmatter: description checks
# ---------------------------------------------------------------------------


class DescriptionCheckTests(unittest.TestCase):
    def test_description_valid_with_trigger(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "Generate reports. Use when auditing."},
        )
        _, records = _run_frontmatter(doc)
        present = _find_check(records, "description-present")
        length = _find_check(records, "description-length")
        trigger = _find_check(records, "description-trigger-phrases")
        self.assertTrue(present["pass"])
        self.assertTrue(length["pass"])
        self.assertTrue(trigger["pass"])

    def test_description_too_long(self) -> None:
        long_desc = "x" * 1025
        doc = _make_doc(frontmatter={"description": long_desc})
        _, records = _run_frontmatter(doc)
        length = _find_check(records, "description-length")
        self.assertFalse(length["pass"])
        self.assertIn("exceeds", str(length["detail"]))

    def test_description_no_trigger_phrase(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "Generate daily reports from data"},
        )
        _, records = _run_frontmatter(doc)
        trigger = _find_check(records, "description-trigger-phrases")
        self.assertFalse(trigger["pass"])
        self.assertIn("trigger phrase", str(trigger["detail"]))

    def test_description_trigger_skipped_for_dmi(self) -> None:
        doc = _make_doc(
            frontmatter={
                "description": "Generate daily reports",
                "disable-model-invocation": "true",
            },
        )
        _, records = _run_frontmatter(doc)
        trigger = _find_check(records, "description-trigger-phrases")
        self.assertTrue(trigger["pass"])
        self.assertIn("disable-model-invocation", str(trigger["detail"]))

    def test_description_first_person_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "I can generate reports for you"},
        )
        _, records = _run_frontmatter(doc)
        voice = _find_check(records, "description-third-person")
        self.assertFalse(voice["pass"])

    def test_description_second_person_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "You can use this to generate reports"},
        )
        _, records = _run_frontmatter(doc)
        voice = _find_check(records, "description-third-person")
        self.assertFalse(voice["pass"])


# ---------------------------------------------------------------------------
# Frontmatter: allowed-tools, user-invocable
# ---------------------------------------------------------------------------


class AllowedToolsTests(unittest.TestCase):
    def test_allowed_tools_present(self) -> None:
        doc = _make_doc(frontmatter={"allowed-tools": "Bash, Read"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "allowed-tools-present")
        self.assertTrue(check["pass"])

    def test_allowed_tools_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "allowed-tools-present")
        self.assertFalse(check["pass"])


class UserInvocableTests(unittest.TestCase):
    def test_user_invocable_valid(self) -> None:
        doc = _make_doc(frontmatter={"user-invocable": "true"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "user-invocable-present")
        self.assertTrue(check["pass"])

    def test_user_invocable_invalid_value(self) -> None:
        doc = _make_doc(frontmatter={"user-invocable": "maybe"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "user-invocable-present")
        self.assertFalse(check["pass"])
        self.assertIn("must be boolean", str(check["detail"]))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


class ParseNdjsonLineTests(unittest.TestCase):
    def test_valid_json(self) -> None:
        result = validate._parse_ndjson_line('{"check": "foo", "pass": true}')
        self.assertIsNotNone(result)
        self.assertEqual(result["check"], "foo")

    def test_invalid_json(self) -> None:
        result = validate._parse_ndjson_line("not json")
        self.assertIsNone(result)

    def test_array_rejected(self) -> None:
        result = validate._parse_ndjson_line("[1, 2, 3]")
        self.assertIsNone(result)


class SummaryIntTests(unittest.TestCase):
    def test_integer(self) -> None:
        self.assertEqual(validate._summary_int({"total": 5}, "total"), 5)

    def test_bool_rejected(self) -> None:
        self.assertIsNone(validate._summary_int({"total": True}, "total"))

    def test_none_field(self) -> None:
        self.assertIsNone(validate._summary_int({"total": None}, "total"))

    def test_missing_field(self) -> None:
        self.assertIsNone(validate._summary_int({}, "total"))

    def test_string_rejected(self) -> None:
        """After simplification, string values are rejected."""
        self.assertIsNone(validate._summary_int({"total": "5"}, "total"))


class SnippetTests(unittest.TestCase):
    def test_truncation(self) -> None:
        long_text = "a" * 300
        result = validate._snippet(long_text)
        self.assertEqual(len(result), validate.ERROR_SNIPPET_LENGTH)

    def test_empty(self) -> None:
        self.assertEqual(validate._snippet(""), "")
        self.assertEqual(validate._snippet("   "), "")


# ---------------------------------------------------------------------------
# Delegate output parsing
# ---------------------------------------------------------------------------


class ParseDelegateOutputTests(unittest.TestCase):
    def test_valid_output(self) -> None:
        lines = [
            json.dumps({"check": "c1", "pass": True, "detail": "ok"}),
            json.dumps({"summary": True, "total": 1, "passed": 1, "failed": 0}),
        ]
        parsed = validate._parse_delegate_output("\n".join(lines))
        self.assertEqual(len(parsed.checks), 1)
        self.assertEqual(parsed.checks[0].check, "c1")
        self.assertIsNotNone(parsed.summary)
        self.assertEqual(len(parsed.invalid_lines), 0)

    def test_duplicate_summary(self) -> None:
        lines = [
            json.dumps({"summary": True, "total": 0, "passed": 0, "failed": 0}),
            json.dumps({"summary": True, "total": 0, "passed": 0, "failed": 0}),
        ]
        parsed = validate._parse_delegate_output("\n".join(lines))
        self.assertIsNotNone(parsed.summary)
        self.assertEqual(len(parsed.invalid_lines), 1)


class ParseLintOutputTests(unittest.TestCase):
    def test_valid_output(self) -> None:
        lines = [
            json.dumps({"check": "S01", "message": "issue", "severity": "critical"}),
            json.dumps({"summary": True, "findings": 1}),
        ]
        parsed = validate._parse_lint_output("\n".join(lines))
        self.assertEqual(len(parsed.findings), 1)
        self.assertIsNotNone(parsed.summary)


# ---------------------------------------------------------------------------
# Delegation infrastructure
# ---------------------------------------------------------------------------


class CollectDelegateOutputTests(unittest.TestCase):
    def test_bad_exit_code(self) -> None:
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=2, stdout="", stderr="error msg",
        )
        with patch.object(validate, "_run_script", return_value=fake_run):
            parsed, error = validate._collect_delegate_output(
                Path("/virtual/script.py"), Path("/virtual/skill"),
            )
        self.assertIsNone(parsed)
        self.assertIn("Unexpected exit code", error)

    def test_empty_stdout(self) -> None:
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=0, stdout="  \n", stderr="",
        )
        with patch.object(validate, "_run_script", return_value=fake_run):
            parsed, error = validate._collect_delegate_output(
                Path("/virtual/script.py"), Path("/virtual/skill"),
            )
        self.assertIsNone(parsed)
        self.assertIn("No stdout", error)

    def test_total_mismatch(self) -> None:
        ndjson = "\n".join([
            json.dumps({"check": "c1", "pass": True, "detail": "ok"}),
            json.dumps({"summary": True, "total": 5, "passed": 5, "failed": 0}),
        ])
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=0, stdout=ndjson, stderr="",
        )
        with patch.object(validate, "_run_script", return_value=fake_run):
            parsed, error = validate._collect_delegate_output(
                Path("/virtual/script.py"), Path("/virtual/skill"),
            )
        self.assertIsNone(parsed)
        self.assertIn("total mismatch", error)


class EmitDelegateChecksTests(unittest.TestCase):
    def test_guard_zero_skips(self) -> None:
        parsed = validate.ParsedDelegateOutput(
            checks=(
                CheckResult(check="c1", passed=True, detail="ok"),
            ),
            summary={"summary": True, "total": 1, "passed": 1, "failed": 0, "refs": 0},
            invalid_lines=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with patch.object(validate, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed, collector, script="test.py", guard_field="refs",
            )
        self.assertEqual(collector.total, 0)
        self.assertEqual(len(records), 0)

    def test_guard_positive_emits(self) -> None:
        parsed = validate.ParsedDelegateOutput(
            checks=(
                CheckResult(check="c1", passed=True, detail="ok"),
            ),
            summary={"summary": True, "total": 1, "passed": 1, "failed": 0, "refs": 2},
            invalid_lines=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with patch.object(validate, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed, collector, script="test.py", guard_field="refs",
            )
        self.assertEqual(collector.total, 1)
        self.assertEqual(records[0]["check"], "c1")


# ---------------------------------------------------------------------------
# Special handlers (mocked subprocess)
# ---------------------------------------------------------------------------


class LintScriptsHandlerTests(unittest.TestCase):
    def test_no_scripts_dir_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "skill"
            skill_dir.mkdir()
            # No scripts/ subdirectory

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            with patch.object(validate, "emit_record", side_effect=records.append):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        self.assertEqual(collector.total, 1)
        check = _find_check(records, "script-lint")
        self.assertTrue(check["pass"])

    def test_zero_findings_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "skill"
            (skill_dir / "scripts").mkdir(parents=True)

            fake_run = validate.ScriptRunResult(
                ok=True, returncode=0,
                stdout=json.dumps({"summary": True, "findings": 0}) + "\n",
                stderr="",
            )

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            with (
                patch.object(validate, "emit_record", side_effect=records.append),
                patch.object(validate, "_run_lint_script", return_value=fake_run),
            ):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        check = _find_check(records, "script-lint")
        self.assertTrue(check["pass"])

    def test_findings_present_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "skill"
            (skill_dir / "scripts").mkdir(parents=True)

            finding = json.dumps(
                {"check": "S01", "message": "bad", "severity": "critical"},
            )
            summary = json.dumps({"summary": True, "findings": 1})
            fake_run = validate.ScriptRunResult(
                ok=True, returncode=1,
                stdout=f"{finding}\n{summary}\n",
                stderr="",
            )

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            with (
                patch.object(validate, "emit_record", side_effect=records.append),
                patch.object(validate, "_run_lint_script", return_value=fake_run),
            ):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        check = _find_check(records, "script-lint")
        self.assertFalse(check["pass"])
        self.assertIn("critical", str(check["detail"]))


class ForkCandidateHandlerTests(unittest.TestCase):
    def test_strong_recommendation_passes(self) -> None:
        summary_line = json.dumps({
            "recommendation": "strong",
            "detail": "5 signals detected",
        })
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=0,
            stdout=summary_line + "\n",
            stderr="",
        )

        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with (
            patch.object(validate, "emit_record", side_effect=records.append),
            patch.object(validate, "_run_script", return_value=fake_run),
        ):
            validate._handle_fork_candidate(SCRIPT_DIR, Path("/virtual/skill"), collector)

        check = _find_check(records, "fork-candidate-info")
        self.assertTrue(check["pass"])
        self.assertIn("INFO:", str(check["detail"]))

    def test_none_recommendation_passes(self) -> None:
        summary_line = json.dumps({
            "recommendation": "none",
            "detail": "No fork signals",
        })
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=1,
            stdout=summary_line + "\n",
            stderr="",
        )

        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with (
            patch.object(validate, "emit_record", side_effect=records.append),
            patch.object(validate, "_run_script", return_value=fake_run),
        ):
            validate._handle_fork_candidate(SCRIPT_DIR, Path("/virtual/skill"), collector)

        check = _find_check(records, "fork-candidate-info")
        self.assertTrue(check["pass"])
        self.assertIn("No fork recommendation", str(check["detail"]))


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def test_main_frontmatter_mode_only(self) -> None:
        doc = _make_doc(
            frontmatter={
                "name": "fake-skill",
                "description": "Test skill. Use for testing.",
                "allowed-tools": "Bash",
                "user-invocable": "true",
            },
        )
        records: list[dict[str, object]] = []
        with (
            patch.object(validate, "emit_record", side_effect=records.append),
            patch.object(validate, "load_skill_document", return_value=doc),
        ):
            exit_code = validate.main(["/virtual/fake-skill", "frontmatter"])

        self.assertEqual(exit_code, 0)
        # Should have 9 frontmatter checks + 1 summary
        check_records = [r for r in records if "check" in r]
        self.assertEqual(len(check_records), 9)

    def test_main_structure_mode_only(self) -> None:
        """Structure mode should not emit frontmatter checks."""
        doc = _make_doc(frontmatter={})
        records: list[dict[str, object]] = []
        with (
            patch.object(validate, "emit_record", side_effect=records.append),
            patch.object(validate, "load_skill_document", return_value=doc),
            patch.object(validate, "run_structure"),
        ):
            validate.main(["/virtual/fake-skill", "structure"])

        check_records = [r for r in records if "check" in r]
        # No frontmatter checks should appear
        fm_checks = [
            r for r in check_records
            if r["check"] in {
                "name-present", "name-format", "name-matches-dir",
                "description-present",
            }
        ]
        self.assertEqual(len(fm_checks), 0)


# ---------------------------------------------------------------------------
# Fork candidate summary parsing
# ---------------------------------------------------------------------------


class ParseForkCandidateSummaryTests(unittest.TestCase):
    def test_recommendation_not_last_line(self) -> None:
        """Summary is last line - verifies current behavior."""
        lines = [
            json.dumps({"signal": "P1", "strength": 1.0}),
            json.dumps({"recommendation": "strong", "detail": "5 signals"}),
        ]
        summary, error = validate._parse_fork_candidate_summary("\n".join(lines))
        self.assertIsNone(error)
        self.assertEqual(summary["recommendation"], "strong")


if __name__ == "__main__":
    unittest.main()
