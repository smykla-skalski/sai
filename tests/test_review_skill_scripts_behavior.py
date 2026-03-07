from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = (
    REPO_ROOT / "claude" / "review-skill" / "skills" / "review-skill" / "scripts"
)
SELF_SKILL_DIR = REPO_ROOT / "claude" / "review-skill" / "skills" / "review-skill"

RUN_CHECK_SCRIPTS = (
    "check-ask-user.py",
    "check-best-practices.py",
    "check-config.py",
    "check-content.py",
    "check-file-refs.py",
    "check-flag-coverage.py",
    "check-fork-candidate.py",
    "check-hooks.py",
    "check-preprocessing.py",
    "check-read-gates.py",
    "check-references.py",
    "check-scripts-dir.py",
)


def _build_skill_md(frontmatter: dict[str, str], body: str) -> str:
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


class ScriptTestCase(unittest.TestCase):
    def create_skill(
        self,
        tmp_dir: Path,
        *,
        dir_name: str = "sample-skill",
        frontmatter_overrides: dict[str, str] | None = None,
        body: str = "# Sample\n\n## Workflow\n\n1. Read input",
        files: dict[str, str] | None = None,
        executable_paths: set[str] | None = None,
    ) -> Path:
        skill_dir = tmp_dir / dir_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "name": dir_name,
            "description": "Sample skill for script testing. Use when validating checks.",
            "allowed-tools": "Read",
            "user-invocable": "true",
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
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                self.fail(
                    f"Command emitted non-JSON line: {line!r} ({error})",
                )
            self.assertIsInstance(payload, dict)
            records.append(payload)

        self.assertTrue(records, f"No NDJSON output for command: {command}")
        self.assertEqual(records[-1].get("kind"), "summary")
        self.assertIn(result.returncode, (0, 1), f"stderr: {result.stderr}")
        return result, records

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

    def run_validate(
        self,
        skill_dir: Path,
        mode: str = "all",
    ) -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
        command = [str(SCRIPTS_DIR / "validate.py"), str(skill_dir)]
        if mode != "all":
            command.append(mode)
        return self.run_ndjson(command)

    def check_records(
        self, records: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        return [record for record in records if record.get("kind") == "check"]

    def summary_record(self, records: list[dict[str, object]]) -> dict[str, object]:
        return records[-1]

    def one_check(
        self,
        records: list[dict[str, object]],
        check_id: str,
    ) -> dict[str, object]:
        matches = [
            record
            for record in self.check_records(records)
            if record.get("check") == check_id
        ]
        self.assertEqual(
            len(matches),
            1,
            f"Expected exactly one {check_id} record, got {len(matches)}",
        )
        return matches[0]

    def assert_summary_consistent(self, records: list[dict[str, object]]) -> None:
        checks = self.check_records(records)
        signals = [record for record in records if record.get("kind") == "signal"]
        summary = self.summary_record(records)
        self.assertEqual(summary.get("total"), len(checks) + len(signals))
        self.assertEqual(
            summary.get("failed"),
            sum(1 for record in checks if record.get("pass") is False),
        )
        if "info" in summary:
            self.assertEqual(
                summary.get("info"),
                sum(1 for record in checks if record.get("level") == "info")
                + len(signals),
            )


class ScriptNdjsonContractTests(ScriptTestCase):
    def test_all_checker_scripts_emit_valid_ndjson_and_consistent_summaries(
        self,
    ) -> None:
        for script_name in RUN_CHECK_SCRIPTS:
            with self.subTest(script=script_name):
                _, records = self.run_checker(script_name, SELF_SKILL_DIR)
                self.assert_summary_consistent(records)

    def test_validate_emits_valid_ndjson_and_consistent_summary(self) -> None:
        _, records = self.run_validate(SELF_SKILL_DIR, "all")
        self.assert_summary_consistent(records)

    def test_check_lint_json_mode_emits_findings_and_summary(self) -> None:
        command = [
            str(SCRIPTS_DIR / "check-lint.py"),
            str(SCRIPTS_DIR),
            "--json",
            "--no-shellcheck",
            "--no-ruff",
        ]
        result, records = self.run_ndjson(command)
        self.assertIn(result.returncode, (0, 1))
        summary = self.summary_record(records)
        self.assertIn("findings", summary)


class ConfigScriptBehaviorTests(ScriptTestCase):
    def test_state_path_bad_relative_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Skill\n\n## Workflow\n\n"
                    "1. Store persistent state in ./findings/state.json"
                ),
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-state-xdg",),
            )

        record = self.one_check(records, "CF-state-xdg")
        self.assertIs(record.get("pass"), False)
        self.assertIn("relative paths", str(record.get("detail")))

    def test_state_path_xdg_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=(
                    "# Skill\n\n## Workflow\n\n"
                    "1. Store persistent state in "
                    "${XDG_DATA_HOME:-$HOME/.local/share}/sai/plugin/state.json"
                ),
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-state-xdg",),
            )

        record = self.one_check(records, "CF-state-xdg")
        self.assertIs(record.get("pass"), True)

    def test_tools_usage_detects_implicit_usage_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={
                    "allowed-tools": (
                        "Task, ToolSearch, AskUserQuestion, Glob, Grep, "
                        "Write, Edit, WebSearch, WebFetch, Agent"
                    ),
                },
                body=(
                    "# Skill\n\n## Workflow\n\n"
                    "1. Spawn a subagent to triage\n"
                    "2. Use mcp__registry__list to inspect available tools\n"
                    "3. Ask the user to choose one option\n"
                    "4. Use glob to find files\n"
                    "5. Search content in matching files\n"
                    "6. Write output file report.md\n"
                    "7. Edit file summary.md\n"
                    "8. Search web for source material\n"
                    "9. Fetch URL https://example.com/context.md\n"
                    "10. Launch a background agent for verification"
                ),
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-tools-usage",),
            )

        record = self.one_check(records, "CF-tools-usage")
        self.assertIs(record.get("pass"), True)

    def test_tools_usage_fails_when_high_signal_tools_are_unused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={
                    "allowed-tools": "Glob, Grep, Write, Edit",
                },
                body="# Skill\n\n## Workflow\n\n1. Read input and summarize",
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-tools-usage",),
            )

        record = self.one_check(records, "CF-tools-usage")
        self.assertIs(record.get("pass"), False)
        self.assertIn("Glob", str(record.get("detail")))

    def test_side_effect_api_signal_requires_dmi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body="# Skill\n\n## Workflow\n\n1. Use GitHub create comment on an issue",
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-side-effect",),
            )

        record = self.one_check(records, "CF-side-effect")
        self.assertIs(record.get("pass"), False)
        self.assertIn("api=", str(record.get("detail")))

    def test_side_effect_api_signal_passes_with_dmi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"disable-model-invocation": "true"},
                body="# Skill\n\n## Workflow\n\n1. Use GitHub create comment on an issue",
            )
            _, records = self.run_checker(
                "check-config.py",
                skill_dir,
                checks=("CF-side-effect",),
            )

        record = self.one_check(records, "CF-side-effect")
        self.assertIs(record.get("pass"), True)
        self.assertIn("is set", str(record.get("detail")))


