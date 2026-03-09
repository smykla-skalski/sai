#!/usr/bin/env python3
"""Shell-safety checks for Codex skill bundles."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path

from _skill_check_common import (
    CheckRecord,
    ResultCollector,
    SkillDocument,
    fenced_code_blocks,
    file_relative_to,
    load_skill_document,
    read_text,
)

INLINE_SHELL_LINE_LIMIT = 15
MAX_SHELL_FINDINGS = 5
RISKY_PATTERNS = (
    r"\brm\s+-rf\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\s+--force(?:-with-lease)?\b",
    r"\bgh\s+pr\s+merge\b",
    r"\bsudo\b",
    r"\bkubectl\s+apply\b",
    r"\bterraform\s+apply\b",
)
SAFETY_PATTERNS = (
    "approval",
    "approve",
    "ask the user",
    "confirm with the user",
    "sandbox_permissions=require_escalated",
    "require_escalated",
    "escalat",
)
UNQUOTED_VAR_RE = re.compile(
    r"(^|[=\s(])(\$[A-Za-z_][A-Za-z0-9_]*|\$\{[A-Za-z_][A-Za-z0-9_]*\})(?=$|[\s/:)])",
)


@dataclass(frozen=True)
class PythonShellContext:
    """Resolved import aliases relevant to shell-safety checks."""

    os_module_aliases: frozenset[str]
    os_system_aliases: frozenset[str]


def _check_python_subprocess_safe(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    unsafe: list[str] = []
    for path in _script_files(doc):
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            unsafe.append(file_relative_to(path, doc.skill_dir))
            continue
        if _has_unsafe_python_call(tree, _python_shell_context(tree)):
            unsafe.append(file_relative_to(path, doc.skill_dir))

    detail = (
        "Python scripts avoid unsafe shell= usage and os.system()."
        if not unsafe
        else "Unsafe Python shell execution found in: " + ", ".join(unsafe[:5])
    )
    return CheckRecord(
        check="SH-python-subprocess-safe",
        passed=not unsafe,
        level="critical",
        detail=detail,
    )


def _check_risky_command_flow(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    bundle_text_parts = [doc.content]
    bundle_text_parts.extend(read_text(path) for path in _script_files(doc))
    bundle_text = "\n".join(bundle_text_parts)
    found_patterns = [
        pattern
        for pattern in RISKY_PATTERNS
        if re.search(pattern, bundle_text, re.IGNORECASE)
    ]
    has_safety_language = any(token in doc.body.lower() for token in SAFETY_PATTERNS)
    passed = not found_patterns or has_safety_language
    detail = (
        "Risky commands are absent or paired with approval and escalation guidance."
        if passed
        else "Risky commands appear without approval or escalation language."
    )
    return CheckRecord(
        check="SH-risky-command-flow",
        passed=passed,
        level="critical",
        detail=detail,
    )


def _check_scripts_executable(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    non_exec = [
        file_relative_to(path, doc.skill_dir)
        for path in _script_files(doc)
        if path.stat().st_mode & 0o111 == 0
    ]
    detail = (
        "Script entrypoints are executable."
        if not non_exec
        else "Non-executable script entrypoints: " + ", ".join(non_exec[:5])
    )
    return CheckRecord(
        check="SH-scripts-executable",
        passed=not non_exec,
        level="important",
        detail=detail,
    )


def _check_pipefail(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    missing_pipefail: list[str] = []
    for path in _script_files(doc):
        if path.suffix not in {".sh", ".bash"}:
            continue
        text = read_text(path)
        has_pipeline = any(
            "|" in line and not line.lstrip().startswith("#")
            for line in text.splitlines()
        )
        if has_pipeline and "pipefail" not in text:
            missing_pipefail.append(file_relative_to(path, doc.skill_dir))

    detail = (
        "Shell scripts using pipelines declare pipefail."
        if not missing_pipefail
        else "Shell scripts with pipelines but no pipefail: "
        + ", ".join(missing_pipefail[:5])
    )
    return CheckRecord(
        check="SH-pipefail",
        passed=not missing_pipefail,
        level="important",
        detail=detail,
    )


def _check_unquoted_expansions(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    findings: list[str] = []
    for path in _script_files(doc):
        if path.suffix not in {".sh", ".bash"}:
            continue
        findings.extend(_shell_findings(path, doc.skill_dir))
        if len(findings) >= MAX_SHELL_FINDINGS:
            break

    detail = (
        "Shell scripts quote variable expansions in risky positions."
        if not findings
        else "Possible unquoted shell expansions: " + ", ".join(findings[:5])
    )
    return CheckRecord(
        check="SH-unquoted-expansions",
        passed=not findings,
        level="important",
        detail=detail,
    )


def _check_inline_shell_heavy(skill_dir: Path) -> CheckRecord:
    doc = load_skill_document(skill_dir)
    heavy_blocks: list[int] = []
    for block in fenced_code_blocks(doc.body):
        if block.info not in {"bash", "sh", "shell", "zsh"}:
            continue
        non_empty = [line for line in block.text.splitlines() if line.strip()]
        if len(non_empty) > INLINE_SHELL_LINE_LIMIT:
            heavy_blocks.append(doc.body_start_line + block.line - 1)

    detail = (
        "Inline shell snippets are small enough to keep in SKILL.md."
        if not heavy_blocks
        else (
            "Long inline shell blocks should move into scripts/. "
            "Start lines: "
            + ", ".join(str(line) for line in heavy_blocks[:MAX_SHELL_FINDINGS])
        )
    )
    return CheckRecord(
        check="SH-inline-shell-heavy",
        passed=not heavy_blocks,
        level="info",
        detail=detail,
    )


def _script_files(skill_doc: SkillDocument) -> list[Path]:
    return [
        path
        for path in skill_doc.resource_files
        if file_relative_to(path, skill_doc.skill_dir).startswith("scripts/")
        and path.suffix in {".py", ".sh", ".bash"}
    ]


def _has_unsafe_python_call(tree: ast.AST, context: PythonShellContext) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_has_unsafe_shell(node):
            return True
        if isinstance(node, ast.Call) and _call_is_os_system(node, context):
            return True
    return False


def _python_shell_context(tree: ast.AST) -> PythonShellContext:
    os_module_aliases = {"os"}
    os_system_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    os_module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name == "*":
                    os_system_aliases.add("system")
                elif alias.name == "system":
                    os_system_aliases.add(alias.asname or alias.name)

    return PythonShellContext(
        os_module_aliases=frozenset(os_module_aliases),
        os_system_aliases=frozenset(os_system_aliases),
    )


def _call_has_unsafe_shell(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "shell":
            return not (
                isinstance(keyword.value, ast.Constant) and keyword.value.value is False
            )
    return False


def _call_is_os_system(node: ast.Call, context: PythonShellContext) -> bool:
    func = node.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "system"
        and isinstance(func.value, ast.Name)
    ):
        return func.value.id in context.os_module_aliases
    return isinstance(func, ast.Name) and func.id in context.os_system_aliases


def _shell_findings(path: Path, skill_root: Path) -> list[str]:
    findings: list[str] = []
    for line_number, raw_line in enumerate(read_text(path).splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", "export ")):
            continue
        if UNQUOTED_VAR_RE.search(raw_line):
            findings.append(f"{file_relative_to(path, skill_root)}:{line_number}")
    return findings


CHECKS = {
    "SH-python-subprocess-safe": _check_python_subprocess_safe,
    "SH-risky-command-flow": _check_risky_command_flow,
    "SH-scripts-executable": _check_scripts_executable,
    "SH-pipefail": _check_pipefail,
    "SH-unquoted-expansions": _check_unquoted_expansions,
    "SH-inline-shell-heavy": _check_inline_shell_heavy,
}


def run_checks(
    skill_dir: Path,
    collector: ResultCollector,
    *,
    selected: set[str] | None = None,
) -> None:
    """Run shell-safety checks for a skill directory."""
    names = selected or set(CHECKS)
    for check_id, check_fn in CHECKS.items():
        if check_id in names:
            collector.emit(check_fn(skill_dir))


def main(argv: list[str] | None = None) -> int:
    """Run shell-safety checks as a CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("--check", action="append", dest="checks")
    args = parser.parse_args(argv)

    collector = ResultCollector()
    selected = set(args.checks) if args.checks else None
    run_checks(args.skill_dir, collector, selected=selected)
    collector.emit_summary()
    return 1 if collector.blocking_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
