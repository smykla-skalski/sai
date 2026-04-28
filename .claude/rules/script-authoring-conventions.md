# Script authoring conventions

This file captures conventions used across scripts in this repo and establishes defaults for future script work.

## Core defaults

- New automation scripts are Python (`.py`) with executable shebang.
- Scripts expose a clear CLI contract and deterministic machine-readable output.
- Prefer shared helpers from `_skill_check_common.py` over reimplementing parsing/output logic.
- Favor safe failure with actionable diagnostics over implicit behavior.

## Convention matrix (what, where, why)

| What | Where | Why |
| --- | --- | --- |
| Use `#!/usr/bin/env python3` and `from __future__ import annotations` | Top of almost every script | Consistent runtime and modern typing behavior |
| Start with a module docstring that includes purpose, checks, usage, output, exit codes | `check-*.py`, `validate.py`, `check-lint.py` | Makes each script self-describing and usable without opening source |
| Keep explicit section blocks with divider comments | All major scripts | Improves scanability in long files |
| Define constants in uppercase with `Final[...]` | All checkers and helpers | Removes magic numbers/strings and keeps behavior centralized |
| Precompile regex patterns once at module scope | Every parser/checker script | Better performance and easier testability |
| Use `if TYPE_CHECKING:` for type-only imports and aliases | `check-config.py`, `check-content.py`, others | Avoids runtime import overhead while keeping static typing clear |
| Model structured data with dataclasses | `_skill_check_common.py`, `validate.py`, `check-hooks.py` | Clear data contracts and reduced dict-shape bugs |
| Use `pathlib.Path` for all path handling | Entire scripts directory | Cross-platform path safety and cleaner path ops |
| Read files with UTF-8 plus replacement fallback | `_skill_check_common.py:67`, many checkers | Prevents hard failures on imperfect encoding |
| Build deterministic output order (sorted paths, stable check order) | Most checkers | Reproducible results and stable tests |
| Use check IDs with stable prefix + slug (`XX-name`) | NDJSON emitters, all checkers | Traceability across scripts and tests |
| Emit NDJSON records using shared record types | `_skill_check_common.py` + checkers | Uniform machine parsing and orchestration compatibility |
| Emit a final summary record in all modes | `emit_results`, `ResultCollector`, `check-lint.py` | Guarantees predictable post-processing |
| Keep detail messages concise, structured, and user-actionable | `CheckRecord` contract + checks | Better UX and easier issue fixing |
| Mark non-applicable checks as `skip`/`info`, not forced `pass`/`fail` | `check-best-practices.py`, others | Preserves semantic meaning in reports |
| Support selective execution with `CHECK_ORDER` + `--check` | Most `check-*.py` via `run_check_cli` | Faster local debugging and focused tests |
| Prefer small pure helper functions for parsing/detection | All larger scripts | Local reasoning and simpler unit coverage |
| Keep orchestration separate from check implementation | `run_checks(...)` pattern in all checkers | Easier extension and lower coupling |
| Use explicit exit codes (`0` pass, `1` findings, `2` usage/input errors) | All scripts | Predictable CI and shell integration |
| Convert parser/load failures into usage errors with clear stderr output | `run_check_cli`, `validate.py`, `check-hooks.py` | Better operator feedback without stack traces |
| Guard subprocess calls with timeout and structured error handling | `validate.py`, `check-lint.py` | Avoids hangs and makes failures diagnosable |
| Validate external tool output before trusting it | `validate.py` delegate parsers | Prevents orchestration from accepting malformed delegate output |
| Skip optional integrations when tool is missing | `check-lint.py` (`shellcheck`, `ruff`) | Portable behavior across environments |
| Keep scans context-aware (ignore fenced blocks, comments, optional sections) | `check-content.py`, `check-flag-coverage.py`, `check-best-practices.py` | Reduces false positives |
| Prefer accumulated findings over early exit in scanners | `check-lint.py`, many checkers | Gives full report in one run |
| Use line-based evidence with compact snippets (`L<n>: ...`) | `_skill_check_common.py:142`, multiple checks | Fast navigation from finding to source |
| Keep script output channel discipline (`stdout` for records, `stderr` for diagnostics) | All CLI scripts | Clean machine parsing and safe human diagnostics |

## Standard checker structure

Use this as the default shape for a new checker script:

```python
#!/usr/bin/env python3
"""Validate <topic> checks for SKILL.md."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from _skill_check_common import CheckRecord, SkillDocument, run_check_cli

CHECK_ONE: Final[str] = "XX-one"
CHECK_TWO: Final[str] = "XX-two"

CHECK_ORDER: Final[tuple[str, ...]] = (
    CHECK_ONE,
    CHECK_TWO,
)


def check_one(document: SkillDocument) -> CheckRecord:
    return CheckRecord(check=CHECK_ONE, passed=True, detail="...", tier="I00")


def check_two(document: SkillDocument) -> CheckRecord:
    return CheckRecord(check=CHECK_TWO, passed=True, detail="...", tier="I00")


def run_checks(
    document: SkillDocument,
    selected_checks: tuple[str, ...] = (),
) -> list[CheckRecord]:
    selected = frozenset(selected_checks)
    results: list[CheckRecord] = []
    for check_name in CHECK_ORDER:
        if selected and check_name not in selected:
            continue
        if check_name == CHECK_ONE:
            results.append(check_one(document))
        elif check_name == CHECK_TWO:
            results.append(check_two(document))
    return results


def main(argv: list[str] | None = None) -> int:
    return run_check_cli(
        "Validate <topic> checks for a skill directory",
        CHECK_ORDER,
        run_checks,
        argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

## Quality guardrails to keep

- Keep checks deterministic - no dependence on wall-clock time or unordered iteration.
- Avoid mutating repo state in validation scripts.
- Treat malformed input and malformed delegated output as first-class failure modes.
- Keep messages precise: what failed, where it failed, and what to change.
- Prefer explicit helper names over compact one-liners in critical parsing logic.

## When to diverge from this pattern

- Use custom CLI parsing when orchestration needs modes, verbosity, or multiple execution paths (`validate.py`, `check-lint.py`).
- Use custom emit logic only when record type differs from check records (for example `signal`/`finding` records).
- Use script-local parsing only when shared helpers do not cover the required structure (example: hook YAML state machine in `check-hooks.py`).