class BestPracticesScriptBehaviorTests(ScriptTestCase):
    def test_example_tags_fail_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp))
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-example-tags",),
            )

        record = self.one_check(records, "BP-example-tags")
        self.assertIs(record.get("pass"), False)

    def test_example_tags_emit_info_for_two_examples(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n1. Read input\n\n"
            "<example>\nInput: a\nOutput: b\n</example>\n\n"
            "<example>\nInput: c\nOutput: d\n</example>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-example-tags",),
            )

        record = self.one_check(records, "BP-example-tags")
        self.assertIs(record.get("pass"), True)
        self.assertEqual(record.get("level"), "info")

    def test_over_prompting_info_threshold_respects_heading_and_example_exclusions(
        self,
    ) -> None:
        body = (
            "# Skill\n\n"
            "## IMPORTANT Notes\n\n"
            "### Phase 1\n\n"
            "1. You MUST parse input\n"
            "2. ALWAYS validate output\n\n"
            "<example>\nInput: test\nOutput: NEVER skip checks\n</example>\n\n"
            "```bash\n"
            "echo CRITICAL\n"
            "```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-over-prompting",),
            )

        record = self.one_check(records, "BP-over-prompting")
        self.assertIs(record.get("pass"), True)
        self.assertEqual(record.get("level"), "info")

    def test_over_prompting_fails_at_three_hits(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "1. You MUST parse input\n"
            "2. ALWAYS validate output\n"
            "3. NEVER ignore malformed data"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-over-prompting",),
            )

        record = self.one_check(records, "BP-over-prompting")
        self.assertIs(record.get("pass"), False)

    def test_constraint_refresh_info_with_four_phases_and_no_reminder(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "### Phase 1\n\n1. A\n\n"
            "### Phase 2\n\n1. B\n\n"
            "### Phase 3\n\n1. C\n\n"
            "### Phase 4\n\n1. D"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-constraint-refresh-info",),
            )

        record = self.one_check(records, "BP-constraint-refresh-info")
        self.assertIs(record.get("pass"), True)
        self.assertIn("INFO:", str(record.get("detail")))

    def test_constraint_refresh_ignores_negative_instruction_context(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "### Phase 1\n\n1. Load state\n\n"
            "### Phase 2\n\n1. Process\n\n"
            "### Phase 3\n\n1. Dedup\n\n"
            "DO NOT re-read or update the file.\n\n"
            "### Phase 4\n\n1. Output"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-constraint-refresh-info",),
            )

        record = self.one_check(records, "BP-constraint-refresh-info")
        self.assertIn("INFO:", str(record.get("detail")))

    def test_constraint_refresh_ignores_output_reading_context(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "### Phase 1\n\n1. Gather\n\n"
            "### Phase 2\n\n1. Rewrite\n\n"
            "### Phase 3\n\n1. Verify\n\n"
            "Re-read the rewritten text and check:\n\n"
            "### Phase 4\n\n1. Output"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-constraint-refresh-info",),
            )

        record = self.one_check(records, "BP-constraint-refresh-info")
        self.assertIn("INFO:", str(record.get("detail")))

    def test_constraint_refresh_detects_genuine_refresh(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "### Phase 1\n\n1. Gather\n\n"
            "### Phase 2\n\n1. Process\n\n"
            "### Phase 3\n\n1. Validate\n\n"
            "Re-read the checklist section to avoid drift.\n\n"
            "### Phase 4\n\n1. Output"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-constraint-refresh-info",),
            )

        record = self.one_check(records, "BP-constraint-refresh-info")
        self.assertNotIn("INFO:", str(record.get("detail")))
        self.assertEqual(record.get("level"), "pass")

    def test_error_section_signal_detects_heading(self) -> None:
        body = "# Skill\n\n## Error handling\n\n- Report parsing errors"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-error-section-info",),
            )

        record = self.one_check(records, "BP-error-section-info")
        self.assertIs(record.get("pass"), True)
        self.assertIn("detected", str(record.get("detail")))

    def test_negative_instr_info_emits_info_level_when_no_matches(self) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Read input and process it"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-negative-instr-info",),
            )

        record = self.one_check(records, "BP-negative-instr-info")
        self.assertEqual(record.get("level"), "info")

    def test_negative_instr_info_emits_info_level_when_matches_found(self) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Do not skip validation\n2. Never ignore errors"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-negative-instr-info",),
            )

        record = self.one_check(records, "BP-negative-instr-info")
        self.assertEqual(record.get("level"), "info")

    def test_error_section_info_not_detected_emits_info_level(self) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Process input"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-error-section-info",),
            )

        record = self.one_check(records, "BP-error-section-info")
        self.assertEqual(record.get("level"), "info")

    def test_scope_boundary_info_not_detected_emits_info_level(self) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Process input"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-scope-boundary-info",),
            )

        record = self.one_check(records, "BP-scope-boundary-info")
        self.assertEqual(record.get("level"), "info")

    def test_constraint_refresh_info_skip_emits_skip_level(self) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Process input"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-constraint-refresh-info",),
            )

        record = self.one_check(records, "BP-constraint-refresh-info")
        self.assertEqual(record.get("level"), "skip")

    def test_negative_instr_info_ignores_patterns_inside_example_blocks(
        self,
    ) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n1. Process input\n\n"
            "<example>\nDo not skip this step\nNever ignore errors\n</example>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-best-practices.py",
                skill_dir,
                checks=("BP-negative-instr-info",),
            )

        record = self.one_check(records, "BP-negative-instr-info")
        self.assertIn("No negative", str(record.get("detail")))


