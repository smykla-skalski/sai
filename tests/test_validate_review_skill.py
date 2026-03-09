from __future__ import annotations

import importlib
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

import _skill_check_common  # noqa: E402
import validate  # noqa: E402
from _skill_check_common import (  # noqa: E402
    CheckRecord,
    SkillDocument,
)


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
    with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
        validate.run_frontmatter(doc, collector)
    return collector, records


def _find_check(records: list[dict[str, object]], check_id: str) -> dict[str, object]:
    """Find a record by check ID, raising if not found."""
    for record in records:
        if record.get("check") == check_id:
            return record
    raise AssertionError(f"No record with check_id={check_id!r} found")


# ---------------------------------------------------------------------------
# Existing tests (preserved)
# ---------------------------------------------------------------------------


class ValidateScriptTests(unittest.TestCase):
    def test_frontmatter_missing_fields_emits_all_checks(self) -> None:
        doc = _make_doc()
        collector, records = _run_frontmatter(doc)

        self.assertEqual(collector.total, 11)
        self.assertEqual(len(records), 11)
        self.assertEqual(
            sum(1 for record in records if record["check"] == "FM-name-format"), 1
        )
        self.assertEqual(
            sum(
                1 for record in records if record["check"] == "FM-desc-voice"
            ),
            1,
        )
        self.assertEqual(
            sum(1 for record in records if record["check"] == "FM-name-reserved"), 1
        )
        self.assertEqual(
            sum(1 for record in records if record["check"] == "FM-desc-no-xml"), 1
        )

    def test_missing_structure_delegate_emits_runtime_failure(self) -> None:
        config = validate.DelegateConfig(script="does-not-exist.py")
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []

        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            validate._run_structure_delegate(
                config,
                SCRIPT_DIR,
                Path("/virtual/skill"),
                collector,
            )

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "XX-runtime")
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
                patch.object(_skill_check_common, "emit_record", side_effect=records.append),
                patch.object(
                    validate, "_run_and_validate_script",
                    return_value=(fake_run, None),
                ),
            ):
                validate._handle_lint_scripts(script_dir, skill_dir, collector)

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "CL-aggregate")
        self.assertIs(records[0]["pass"], False)
        self.assertIn("Summary missing integer 'findings'", str(records[0]["detail"]))

    def test_load_error_preserves_detail_and_usage_exit_code(self) -> None:
        records: list[dict[str, object]] = []

        with (
            patch.object(_skill_check_common, "emit_record", side_effect=records.append),
            patch.object(
                validate,
                "load_skill_document",
                side_effect=validate.SkillLoadError("Custom load failure"),
            ),
        ):
            exit_code = validate.main(["/virtual/missing"])

        self.assertEqual(exit_code, validate.EXIT_USAGE_ERROR)
        self.assertEqual(records[0]["check"], "FM-skill-md-exists")
        self.assertIn("Custom load failure", str(records[0]["detail"]))
        self.assertEqual(records[-1].get("kind"), "summary")

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

        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed,
                collector,
                script="check-preprocessing.py",
                guard_field="directives",
            )

        self.assertEqual(collector.failed, 1)
        self.assertEqual(records[0]["check"], "PP-runtime")
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
        present = _find_check(records, "FM-name-present")
        fmt = _find_check(records, "FM-name-format")
        match = _find_check(records, "FM-name-matches-dir")
        self.assertTrue(present["pass"])
        self.assertTrue(fmt["pass"])
        self.assertTrue(match["pass"])

    def test_name_too_long(self) -> None:
        long_name = "a" * 65
        doc = _make_doc(frontmatter={"name": long_name})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "FM-name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("exceeds", str(fmt["detail"]))

    def test_name_invalid_chars(self) -> None:
        doc = _make_doc(frontmatter={"name": "Bad_Name"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "FM-name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("invalid characters", str(fmt["detail"]))

    def test_name_leading_trailing_hyphen(self) -> None:
        doc = _make_doc(frontmatter={"name": "-bad-name-"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "FM-name-format")
        self.assertFalse(fmt["pass"])
        # The regex catches this as invalid chars first (uppercase pattern)
        # since -bad-name- does match [a-z0-9-]+, it should hit the hyphen check
        self.assertIn("hyphen", str(fmt["detail"]))

    def test_name_consecutive_hyphens(self) -> None:
        doc = _make_doc(frontmatter={"name": "bad--name"})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "FM-name-format")
        self.assertFalse(fmt["pass"])
        self.assertIn("consecutive", str(fmt["detail"]))

    def test_name_dir_mismatch(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "other-name"},
            skill_dir="/virtual/fake-skill",
        )
        _, records = _run_frontmatter(doc)
        match = _find_check(records, "FM-name-matches-dir")
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
        present = _find_check(records, "FM-desc-present")
        length = _find_check(records, "FM-desc-length")
        trigger = _find_check(records, "FM-desc-trigger")
        self.assertTrue(present["pass"])
        self.assertTrue(length["pass"])
        self.assertTrue(trigger["pass"])

    def test_description_too_long(self) -> None:
        long_desc = "x" * 1025
        doc = _make_doc(frontmatter={"description": long_desc})
        _, records = _run_frontmatter(doc)
        length = _find_check(records, "FM-desc-length")
        self.assertFalse(length["pass"])
        self.assertIn("exceeds", str(length["detail"]))

    def test_description_no_trigger_phrase(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "Generate daily reports from data"},
        )
        _, records = _run_frontmatter(doc)
        trigger = _find_check(records, "FM-desc-trigger")
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
        trigger = _find_check(records, "FM-desc-trigger")
        self.assertTrue(trigger["pass"])
        self.assertIn("disable-model-invocation", str(trigger["detail"]))

    def test_description_first_person_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "I can generate reports for you"},
        )
        _, records = _run_frontmatter(doc)
        voice = _find_check(records, "FM-desc-voice")
        self.assertFalse(voice["pass"])

    def test_description_second_person_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"description": "You can use this to generate reports"},
        )
        _, records = _run_frontmatter(doc)
        voice = _find_check(records, "FM-desc-voice")
        self.assertFalse(voice["pass"])


