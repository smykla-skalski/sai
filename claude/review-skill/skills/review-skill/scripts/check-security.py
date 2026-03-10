#!/usr/bin/env python3
"""Validate security checks for python and shell scripts in skills.

Sub-checks:
- SC-no-shell-true
- SC-no-eval-exec
- SC-no-os-system
- SC-no-yaml-load
- SC-no-pickle

Output is NDJSON, one object per line, with a summary on the final line.
Exit codes: 0 when all pass, 1 when any fail, 2 for usage/input errors.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from _skill_check_common import (
    CheckRecord,
    SkillDocument,
    read_text,
    run_check_cli,
)

# ---------------------------------------------------------------------------
# AST detectors
# ---------------------------------------------------------------------------

CHECK_SCRIPT_PATH: Final[Path] = Path(__file__).resolve()


def _has_shell_true(tree: ast.AST) -> bool:
    """Detect any call with ``shell=True`` keyword argument."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "shell":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                return True
    return False


def _has_eval_exec(tree: ast.AST) -> bool:
    """Detect direct calls to ``eval()`` and ``exec()``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            return True
    return False


def _has_attribute_call(
    tree: ast.AST,
    *,
    object_name: str,
    attribute_name: str,
) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == attribute_name
            and isinstance(func.value, ast.Name)
            and func.value.id == object_name
        ):
            return True
    return False


def _has_pickle_call(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"load", "loads", "dump", "dumps"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "pickle"
        ):
            return True
    return False


def _has_os_system(tree: ast.AST) -> bool:
    return _has_attribute_call(
        tree,
        object_name="os",
        attribute_name="system",
    )


def _has_yaml_load(tree: ast.AST) -> bool:
    return _has_attribute_call(
        tree,
        object_name="yaml",
        attribute_name="load",
    )


# ---------------------------------------------------------------------------
# Check definitions (data-driven)
# ---------------------------------------------------------------------------

_AstDetector = Callable[[ast.AST], bool]


@dataclass(frozen=True)
class _SecurityCheck:
    """A single security pattern check."""

    check_id: str
    detector: _AstDetector
    ok_detail: str
    fail_detail: str


SECURITY_CHECKS: Final[tuple[_SecurityCheck, ...]] = (
    _SecurityCheck(
        check_id="SC-no-shell-true",
        detector=_has_shell_true,
        ok_detail="No shell=True detected in scripts",
        fail_detail="Found unsafe shell=True in scripts: {files}",
    ),
    _SecurityCheck(
        check_id="SC-no-eval-exec",
        detector=_has_eval_exec,
        ok_detail="No eval() or exec() detected in scripts",
        fail_detail="Found unsafe eval/exec in scripts: {files}",
    ),
    _SecurityCheck(
        check_id="SC-no-os-system",
        detector=_has_os_system,
        ok_detail="No os.system() detected in scripts",
        fail_detail="Found unsafe os.system() in scripts: {files}",
    ),
    _SecurityCheck(
        check_id="SC-no-yaml-load",
        detector=_has_yaml_load,
        ok_detail="No yaml.load() detected in scripts",
        fail_detail="yaml.load() found in: {files} - use yaml.safe_load()",
    ),
    _SecurityCheck(
        check_id="SC-no-pickle",
        detector=_has_pickle_call,
        ok_detail="No pickle usage detected in scripts",
        fail_detail="Found unsafe pickle usage in: {files} - use JSON instead",
    ),
)

CHECK_ORDER: Final[tuple[str, ...]] = tuple(sc.check_id for sc in SECURITY_CHECKS)


# ---------------------------------------------------------------------------
# Single-pass scanner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ScanResult:
    """Aggregated scan output: hits per check ID and skipped file names."""

    hits: dict[str, list[str]]
    skipped: list[str]


def _scan_scripts(document: SkillDocument) -> _ScanResult:
    """Parse each script file once and run all detectors against it."""
    hits: dict[str, list[str]] = {sc.check_id: [] for sc in SECURITY_CHECKS}
    skipped: list[str] = []

    scripts_dir = document.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return _ScanResult(hits=hits, skipped=skipped)

    for file_path in scripts_dir.rglob("*.py"):
        if file_path.resolve() == CHECK_SCRIPT_PATH:
            continue

        content = read_text(file_path)
        if not content:
            continue

        rel = file_path.relative_to(scripts_dir).as_posix()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            skipped.append(rel)
            continue

        for sc in SECURITY_CHECKS:
            if sc.detector(tree):
                hits[sc.check_id].append(rel)

    return _ScanResult(hits=hits, skipped=skipped)


# ---------------------------------------------------------------------------
# Check runner
# ---------------------------------------------------------------------------


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...],
) -> list[CheckRecord]:
    """Run selected checks in stable output order."""
    selected = frozenset(selected_checks)
    scan = _scan_scripts(document)
    skip_suffix = ""
    if scan.skipped:
        names = ", ".join(scan.skipped)
        skip_suffix = f" ({len(scan.skipped)} file(s) skipped - syntax error: {names})"

    results: list[CheckRecord] = []
    for sc in SECURITY_CHECKS:
        if selected and sc.check_id not in selected:
            continue
        files = scan.hits[sc.check_id]
        if files:
            results.append(
                CheckRecord(
                    check=sc.check_id,
                    passed=False,
                    detail=sc.fail_detail.format(files=", ".join(files)) + skip_suffix,
                    tier="C8",
                ),
            )
        else:
            results.append(
                CheckRecord(
                    check=sc.check_id,
                    passed=True,
                    detail=sc.ok_detail + skip_suffix,
                    tier="C8",
                ),
            )
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run security checks and return the process exit code."""
    return run_check_cli(
        "Validate security checks for python scripts in skills.",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