class FlagCoverageScriptBehaviorTests(ScriptTestCase):
    def test_hint_doc_fails_when_hint_flag_missing_from_arguments(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n- `--alpha` -- option\n\n"
            "## Workflow\n\n1. Use --alpha"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"argument-hint": "[--alpha] [--beta]"},
                body=body,
            )
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-hint-doc",),
            )

        record = self.one_check(records, "FC-hint-doc")
        self.assertIs(record.get("pass"), False)
        self.assertIn("--beta", str(record.get("detail")))

    def test_doc_hint_fails_when_argument_hint_field_missing(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n- `--alpha` -- option\n\n"
            "## Workflow\n\n1. Use --alpha"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-doc-hint",),
            )

        record = self.one_check(records, "FC-doc-hint")
        self.assertIs(record.get("pass"), False)
        self.assertIn("argument-hint field is missing", str(record.get("detail")))

    def test_doc_workflow_fails_when_documented_flag_not_used(self) -> None:
        body = "# Skill\n\n## Arguments\n\n- `--alpha` -- option\n\n## Workflow\n\n1. Read input"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"argument-hint": "[--alpha]"},
                body=body,
            )
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-doc-workflow",),
            )

        record = self.one_check(records, "FC-doc-workflow")
        self.assertIs(record.get("pass"), False)

    def test_example_flags_skip_when_fewer_than_three_documented(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n"
            "- `--alpha` -- option\n"
            "- `--beta` -- option\n\n"
            "## Workflow\n\n1. Use --alpha and --beta\n\n"
            "## Example Invocations\n\n```bash\n/skill --alpha\n```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"argument-hint": "[--alpha] [--beta]"},
                body=body,
            )
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-example-flags",),
            )

        record = self.one_check(records, "FC-example-flags")
        self.assertIs(record.get("pass"), True)
        self.assertIn("skipped", str(record.get("detail")))

    def test_example_flags_fails_when_coverage_below_fifty_percent(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n"
            "- `--alpha` -- option\n"
            "- `--beta` -- option\n"
            "- `--gamma` -- option\n"
            "- `--delta` -- option\n\n"
            "## Workflow\n\n1. Use --alpha --beta --gamma --delta\n\n"
            "## Example Invocations\n\n```bash\n/skill --alpha\n```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={
                    "argument-hint": "[--alpha] [--beta] [--gamma] [--delta]",
                },
                body=body,
            )
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-example-flags",),
            )

        record = self.one_check(records, "FC-example-flags")
        self.assertIs(record.get("pass"), False)
        self.assertIn("below 50% threshold", str(record.get("detail")))

    def test_example_flags_passes_at_fifty_percent_threshold(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n"
            "- `--alpha` -- option\n"
            "- `--beta` -- option\n"
            "- `--gamma` -- option\n"
            "- `--delta` -- option\n\n"
            "## Workflow\n\n1. Use --alpha --beta --gamma --delta\n\n"
            "## Example Invocations\n\n```bash\n/skill --alpha --beta\n```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={
                    "argument-hint": "[--alpha] [--beta] [--gamma] [--delta]",
                },
                body=body,
            )
            _, records = self.run_checker(
                "check-flag-coverage.py",
                skill_dir,
                checks=("FC-example-flags",),
            )

        record = self.one_check(records, "FC-example-flags")
        self.assertIs(record.get("pass"), True)
        self.assertIn("50%", str(record.get("detail")))


