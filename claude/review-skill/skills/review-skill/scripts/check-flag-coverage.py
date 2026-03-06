#!/usr/bin/env python3
"""check-flag-coverage.py - Verify flag documentation consistency in SKILL.md.

Compares three zones where flags are declared:
  1. argument-hint frontmatter field (autocomplete hint)
  2. Arguments section in SKILL.md body (formal documentation)
  3. Workflow/body text outside Arguments and Examples (actual usage)

Sub-checks:
  FC-HINT-DOC:     Every --flag in argument-hint appears in Arguments section
  FC-DOC-HINT:     Every --flag in Arguments section appears in argument-hint
  FC-DOC-WORKFLOW: Every --flag in Arguments section is referenced in workflow body

Usage:
    ./check-flag-coverage.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes: 0 = all pass, 1 = any fail, 2 = usage error.
"""

import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Parsing infrastructure
# ---------------------------------------------------------------------------

FLAG_RE = re.compile(r"--[a-zA-Z][\w-]*")


def find_skill_md(skill_dir: str) -> str:
    """Find SKILL.md in the given directory."""
    path = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(path):
        return path
    return ""


def read_file(path: str) -> str:
    """Read file contents, return empty string on failure."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def extract_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter between --- delimiters.

    Handles single-line values and block scalars (>- and >).
    Returns dict of field -> value (string).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    else:
        return {}

    result: dict = {}
    current_key = ""
    block_lines: list = []
    in_block = False

    for line in fm_lines:
        # Top-level field
        m = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if m:
            # Flush previous block scalar
            if in_block and current_key:
                result[current_key] = " ".join(block_lines).strip()
                block_lines = []
                in_block = False

            key = m.group(1)
            val = m.group(2).strip()

            # Block scalar indicator
            if val in (">-", ">", "|", "|-"):
                current_key = key
                in_block = True
                continue

            # Strip surrounding quotes
            if len(val) >= 2:
                if (val[0] == '"' and val[-1] == '"') or \
                   (val[0] == "'" and val[-1] == "'"):
                    val = val[1:-1]

            result[key] = val
            current_key = key
        elif in_block and line and line[0].isspace():
            block_lines.append(line.strip())

    # Flush trailing block scalar
    if in_block and current_key:
        result[current_key] = " ".join(block_lines).strip()

    return result


def extract_body(content: str) -> str:
    """Everything after the second --- delimiter."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            count += 1
            if count == 2:
                return "\n".join(lines[i + 1:])
    return content


def extract_flags(text: str) -> set:
    """Extract all --flag patterns from text."""
    return set(FLAG_RE.findall(text))


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