# ---------------------------------------------------------------------------
# Frontmatter: allowed-tools, user-invocable
# ---------------------------------------------------------------------------


class AllowedToolsTests(unittest.TestCase):
    def test_allowed_tools_present(self) -> None:
        doc = _make_doc(frontmatter={"allowed-tools": "Bash, Read"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-tools-present")
        self.assertTrue(check["pass"])

    def test_allowed_tools_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-tools-present")
        self.assertFalse(check["pass"])


class UserInvocableTests(unittest.TestCase):
    def test_user_invocable_valid(self) -> None:
        doc = _make_doc(frontmatter={"user-invocable": "true"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-invocable-present")
        self.assertTrue(check["pass"])

    def test_user_invocable_invalid_value(self) -> None:
        doc = _make_doc(frontmatter={"user-invocable": "maybe"})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-invocable-present")
        self.assertFalse(check["pass"])
        self.assertIn("must be boolean", str(check["detail"]))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


class ParseNdjsonLineTests(unittest.TestCase):
    def test_valid_json(self) -> None:
        result = validate._parse_ndjson_line('{"check": "foo", "pass": true}')
        assert result is not None
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
            json.dumps({
                "kind": "check", "check": "XX-test", "pass": True,
                "level": "pass", "detail": "Test passed",
            }),
            json.dumps({
                "kind": "summary", "total": 1, "passed": 1, "failed": 0,
            }),
        ]
        parsed = validate._parse_delegate_output("\n".join(lines))
        self.assertEqual(len(parsed.checks), 1)
        self.assertEqual(parsed.checks[0].check, "XX-test")
        self.assertIsNotNone(parsed.summary)
        self.assertEqual(len(parsed.invalid_lines), 0)

    def test_duplicate_summary(self) -> None:
        lines = [
            json.dumps({"kind": "summary", "total": 0, "passed": 0, "failed": 0}),
            json.dumps({"kind": "summary", "total": 0, "passed": 0, "failed": 0}),
        ]
        parsed = validate._parse_delegate_output("\n".join(lines))
        self.assertIsNotNone(parsed.summary)
        self.assertEqual(len(parsed.invalid_lines), 1)


class ParseLintOutputTests(unittest.TestCase):
    def test_valid_output(self) -> None:
        lines = [
            json.dumps({
                "kind": "finding", "check": "CL-S01",
                "message": "Issue found", "severity": "critical",
                "file": "test.sh", "line": 1,
            }),
            json.dumps({"kind": "summary", "findings": 1}),
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
        assert error is not None
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
        assert error is not None
        self.assertIn("No stdout", error)

    def test_total_mismatch(self) -> None:
        ndjson = "\n".join([
            json.dumps({
                "kind": "check", "check": "XX-test", "pass": True,
                "level": "pass", "detail": "Test passed",
            }),
            json.dumps({
                "kind": "summary", "total": 5, "passed": 5, "failed": 0,
            }),
        ])
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=0, stdout=ndjson, stderr="",
        )
        with patch.object(validate, "_run_script", return_value=fake_run):
            parsed, error = validate._collect_delegate_output(
                Path("/virtual/script.py"), Path("/virtual/skill"),
            )
        self.assertIsNone(parsed)
        assert error is not None
        self.assertIn("total mismatch", error)


class EmitDelegateChecksTests(unittest.TestCase):
    def test_guard_zero_skips(self) -> None:
        parsed = validate.ParsedDelegateOutput(
            checks=(
                CheckRecord(check="XX-test", passed=True, detail="Test passed"),
            ),
            summary={
                "kind": "summary", "total": 1, "passed": 1,
                "failed": 0, "refs": 0,
            },
            invalid_lines=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed, collector, script="test.py", guard_field="refs",
            )
        self.assertEqual(collector.total, 0)
        self.assertEqual(len(records), 0)

    def test_guard_positive_emits(self) -> None:
        parsed = validate.ParsedDelegateOutput(
            checks=(
                CheckRecord(check="XX-test", passed=True, detail="Test passed"),
            ),
            summary={
                "kind": "summary", "total": 1, "passed": 1,
                "failed": 0, "refs": 2,
            },
            invalid_lines=(),
        )
        collector = validate.ResultCollector()
        records: list[dict[str, object]] = []
        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            validate._emit_delegate_checks(
                parsed, collector, script="test.py", guard_field="refs",
            )
        self.assertEqual(collector.total, 1)
        self.assertEqual(records[0]["check"], "XX-test")


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
            with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        self.assertEqual(collector.total, 1)
        check = _find_check(records, "CL-aggregate")
        self.assertTrue(check["pass"])

    def test_zero_findings_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "skill"
            (skill_dir / "scripts").mkdir(parents=True)

            fake_run = validate.ScriptRunResult(
                ok=True, returncode=0,
                stdout=json.dumps({
                    "kind": "summary", "findings": 0,
                }) + "\n",
                stderr="",
            )

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            with (
                patch.object(_skill_check_common, "emit_record", side_effect=records.append),
                patch.object(
                    validate, "_run_and_validate_script",
                    return_value=(fake_run, None),
                ),
            ):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        check = _find_check(records, "CL-aggregate")
        self.assertTrue(check["pass"])

    def test_findings_present_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            skill_dir = Path(tmp_dir) / "skill"
            (skill_dir / "scripts").mkdir(parents=True)

            finding = json.dumps({
                "kind": "finding", "check": "CL-S01",
                "message": "Bad pattern", "severity": "critical",
                "file": "test.sh", "line": 1,
            })
            summary = json.dumps({
                "kind": "summary", "findings": 1,
            })
            fake_run = validate.ScriptRunResult(
                ok=True, returncode=1,
                stdout=f"{finding}\n{summary}\n",
                stderr="",
            )

            collector = validate.ResultCollector()
            records: list[dict[str, object]] = []
            with (
                patch.object(_skill_check_common, "emit_record", side_effect=records.append),
                patch.object(
                    validate, "_run_and_validate_script",
                    return_value=(fake_run, None),
                ),
            ):
                validate._handle_lint_scripts(SCRIPT_DIR, skill_dir, collector)

        check = _find_check(records, "CL-aggregate")
        self.assertFalse(check["pass"])
        self.assertIn("critical", str(check["detail"]))


class ForkCandidateHandlerTests(unittest.TestCase):
    def test_strong_recommendation_passes(self) -> None:
        summary_line = json.dumps({
            "kind": "summary",
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
            patch.object(_skill_check_common, "emit_record", side_effect=records.append),
            patch.object(
                validate, "_run_and_validate_script",
                return_value=(fake_run, None),
            ),
        ):
            validate._handle_fork_candidate(SCRIPT_DIR, Path("/virtual/skill"), collector)

        check = _find_check(records, "FK-recommendation-info")
        self.assertTrue(check["pass"])
        self.assertIn("INFO:", str(check["detail"]))

    def test_none_recommendation_passes(self) -> None:
        summary_line = json.dumps({
            "kind": "summary",
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
            patch.object(_skill_check_common, "emit_record", side_effect=records.append),
            patch.object(
                validate, "_run_and_validate_script",
                return_value=(fake_run, None),
            ),
        ):
            validate._handle_fork_candidate(SCRIPT_DIR, Path("/virtual/skill"), collector)

        check = _find_check(records, "FK-recommendation-info")
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
            patch.object(_skill_check_common, "emit_record", side_effect=records.append),
            patch.object(validate, "load_skill_document", return_value=doc),
        ):
            exit_code = validate.main(["/virtual/fake-skill", "frontmatter"])

        self.assertEqual(exit_code, 0)
        # Should have 11 frontmatter checks + 1 summary
        check_records = [r for r in records if "check" in r]
        self.assertEqual(len(check_records), 11)

    def test_main_structure_mode_only(self) -> None:
        """Structure mode should not emit frontmatter checks."""
        doc = _make_doc(frontmatter={})
        records: list[dict[str, object]] = []
        with (
            patch.object(_skill_check_common, "emit_record", side_effect=records.append),
            patch.object(validate, "load_skill_document", return_value=doc),
            patch.object(validate, "run_structure"),
        ):
            validate.main(["/virtual/fake-skill", "structure"])

        check_records = [r for r in records if "check" in r]
        # No frontmatter checks should appear
        fm_checks = [
            r for r in check_records
            if r["check"] in {
                "FM-name-present", "FM-name-format", "FM-name-matches-dir",
                "FM-desc-present",
            }
        ]
        self.assertEqual(len(fm_checks), 0)


# ---------------------------------------------------------------------------
# Fork candidate summary parsing
# ---------------------------------------------------------------------------


class ParseForkCandidateSummaryTests(unittest.TestCase):
    def test_recommendation_not_last_line(self) -> None:
        """B6: recommendation record doesn't need to be last."""
        lines = [
            json.dumps({
                "kind": "summary", "recommendation": "strong",
                "detail": "5 signals",
            }),
            json.dumps({
                "kind": "signal", "signal": "FK-P1",
                "type": "positive", "detected": True,
                "detail": "Phase count",
            }),
        ]
        summary, error = validate._parse_fork_candidate_summary("\n".join(lines))
        self.assertIsNone(error)
        assert summary is not None
        self.assertEqual(summary["recommendation"], "strong")

    def test_no_recommendation_field(self) -> None:
        """B6: error when no record has recommendation or kind=summary."""
        lines = [
            json.dumps({
                "kind": "signal", "signal": "FK-P1",
                "type": "positive", "detected": True,
                "detail": "Phase count",
            }),
        ]
        summary, error = validate._parse_fork_candidate_summary("\n".join(lines))
        self.assertIsNone(summary)
        assert error is not None
        self.assertIn("summary", error)


# ---------------------------------------------------------------------------
# B1: missing vs empty field distinction
# ---------------------------------------------------------------------------


class MissingVsEmptyTests(unittest.TestCase):
    def test_name_missing_says_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-name-present")
        self.assertIn("missing", str(check["detail"]))

    def test_name_empty_says_empty(self) -> None:
        doc = _make_doc(frontmatter={"name": ""})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-name-present")
        self.assertIn("empty", str(check["detail"]))

    def test_description_missing_says_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-desc-present")
        self.assertIn("missing", str(check["detail"]))

    def test_description_empty_says_empty(self) -> None:
        doc = _make_doc(frontmatter={"description": ""})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-desc-present")
        self.assertIn("empty", str(check["detail"]))

    def test_allowed_tools_missing_says_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-tools-present")
        self.assertIn("missing", str(check["detail"]))

    def test_allowed_tools_empty_says_empty(self) -> None:
        doc = _make_doc(frontmatter={"allowed-tools": ""})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-tools-present")
        self.assertIn("empty", str(check["detail"]))

    def test_user_invocable_missing_says_missing(self) -> None:
        doc = _make_doc(frontmatter={})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-invocable-present")
        self.assertIn("missing", str(check["detail"]))

    def test_user_invocable_empty_says_empty(self) -> None:
        doc = _make_doc(frontmatter={"user-invocable": ""})
        _, records = _run_frontmatter(doc)
        check = _find_check(records, "FM-invocable-present")
        self.assertIn("empty", str(check["detail"]))


# ---------------------------------------------------------------------------
# B2: passed+failed consistency
# ---------------------------------------------------------------------------


class PassedFailedConsistencyTests(unittest.TestCase):
    def test_passed_failed_mismatch_rejected(self) -> None:
        ndjson = "\n".join([
            json.dumps({
                "kind": "check", "check": "XX-test", "pass": True,
                "level": "pass", "detail": "Test passed",
            }),
            json.dumps({
                "kind": "summary", "total": 1,
                "passed": 0, "failed": 0,
            }),
        ])
        fake_run = validate.ScriptRunResult(
            ok=True, returncode=0, stdout=ndjson, stderr="",
        )
        with patch.object(validate, "_run_script", return_value=fake_run):
            parsed, error = validate._collect_delegate_output(
                Path("/virtual/script.py"), Path("/virtual/skill"),
            )
        self.assertIsNone(parsed)
        assert error is not None
        self.assertIn("passed+failed mismatch", error)


# ---------------------------------------------------------------------------
# B3: invalid argparse mode
# ---------------------------------------------------------------------------


class InvalidArgparseTests(unittest.TestCase):
    def test_invalid_mode_emits_ndjson(self) -> None:
        records: list[dict[str, object]] = []
        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            exit_code = validate.main(["/virtual/skill", "invalid-mode"])
        self.assertEqual(exit_code, validate.EXIT_USAGE_ERROR)
        self.assertTrue(len(records) > 0)
        self.assertIn("Invalid arguments", str(records[0]["detail"]))

    def test_no_args_emits_ndjson(self) -> None:
        records: list[dict[str, object]] = []
        with patch.object(_skill_check_common, "emit_record", side_effect=records.append):
            exit_code = validate.main([])
        self.assertEqual(exit_code, validate.EXIT_USAGE_ERROR)


# ---------------------------------------------------------------------------
# B4: multiple name format errors
# ---------------------------------------------------------------------------


class MultipleNameErrorTests(unittest.TestCase):
    def test_multiple_errors_joined(self) -> None:
        # Name with both too-long AND invalid chars
        long_bad = "A" * 65
        doc = _make_doc(frontmatter={"name": long_bad})
        _, records = _run_frontmatter(doc)
        fmt = _find_check(records, "FM-name-format")
        self.assertFalse(fmt["pass"])
        detail = str(fmt["detail"])
        self.assertIn("exceeds", detail)
        self.assertIn("invalid characters", detail)


# ---------------------------------------------------------------------------
# B5: empty lint fields rejected
# ---------------------------------------------------------------------------


class EmptyLintFieldTests(unittest.TestCase):
    def test_empty_check_id_rejected(self) -> None:
        lines = [
            json.dumps({"check": "", "message": "bad", "severity": "critical"}),
            json.dumps({"kind": "summary", "findings": 0}),
        ]
        parsed = validate._parse_lint_output("\n".join(lines))
        self.assertEqual(len(parsed.findings), 0)
        self.assertEqual(len(parsed.invalid_lines), 1)


# ---------------------------------------------------------------------------
# CheckRecord auto-sanitization (crash prevention)
# ---------------------------------------------------------------------------


class CheckRecordSanitizationTests(unittest.TestCase):
    """Verify CheckRecord auto-sanitizes detail instead of crashing."""

    def test_long_detail_auto_truncated(self) -> None:
        long_detail = "A" * 600
        record = CheckRecord(check="XX-test", passed=True, detail=long_detail)
        self.assertEqual(len(record.detail), 500)
        self.assertTrue(record.detail.endswith("..."))

    def test_lowercase_detail_auto_capitalized(self) -> None:
        record = CheckRecord(check="XX-test", passed=True, detail="context: fork")
        self.assertEqual(record.detail[0], "C")
        self.assertEqual(record.detail, "Context: fork")

    def test_trailing_period_auto_stripped(self) -> None:
        record = CheckRecord(check="XX-test", passed=True, detail="Found issues.")
        self.assertFalse(record.detail.endswith("."))
        self.assertEqual(record.detail, "Found issues")

    def test_multiple_trailing_periods_stripped(self) -> None:
        record = CheckRecord(check="XX-test", passed=True, detail="Found issues...")
        self.assertFalse(record.detail.endswith("."))

    def test_all_periods_replaced(self) -> None:
        record = CheckRecord(check="XX-test", passed=True, detail="...")
        self.assertTrue(len(record.detail) > 0)
        self.assertFalse(record.detail.endswith("."))

    def test_combined_long_lowercase_period(self) -> None:
        detail = "lowercase start " + "x" * 500 + "."
        record = CheckRecord(check="XX-test", passed=True, detail=detail)
        self.assertTrue(record.detail[0].isupper())
        self.assertLessEqual(len(record.detail), 500)
        # Truncation suffix "..." ends with "." but that's intentional
        self.assertTrue(record.detail.endswith("..."))

    def test_short_lowercase_period_sanitized(self) -> None:
        record = CheckRecord(
            check="XX-test", passed=True, detail="lowercase text.",
        )
        self.assertEqual(record.detail, "Lowercase text")

    def test_invalid_check_id_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            CheckRecord(check="bad", passed=True, detail="Test")

    def test_empty_detail_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            CheckRecord(check="XX-test", passed=True, detail="")

    def test_invalid_tier_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            CheckRecord(check="XX-test", passed=True, detail="Test", tier="bad")

    def test_cap_detail_under_limit(self) -> None:
        result = _skill_check_common.cap_detail("Short text")
        self.assertEqual(result, "Short text")

    def test_cap_detail_over_limit(self) -> None:
        result = _skill_check_common.cap_detail("A" * 600)
        self.assertEqual(len(result), 500)
        self.assertTrue(result.endswith("..."))

    def test_cap_detail_custom_limit(self) -> None:
        result = _skill_check_common.cap_detail("A" * 100, limit=50)
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith("..."))


# ---------------------------------------------------------------------------
# Frontmatter parsing edge cases
# ---------------------------------------------------------------------------


class FrontmatterParsingTests(unittest.TestCase):
    """Verify parse_frontmatter_lines handles block scalars and lists with blank lines."""

    def test_block_scalar_with_empty_lines(self) -> None:
        lines = [
            "description: |",
            "  line 1",
            "",
            "  line 2",
        ]
        parsed = _skill_check_common.parse_frontmatter_lines(lines)
        self.assertEqual(parsed.get("description"), "line 1\nline 2")

    def test_list_with_empty_lines(self) -> None:
        lines = [
            "allowed-tools:",
            "  - tool1",
            "",
            "  - tool2",
        ]
        parsed = _skill_check_common.parse_frontmatter_lines(lines)
        self.assertEqual(parsed.get("allowed-tools"), "tool1, tool2")


# ---------------------------------------------------------------------------
# Agent indices (find_agent_indices)
# ---------------------------------------------------------------------------


class AgentIndicesTests(unittest.TestCase):
    """Verify find_agent_indices handles multi-paragraph agent blocks."""

    def test_multi_paragraph_included(self) -> None:
        prose = _skill_check_common.extract_prose_lines(
            "Spawn a new agent with these instructions:\n"
            "First paragraph of instructions.\n"
            "\n"
            "Second paragraph of instructions."
        )
        indices = _skill_check_common.find_agent_indices(prose)
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertIn(3, indices)

    def test_exits_on_l3_heading(self) -> None:
        prose = _skill_check_common.extract_prose_lines(
            "Spawn a new agent with config:\n"
            "Do the work.\n"
            "### Next Section\n"
            "Not agent content."
        )
        indices = _skill_check_common.find_agent_indices(prose)
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertNotIn(2, indices)
        self.assertNotIn(3, indices)

    def test_exits_on_l2_heading(self) -> None:
        prose = _skill_check_common.extract_prose_lines(
            "Create the agent with prompt:\n"
            "Agent instructions here.\n"
            "## New Section\n"
            "Not agent content."
        )
        indices = _skill_check_common.find_agent_indices(prose)
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertNotIn(2, indices)
        self.assertNotIn(3, indices)

    def test_list_items_included(self) -> None:
        prose = _skill_check_common.extract_prose_lines(
            "The agent must:\n"
            "- Step one\n"
            "- Step two\n"
            "- Step three"
        )
        indices = _skill_check_common.find_agent_indices(prose)
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertIn(2, indices)
        self.assertIn(3, indices)

    def test_mixed_paragraphs_and_lists(self) -> None:
        prose = _skill_check_common.extract_prose_lines(
            "Instruct the agent to do the following:\n"
            "Overview paragraph.\n"
            "\n"
            "- Item one\n"
            "- Item two\n"
            "\n"
            "Another paragraph of instructions."
        )
        indices = _skill_check_common.find_agent_indices(prose)
        self.assertIn(0, indices)
        self.assertIn(1, indices)
        self.assertIn(3, indices)
        self.assertIn(4, indices)
        self.assertIn(6, indices)


# ---------------------------------------------------------------------------
# Flag coverage: missing vs empty section
# ---------------------------------------------------------------------------


class FlagCoverageUnitTests(unittest.TestCase):
    """Verify _check_hint_doc and _get_arguments_section_flags."""

    def setUp(self) -> None:
        self._mod = importlib.import_module("check-flag-coverage")

    def test_hint_doc_missing_section(self) -> None:
        result = self._mod._check_hint_doc({"--foo"}, None)
        assert result is not None
        self.assertFalse(result.passed)
        self.assertIn("no Arguments section found", result.detail)

    def test_hint_doc_empty_section(self) -> None:
        result = self._mod._check_hint_doc({"--foo"}, set())
        assert result is not None
        self.assertFalse(result.passed)
        self.assertIn("documents none", result.detail)

    def test_hint_doc_populated_passes(self) -> None:
        result = self._mod._check_hint_doc({"--foo"}, {"--foo"})
        assert result is not None
        self.assertTrue(result.passed)

    def test_get_arguments_section_flags_missing(self) -> None:
        lines = ["# Skill", "", "## Workflow", "", "1. Do things"]
        fenced = _skill_check_common.build_fenced_line_indices(lines)
        result = self._mod._get_arguments_section_flags(lines, fenced)
        self.assertIsNone(result)

    def test_get_arguments_section_flags_empty(self) -> None:
        lines = ["# Skill", "", "## Arguments", "", "No flags here.", "", "## Workflow"]
        fenced = _skill_check_common.build_fenced_line_indices(lines)
        result = self._mod._get_arguments_section_flags(lines, fenced)
        self.assertIsNotNone(result)
        self.assertEqual(result, set())

    def test_get_arguments_section_flags_populated(self) -> None:
        lines = [
            "# Skill", "", "## Arguments", "",
            "- `--foo` -- a flag", "", "## Workflow",
        ]
        fenced = _skill_check_common.build_fenced_line_indices(lines)
        result = self._mod._get_arguments_section_flags(lines, fenced)
        self.assertIsNotNone(result)
        self.assertEqual(result, {"--foo"})


class ReservedNameTests(unittest.TestCase):
    def test_claude_helper_fails(self) -> None:
        doc = _make_doc(frontmatter={"name": "claude-helper"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], False)
        self.assertIn("claude", str(rec["detail"]))

    def test_my_anthropic_tool_fails(self) -> None:
        doc = _make_doc(frontmatter={"name": "my-anthropic-tool"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], False)
        self.assertIn("anthropic", str(rec["detail"]))

    def test_safe_name_passes(self) -> None:
        doc = _make_doc(frontmatter={"name": "fake-skill"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], True)

    def test_missing_name_cascades(self) -> None:
        doc = _make_doc()
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], False)
        self.assertIn("Cannot validate", str(rec["detail"]))

    def test_both_reserved_words_detected(self) -> None:
        doc = _make_doc(frontmatter={"name": "claude-anthropic-bot"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], False)
        self.assertIn("claude", str(rec["detail"]))
        self.assertIn("anthropic", str(rec["detail"]))

    def test_substring_not_flagged(self) -> None:
        doc = _make_doc(frontmatter={"name": "claudette-review"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-name-reserved")
        self.assertIs(rec["pass"], True)


class DescriptionXmlTests(unittest.TestCase):
    def test_bold_tag_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "test", "description": "Generate <b>reports</b>."}
        )
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-desc-no-xml")
        self.assertIs(rec["pass"], False)

    def test_br_tag_fails(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "test", "description": "First line.<br />Second."}
        )
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-desc-no-xml")
        self.assertIs(rec["pass"], False)

    def test_clean_description_passes(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "test", "description": "Review skills. Use when auditing."}
        )
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-desc-no-xml")
        self.assertIs(rec["pass"], True)

    def test_missing_description_cascades(self) -> None:
        doc = _make_doc(frontmatter={"name": "test"})
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-desc-no-xml")
        self.assertIs(rec["pass"], False)
        self.assertIn("Cannot validate", str(rec["detail"]))

    def test_comparison_operator_not_flagged(self) -> None:
        doc = _make_doc(
            frontmatter={"name": "test", "description": "Handle cases where count < 10."}
        )
        _, records = _run_frontmatter(doc)
        rec = _find_check(records, "FM-desc-no-xml")
        self.assertIs(rec["pass"], True)


if __name__ == "__main__":
    unittest.main()