class ScriptsDirBehaviorTests(ScriptTestCase):
    def test_invocation_prefix_check_fails_without_claude_skill_dir_prefix(
        self,
    ) -> None:
        body = "# Skill\n\n## Workflow\n\n1. Run scripts/run.sh"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=body,
                files={"scripts/run.sh": "#!/usr/bin/env bash\necho ok\n"},
                executable_paths={"scripts/run.sh"},
            )
            _, records = self.run_checker(
                "check-scripts-dir.py",
                skill_dir,
                checks=("SD-invocation-prefix",),
            )

        record = self.one_check(records, "SD-invocation-prefix")
        self.assertIs(record.get("pass"), False)

    def test_no_bash_prefix_check_fails_on_bash_prefixed_invocation(self) -> None:
        body = '# Skill\n\n## Workflow\n\n1. bash "${CLAUDE_SKILL_DIR}/scripts/run.sh"'
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=body,
                files={"scripts/run.sh": "#!/usr/bin/env bash\necho ok\n"},
                executable_paths={"scripts/run.sh"},
            )
            _, records = self.run_checker(
                "check-scripts-dir.py",
                skill_dir,
                checks=("SD-no-bash",),
            )

        record = self.one_check(records, "SD-no-bash")
        self.assertIs(record.get("pass"), False)

    def test_executable_check_fails_for_non_executable_shebang_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={"scripts/run.sh": "#!/usr/bin/env bash\necho ok\n"},
            )
            _, records = self.run_checker(
                "check-scripts-dir.py",
                skill_dir,
                checks=("SD-executable",),
            )

        record = self.one_check(records, "SD-executable")
        self.assertIs(record.get("pass"), False)
        self.assertIn("missing executable bit", str(record.get("detail")))

    def test_legacy_shell_info_reports_top_level_shell_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={"scripts/legacy.sh": "#!/usr/bin/env bash\necho legacy\n"},
                executable_paths={"scripts/legacy.sh"},
            )
            _, records = self.run_checker(
                "check-scripts-dir.py",
                skill_dir,
                checks=("SD-legacy-bash-info",),
            )

        record = self.one_check(records, "SD-legacy-bash-info")
        self.assertIs(record.get("pass"), True)
        self.assertIn("INFO: Found 1 top-level legacy .sh", str(record.get("detail")))