def _build_fence_set(lines: list) -> set:
    """Return set of line indices that are inside fenced code blocks."""
    fenced: set = set()
    in_fence = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*```", line):
            fenced.add(i)
            in_fence = not in_fence
            continue
        if in_fence:
            fenced.add(i)
    return fenced


def find_section(lines: list, pattern: str,
                 fenced=None) -> tuple:
    """Find section by header regex, return (start_idx, end_idx).

    Matches ## or ### headers outside fenced code blocks. The section
    ends at the next header of equal or higher level, or end of file.
    """
    if fenced is None:
        fenced = _build_fence_set(lines)

    start = None
    header_level = None

    for i, line in enumerate(lines):
        if i in fenced:
            continue
        header_match = re.match(r"^(#{1,6})\s+", line)

        if start is None:
            if header_match and re.search(pattern, line, re.IGNORECASE):
                start = i
                header_level = len(header_match.group(1))
        else:
            if header_match and len(header_match.group(1)) <= header_level:
                return (start, i)

    if start is not None:
        return (start, len(lines))
    return (None, None)


def find_all_sections(lines: list, pattern: str,
                      fenced=None) -> list:
    """Find all sections matching pattern, return list of (start, end) tuples."""
    if fenced is None:
        fenced = _build_fence_set(lines)

    sections = []
    i = 0
    while i < len(lines):
        if i in fenced:
            i += 1
            continue
        header_match = re.match(r"^(#{1,6})\s+", lines[i])
        if header_match and re.search(pattern, lines[i], re.IGNORECASE):
            start = i
            level = len(header_match.group(1))
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if j in fenced:
                    continue
                hm = re.match(r"^(#{1,6})\s+", lines[j])
                if hm and len(hm.group(1)) <= level:
                    end = j
                    break
            sections.append((start, end))
            i = end
        else:
            i += 1
    return sections


# ---------------------------------------------------------------------------
# Zone extraction
# ---------------------------------------------------------------------------

def get_arguments_section_flags(body_lines: list,
                                fenced: set) -> set:
    """Extract --flag patterns from the Arguments section."""
    start, end = find_section(body_lines, r"\barguments\b", fenced)
    if start is None:
        return set()
    section_text = "\n".join(body_lines[start:end])
    return extract_flags(section_text)


def get_workflow_flags(body_lines: list, fenced: set) -> set:
    """Extract --flag patterns from body excluding Arguments and Example sections.

    The 'workflow zone' includes everything EXCEPT:
    - The Arguments section
    - Example Invocations / Example sections at the end
    - Bundled resources listings
    """
    # Identify sections to exclude
    args_start, args_end = find_section(
        body_lines, r"\barguments\b", fenced
    )

    exclude_ranges = []
    if args_start is not None:
        exclude_ranges.append((args_start, args_end))

    # Exclude all example-like sections
    for pattern in [r"\bexample\s+invocations?\b", r"\bexamples?\b"]:
        for s, e in find_all_sections(body_lines, pattern, fenced):
            exclude_ranges.append((s, e))

    # Exclude bundled resources section
    for s, e in find_all_sections(
        body_lines, r"\bbundled\s+resources\b", fenced
    ):
        exclude_ranges.append((s, e))

    # Build workflow text from non-excluded lines
    workflow_lines = []
    for i, line in enumerate(body_lines):
        excluded = False
        for rs, re_ in exclude_ranges:
            if rs <= i < re_:
                excluded = True
                break
        if not excluded:
            workflow_lines.append(line)

    return extract_flags("\n".join(workflow_lines))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def emit(check: str, passed: bool, detail: str) -> dict:
    """Build a check result dict."""
    return {"check": check, "pass": passed, "detail": detail}


def emit_json(obj: dict) -> None:
    """Print a JSON object as a single line."""
    print(json.dumps(obj, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check-flag-coverage.py <skill-directory>", file=sys.stderr)
        sys.exit(2)

    skill_dir = sys.argv[1]
    skill_md_path = find_skill_md(skill_dir)

    if not skill_md_path:
        emit_json(emit("flag-coverage", True, "No SKILL.md found"))
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    content = read_file(skill_md_path)
    if not content:
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    fm = extract_frontmatter(content)
    body = extract_body(content)
    body_lines = body.splitlines()

    # Pre-compute fenced code block line indices
    fenced = _build_fence_set(body_lines)

    # Extract flags from each zone
    hint_raw = fm.get("argument-hint", "")
    hint_flags = extract_flags(hint_raw)
    doc_flags = get_arguments_section_flags(body_lines, fenced)
    workflow_flags = get_workflow_flags(body_lines, fenced)

    total = 0
    passed = 0
    failed = 0

    # No flags anywhere — nothing to check
    if not hint_flags and not doc_flags:
        emit_json({"summary": True, "total": 0, "passed": 0, "failed": 0})
        sys.exit(0)

    # FC-HINT-DOC: flags in argument-hint must be in Arguments section
    if hint_flags:
        if doc_flags:
            missing = sorted(hint_flags - doc_flags)
            if missing:
                detail = (
                    f"Flags in argument-hint not documented in Arguments section: "
                    f"{', '.join(missing)}"
                )
                emit_json(emit("FC-HINT-DOC", False, detail))
                failed += 1
            else:
                emit_json(emit(
                    "FC-HINT-DOC", True,
                    f"All {len(hint_flags)} argument-hint flags documented"
                ))
                passed += 1
        else:
            detail = (
                f"argument-hint has {len(hint_flags)} flags but no Arguments "
                f"section found in body"
            )
            emit_json(emit("FC-HINT-DOC", False, detail))
            failed += 1
        total += 1

    # FC-DOC-HINT: flags in Arguments section must be in argument-hint
    if doc_flags:
        if hint_flags:
            missing = sorted(doc_flags - hint_flags)
            if missing:
                detail = (
                    f"Flags in Arguments section missing from argument-hint: "
                    f"{', '.join(missing)}"
                )
                emit_json(emit("FC-DOC-HINT", False, detail))
                failed += 1
            else:
                emit_json(emit(
                    "FC-DOC-HINT", True,
                    f"All {len(doc_flags)} documented flags in argument-hint"
                ))
                passed += 1
        elif not hint_raw:
            detail = (
                f"Arguments section documents {len(doc_flags)} flags but "
                f"argument-hint field is missing from frontmatter"
            )
            emit_json(emit("FC-DOC-HINT", False, detail))
            failed += 1
        else:
            # argument-hint exists but has no --flags (only positional args)
            detail = (
                f"Arguments section documents {len(doc_flags)} flags but "
                f"argument-hint has none: {', '.join(sorted(doc_flags))}"
            )
            emit_json(emit("FC-DOC-HINT", False, detail))
            failed += 1
        total += 1

    # FC-DOC-WORKFLOW: flags in Arguments section must appear in workflow body
    if doc_flags:
        unreferenced = sorted(doc_flags - workflow_flags)
        if unreferenced:
            detail = (
                f"Flags documented but not referenced in workflow: "
                f"{', '.join(unreferenced)}"
            )
            emit_json(emit("FC-DOC-WORKFLOW", False, detail))
            failed += 1
        else:
            emit_json(emit(
                "FC-DOC-WORKFLOW", True,
                f"All {len(doc_flags)} documented flags referenced in workflow"
            ))
            passed += 1
        total += 1

    emit_json({"summary": True, "total": total, "passed": passed, "failed": failed})
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