class ReferencesScriptBehaviorTests(ScriptTestCase):
    def test_body_line_limit_failure(self) -> None:
        long_body = "# Skill\n\n" + "\n".join(f"line {idx}" for idx in range(510))
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=long_body)
            _, records = self.run_checker(
                "check-references.py",
                skill_dir,
                checks=("RF-body-lines",),
            )

        record = self.one_check(records, "RF-body-lines")
        self.assertIs(record.get("pass"), False)

    def test_body_char_limit_failure(self) -> None:
        body = "# Skill\n\n" + ("x" * 20050)
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-references.py",
                skill_dir,
                checks=("RF-body-chars",),
            )

        record = self.one_check(records, "RF-body-chars")
        self.assertIs(record.get("pass"), False)

    def test_duplicate_table_signal(self) -> None:
        table = "| A | B |\n| :-- | :-- |\n| 1 | 2 |\n| 3 | 4 |"
        body = f"# Skill\n\n## Workflow\n\n{table}"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=body,
                files={"references/table.md": table},
            )
            _, records = self.run_checker(
                "check-references.py",
                skill_dir,
                checks=("RF-dup-tables-info",),
            )

        record = self.one_check(records, "RF-dup-tables-info")
        self.assertIs(record.get("pass"), True)
        self.assertIn("INFO:", str(record.get("detail")))

    def test_phase_numbering_mismatch_failure(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "### Phase 1: Discover\n\n1. Read\n\n"
            "### Phase 2: Execute\n\n1. Run"
        )
        reference = "### Phase 1: Discover\n\n### Phase 3: Verify\n"
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                body=body,
                files={"references/guide.md": reference},
            )
            _, records = self.run_checker(
                "check-references.py",
                skill_dir,
                checks=("RF-phase-numbering",),
            )

        matches = [
            record
            for record in self.check_records(records)
            if record.get("check") == "RF-phase-numbering"
        ]
        self.assertTrue(matches)
        self.assertTrue(any(record.get("pass") is False for record in matches))

    def test_long_reference_without_toc_fails(self) -> None:
        long_reference = "\n".join(f"line {idx}" for idx in range(101))
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={"references/long.md": long_reference},
            )
            _, records = self.run_checker(
                "check-references.py",
                skill_dir,
                checks=("RF-long-ref-toc",),
            )

        record = self.one_check(records, "RF-long-ref-toc")
        self.assertIs(record.get("pass"), False)


class ContentScriptBehaviorTests(ScriptTestCase):
    def test_secret_detection_fails_on_token_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={
                    "references/secret.md": (
                        "token: sk-ZYXWVUTSRQPONMLKJIHG9876543210"
                    ),
                },
            )
            _, records = self.run_checker(
                "check-content.py",
                skill_dir,
                checks=("CT-no-secrets",),
            )

        record = self.one_check(records, "CT-no-secrets")
        self.assertIs(record.get("pass"), False)

    def test_useless_echo_detection_fails_on_literal_echo_subshell(self) -> None:
        reference = '```bash\nVALUE="$(echo "literal")"\n```\n'
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                files={"references/shell.md": reference},
            )
            _, records = self.run_checker(
                "check-content.py",
                skill_dir,
                checks=("CT-no-echo",),
            )

        record = self.one_check(records, "CT-no-echo")
        self.assertIs(record.get("pass"), False)

    def test_grading_detection_fails_on_multiple_signals(self) -> None:
        body = (
            "# Skill\n\n## Workflow\n\n"
            "1. Assign 10 points for each passing criterion\n"
            "2. grade: A"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-content.py",
                skill_dir,
                checks=("CT-no-grading",),
            )

        record = self.one_check(records, "CT-no-grading")
        self.assertIs(record.get("pass"), False)

    def test_long_prose_line_fails(self) -> None:
        body = "# Skill\n\n## Workflow\n\n" + ("x" * 320)
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-content.py",
                skill_dir,
                checks=("CT-long-prose",),
            )

        record = self.one_check(records, "CT-long-prose")
        self.assertIs(record.get("pass"), False)

    def test_long_prose_check_ignores_url_table_and_fenced_lines(self) -> None:
        long_url = "https://example.com/" + ("segment/" * 70)
        long_table = "| " + ("cell | " * 70)
        body = (
            "# Skill\n\n## Workflow\n\n"
            f"{long_url}\n\n"
            f"{long_table}\n\n"
            "```bash\n"
            f"{('x' * 400)}\n"
            "```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp), body=body)
            _, records = self.run_checker(
                "check-content.py",
                skill_dir,
                checks=("CT-long-prose",),
            )

        record = self.one_check(records, "CT-long-prose")
        self.assertIs(record.get("pass"), True)


class ValidateDelegationBehaviorTests(ScriptTestCase):
    def test_validate_structure_mode_includes_new_bp_and_fc_checks(self) -> None:
        body = (
            "# Skill\n\n## Arguments\n\n"
            "- `--alpha` -- a\n"
            "- `--beta` -- b\n"
            "- `--gamma` -- c\n\n"
            "## Workflow\n\n"
            "1. Use --alpha --beta --gamma\n\n"
            "## Example Invocations\n\n```bash\n/skill --alpha\n```"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(
                Path(tmp),
                frontmatter_overrides={"argument-hint": "[--alpha] [--beta] [--gamma]"},
                body=body,
            )
            _, records = self.run_validate(skill_dir, "structure")

        check_ids = {record.get("check") for record in self.check_records(records)}
        self.assertIn("BP-example-tags", check_ids)
        self.assertIn("FC-example-flags", check_ids)

    def test_validate_frontmatter_mode_excludes_structure_delegate_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self.create_skill(Path(tmp))
            _, records = self.run_validate(skill_dir, "frontmatter")

        check_ids = {record.get("check") for record in self.check_records(records)}
        self.assertIn("FM-name-present", check_ids)
        self.assertNotIn("BP-example-tags", check_ids)
        self.assertNotIn("CF-tools-usage", check_ids)


if __name__ == "__main__":
    unittest.main()
