#!/usr/bin/env python3
"""check-ask-user.py - Validate AskUserQuestion usage in SKILL.md files.

Checks declaration/usage consistency, implicit interaction patterns,
required-arg fallbacks, spawned agent anti-patterns, option structure,
destructive confirmation, ambiguity resolution, multiSelect grouping,
and wizard loop termination.

Usage:
    ./check-ask-user.py <skill-directory>

Output: NDJSON (one JSON object per line)
    {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
Summary (final line):
    {"summary": true, "total": N, "passed": N, "failed": N}

Exit codes: 0 = all pass, 1 = any fail, 2 = usage error.
"""

import sys
import os
import re
import json


# ---------------------------------------------------------------------------
# Parsing infrastructure
# ---------------------------------------------------------------------------

def find_skill_md(skill_dir: str) -> str:
    """Find SKILL.md in the given directory."""
    path = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(path):
        return path
    return ""


def extract_frontmatter(content: str) -> dict:
    """Extract YAML-like frontmatter between --- delimiters."""
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

    result = {}
    for line in fm_lines:
        # Simple key: value parsing (handles multi-line description via >-)
        m = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            result[key] = val
    return result


def get_allowed_tools(fm: dict) -> set:
    """Parse allowed-tools into a set."""
    raw = fm.get("allowed-tools", "")
    return {t.strip() for t in raw.split(",") if t.strip()}


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


def body_line_offset(content: str) -> int:
    """Return the 1-based line number where the body starts."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return 1
    count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            count += 1
            if count == 2:
                return i + 2  # 1-based, line after second ---
    return 1


def strip_code_blocks(body: str) -> list:
    """Return list of (original_line_index, line_text) for non-code-block lines."""
    lines = body.splitlines()
    result = []
    in_fence = False
    for i, line in enumerate(lines):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            result.append((i, line))
    return result


def find_bundled_section(prose_lines: list) -> set:
    """Return set of line indices that are inside a ## Bundled section."""
    indices = set()
    in_bundled = False
    for idx, line in prose_lines:
        stripped = line.strip()
        if re.match(r"^##\s+[Bb]undled", stripped):
            in_bundled = True
            indices.add(idx)
            continue
        if in_bundled:
            if re.match(r"^##\s+", stripped) and not re.match(r"^###", stripped):
                in_bundled = False
                continue
            indices.add(idx)
    return indices


def find_spawned_agent_sections(prose_lines: list) -> set:
    """Return set of line indices inside spawned agent instruction blocks."""
    indices = set()
    agent_patterns = [
        r"[Ss]pawn\s+(a|an)\s+",
        r"[Cc]reate\s+the\s+agent\s+with",
        r"[Aa]gent\s+instructions:",
        r"[Tt]he\s+agent\s+must:",
        r"[Ii]nstruct\s+the\s+agent\s+to",
        r"[Pp]ass\s+the\s+agent:",
    ]
    in_agent = False
    blank_count = 0
    for idx, line in prose_lines:
        stripped = line.strip()
        # Check for heading exit
        if in_agent and re.match(r"^###\s+", stripped):
            in_agent = False
            continue
        # Check for blank line followed by non-indented text
        if in_agent:
            if stripped == "":
                blank_count += 1
            else:
                if blank_count > 0 and not line.startswith(" ") and not line.startswith("\t") and not line.startswith("-"):
                    # Non-indented text after blank - exit agent section
                    in_agent = False
                    blank_count = 0
                    continue
                blank_count = 0
                indices.add(idx)
        # Check for agent section start
        if not in_agent:
            for pat in agent_patterns:
                if re.search(pat, stripped):
                    in_agent = True
                    blank_count = 0
                    indices.add(idx)
                    break
    return indices


def parse_argument_table(body: str) -> list:
    """Parse markdown argument table, return list of dicts with name, default."""
    lines = body.splitlines()
    in_args = False
    table_started = False
    separator_seen = False
    args = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^##\s+[Aa]rguments", stripped):
            in_args = True
            continue
        if in_args and re.match(r"^##\s+", stripped) and not re.match(r"^###", stripped):
            break
        if not in_args:
            continue
        if not stripped.startswith("|"):
            if table_started and separator_seen:
                break
            continue
        if not table_started:
            table_started = True
            continue
        if re.match(r"^\|[\s:-]+\|", stripped):
            separator_seen = True
            continue
        if not separator_seen:
            continue
        # Parse table row
        cells = [c.strip() for c in stripped.split("|")]
        # cells[0] is empty (before first |), cells[-1] is empty (after last |)
        cells = [c for c in cells if c != ""]
        if len(cells) >= 2:
            name = cells[0].strip("`").strip()
            default = cells[1].strip("`").strip() if len(cells) >= 2 else ""
            args.append({"name": name, "default": default})
    return args


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def result(check: str, passed: bool, detail: str) -> dict:
    return {"check": check, "pass": passed, "detail": detail}


def emit(r: dict):
    print(json.dumps(r, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Sub-checks
# ---------------------------------------------------------------------------

def check_declaration_match(fm: dict, body: str, prose_lines: list,
                            bundled_indices: set, has_implicit: bool) -> dict:
    """AUQ-DECL: AskUserQuestion in allowed-tools IFF body references it."""
    tools = get_allowed_tools(fm)
    declared = "AskUserQuestion" in tools

    # Direct mention in prose (outside code blocks and bundled section)
    body_mentions = False
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        if "AskUserQuestion" in line:
            body_mentions = True
            break

    body_uses = body_mentions or has_implicit

    if declared and body_uses:
        return result("auq-declaration-match", True,
                       "AskUserQuestion declared and used in body")
    if not declared and not body_uses:
        return result("auq-declaration-match", True,
                       "AskUserQuestion not declared and not used")
    if declared and not body_uses:
        return result("auq-declaration-match", False,
                       "AskUserQuestion in allowed-tools but not referenced "
                       "in body - phantom declaration, remove from allowed-tools")
    # not declared and body_uses
    return result("auq-declaration-match", False,
                   "Body references AskUserQuestion or implies user interaction "
                   "but AskUserQuestion missing from allowed-tools")


def check_implicit_interaction(fm: dict, prose_lines: list,
                               bundled_indices: set,
                               agent_indices: set) -> tuple:
    """AUQ-IMPLICIT: Natural-language patterns implying user interaction."""
    tools = get_allowed_tools(fm)
    declared = "AskUserQuestion" in tools

    if declared:
        return (result("auq-implicit-interaction", True,
                        "AskUserQuestion in allowed-tools - implicit patterns OK"),
                False)

    strong_patterns = [
        r"\bask\s+the\s+user\b",
        r"\bask\s+user\b",
        r"\bprompt\s+the\s+user\b",
        r"\bprompt\s+user\b",
        r"\bprompt\s+interactively\b",
        r"\buse\s+AskUserQuestion\b",
        r"\bvia\s+AskUserQuestion\b",
        r"\bwith\s+AskUserQuestion\b",
    ]
    medium_patterns = [
        r"\blet\s+the\s+user\s+(choose|decide|pick|select|confirm)\b",
        r"\bget\s+(user\s+|the\s+user's\s+|explicit\s+)?(input|approval|confirmation|consent|decision)\b",
        r"\bconfirm\s+with\s+(the\s+)?user\b",
        r"\buser\s+(selects|decides|chooses|picks|approves|confirms)\b",
        r"\bpresent\s+.{0,40}\s+(to\s+the\s+user|via.*question|as\s+options)\b",
        r"\boffer\s+.{0,30}\s+options\b",
    ]
    negation_patterns = [
        r"\bdo\s+NOT\s+ask\b",
        r"\bdon't\s+ask\b",
        r"\bwithout\s+asking\b",
        r"\bdo\s+not\s+ask\b",
        r"\bnever\s+ask\b",
        r"\bshould\s+NOT\b.*\bask\b",
    ]

    strong_hits = []
    medium_hits = []
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        if idx in agent_indices:
            # Check if it's a "should NOT" line
            continue

        # Check negation
        negated = False
        for neg in negation_patterns:
            if re.search(neg, line, re.IGNORECASE):
                negated = True
                break
        if negated:
            continue

        for pat in strong_patterns:
            if re.search(pat, line, re.IGNORECASE):
                strong_hits.append((idx, line.strip()[:80]))
                break

        for pat in medium_patterns:
            if re.search(pat, line, re.IGNORECASE):
                medium_hits.append((idx, line.strip()[:80]))
                break

    has_implicit = len(strong_hits) > 0 or len(medium_hits) >= 2

    if not has_implicit:
        detail = "No implicit user interaction patterns detected"
        if medium_hits:
            detail = f"1 medium signal (below threshold of 2): L{medium_hits[0][0] + 1}"
        return (result("auq-implicit-interaction", True, detail), False)

    parts = []
    for idx, text in strong_hits:
        parts.append(f"L{idx + 1}: {text}")
    for idx, text in medium_hits:
        parts.append(f"L{idx + 1}: {text}")
    detail = (f"{len(strong_hits)} strong, {len(medium_hits)} medium signal(s) "
              f"but AskUserQuestion not in allowed-tools: "
              + "; ".join(parts[:5]))
    return (result("auq-implicit-interaction", False, detail), True)


def check_required_arg_fallback(fm: dict, body: str,
                                prose_lines: list) -> list:
    """AUQ-REQUIRED-ARG: Required args have ask-or-fallback paths."""
    tools = get_allowed_tools(fm)
    declared = "AskUserQuestion" in tools
    args = parse_argument_table(body)

    if not args:
        return [result("auq-required-arg-fallback", True,
                        "No argument table found - skipped")]

    if not declared:
        return [result("auq-required-arg-fallback", True,
                        "AskUserQuestion not in allowed-tools - skip required-arg check")]

    results = []
    # Only positional args (not starting with --) with default - or empty
    # are truly required. Flag-style args with - default are optional.
    required_args = [a for a in args
                     if a["default"] in ("-", "")
                     and not a["name"].startswith("--")]
    if not required_args:
        return [result("auq-required-arg-fallback", True,
                        "No required arguments (all have defaults)")]

    body_lower = body.lower()
    for arg in required_args:
        name = arg["name"]
        # Normalize: strip parens, flags
        clean_name = re.sub(r"^[-(]+", "", name).strip(")")
        clean_name_lower = clean_name.lower()

        has_ask = False
        has_fallback = False

        # Check if body mentions asking/prompting for this arg
        for pat in [r"ask.*" + re.escape(clean_name_lower),
                    r"prompt.*" + re.escape(clean_name_lower),
                    r"AskUserQuestion.*" + re.escape(clean_name_lower),
                    re.escape(clean_name_lower) + r".*ask",
                    re.escape(clean_name_lower) + r".*prompt"]:
            if re.search(pat, body_lower):
                has_ask = True
                break

        # Also check for "positional" args with generic ask
        if "positional" in clean_name_lower:
            for pat in [r"ask.*feature", r"ask.*name", r"prompt.*feature"]:
                if re.search(pat, body_lower):
                    has_ask = True
                    break

        # Check fallback mechanisms
        for pat in [r"auto.?detect", r"default\s+to", r"fall\s*back",
                    r"env\s*var", r"environment\s+variable",
                    r"if\s+(no|not\s+provided|missing|omit)"]:
            if re.search(pat + r".*" + re.escape(clean_name_lower), body_lower):
                has_fallback = True
                break
            if re.search(re.escape(clean_name_lower) + r".*" + pat, body_lower):
                has_fallback = True
                break

        if has_ask or has_fallback:
            continue

        results.append(result("auq-required-arg-fallback", False,
                              f"Required arg `{name}` has no ask/prompt mechanism "
                              f"and no fallback - AskUserQuestion is available but "
                              f"not used for missing input"))

    if not results:
        return [result("auq-required-arg-fallback", True,
                        f"All {len(required_args)} required arg(s) have "
                        f"ask or fallback paths")]
    return results


def check_spawned_agent(fm: dict, prose_lines: list,
                        agent_indices: set) -> dict:
    """AUQ-SPAWNED: AskUserQuestion should not appear in agent sections."""
    context = fm.get("context", "")
    if context == "fork":
        return result("auq-spawned-agent", True,
                       "context: fork - entire skill is a subagent, check skipped")

    if not agent_indices:
        return result("auq-spawned-agent", True,
                       "No spawned agent sections detected")

    violations = []
    for idx, line in prose_lines:
        if idx not in agent_indices:
            continue
        if "AskUserQuestion" in line:
            violations.append(f"L{idx + 1}")

    if violations:
        return result("auq-spawned-agent", False,
                       "AskUserQuestion in spawned agent section (agents "
                       f"cannot interact with users): {', '.join(violations)}")
    return result("auq-spawned-agent", True,
                   "No AskUserQuestion in spawned agent sections")


def check_option_structure(fm: dict, prose_lines: list,
                           bundled_indices: set) -> dict:
    """AUQ-OPTION-STRUCTURE: AskUserQuestion usage sites have options nearby."""
    tools = get_allowed_tools(fm)
    if "AskUserQuestion" not in tools:
        return result("auq-option-structure", True,
                       "AskUserQuestion not in allowed-tools - skipped")

    # Find AskUserQuestion usage sites
    sites = []
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        if "AskUserQuestion" in line:
            sites.append(idx)

    if not sites:
        return result("auq-option-structure", True,
                       "No explicit AskUserQuestion mentions in workflow prose")

    missing_input_pat = re.compile(
        r"AskUserQuestion.*(to\s+get|to\s+ask|if\s+(no|omit|miss|not\s+provided))",
        re.IGNORECASE)
    # Also exempt lines that combine "ask/collect/gather" with AskUserQuestion
    input_collection_pat = re.compile(
        r"(ask|collect|gather|get)\s+.{0,40}(using|via)\s+AskUserQuestion"
        r"|AskUserQuestion\s+.{0,20}(ask|collect|gather|get)",
        re.IGNORECASE)

    violations = []
    prose_dict = {idx: line for idx, line in prose_lines}
    for site_idx in sites:
        line = prose_dict.get(site_idx, "")

        # Missing-input exemption
        if missing_input_pat.search(line):
            continue
        if input_collection_pat.search(line):
            continue

        # "with options" or "options:" on the AUQ line itself
        if re.search(r"with\s+options|options:", line, re.IGNORECASE):
            continue

        # Check within 10 lines for option structure
        has_options = False
        for offset in range(-2, 11):
            check_idx = site_idx + offset
            nearby = prose_dict.get(check_idx, "")
            # Quoted option bullets
            if re.search(r"^\s*-\s+[\"']", nearby):
                has_options = True
                break
            # Option N, Options: heading
            if re.search(r"[Oo]ption\s*\d|[Oo]ptions:", nearby):
                has_options = True
                break
            # Numbered list with option-like content
            if re.search(r"^\s*\d+\.\s+", nearby) and "option" in nearby.lower():
                has_options = True
                break
            # Description bullets (choice descriptions)
            if re.search(r"^\s*-\s+\S.{10,}", nearby):
                has_options = True
                break

        if not has_options:
            violations.append(f"L{site_idx + 1}")

    if violations:
        return result("auq-option-structure", False,
                       f"AskUserQuestion mentioned without nearby options/choices: "
                       f"{', '.join(violations)}")
    return result("auq-option-structure", True,
                   f"All {len(sites)} AskUserQuestion site(s) have option structure")


def check_destructive(fm: dict, prose_lines: list,
                      bundled_indices: set) -> dict:
    """AUQ-DESTRUCTIVE: Side-effect skills with destructive ops need confirmation."""
    dmi = fm.get("disable-model-invocation", "")
    if dmi != "true":
        return result("auq-destructive-no-confirm", True,
                       "disable-model-invocation not true - skipped")

    destructive_patterns = [
        r"k3d\s+(cluster|create|delete)",
        r"git\s+reset",
        r"git\s+branch\s+-[dD]",
        r"git\s+push\s+--force",
        r"git\s+clean",
        r"kubectl\s+(delete|drain|cordon)",
        r"helm\s+(uninstall|delete)",
        r"\brm\s+-rf\b",
        r"git\s+apply\s+--cached",
    ]
    confirmation_patterns = [
        r"\bconfirm\b",
        r"\bapproval\b",
        r"\bapprove\b",
        r"\bask.*before\b",
        r"\bgate\b",
        r"\bAskUserQuestion\b",
    ]

    found_destructive = []
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        for pat in destructive_patterns:
            if re.search(pat, line, re.IGNORECASE):
                found_destructive.append((idx, pat))
                break

    if not found_destructive:
        return result("auq-destructive-no-confirm", True,
                       "No destructive patterns detected")

    # Check for confirmation language anywhere in prose
    all_prose = " ".join(line for _, line in prose_lines
                         if _ not in bundled_indices)
    has_confirmation = False
    for pat in confirmation_patterns:
        if re.search(pat, all_prose, re.IGNORECASE):
            has_confirmation = True
            break

    if has_confirmation:
        return result("auq-destructive-no-confirm", True,
                       "Destructive patterns present but confirmation "
                       "mechanism exists")

    detail_pats = list({p for _, p in found_destructive[:3]})
    return result("auq-destructive-no-confirm", False,
                   f"Side-effect skill has destructive patterns but no "
                   f"confirmation mechanism: {', '.join(detail_pats)}")


def check_ambiguity(prose_lines: list, bundled_indices: set) -> dict:
    """AUQ-AMBIGUITY: Ambiguous situations have resolution mechanisms."""
    ambiguity_patterns = [
        r"\bif\s+(unclear|ambiguous)\b",
        r"\bmultiple\s+.{0,20}\s+match\b",
        r"\bcould\s+mean\b",
        r"\bmore\s+than\s+one\b",
        r"\b(uncertain|unsure)\s+(which|what|whether)\b",
        r"\bcannot\s+determine\b",
        r"\bmultiple\s+(valid|possible)\s+(interpretations|options|matches|candidates)\b",
    ]
    resolution_patterns = [
        r"\bAskUserQuestion\b",
        r"\bask\b",
        r"\bprompt\b",
        r"\bconfirm\b",
        r"\bdefault\s+to\b",
        r"\bfall\s*back\b",
        r"\buse\s+the\s+first\b",
    ]

    prose_dict = {idx: line for idx, line in prose_lines}

    violations = []
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        is_ambiguous = False
        for pat in ambiguity_patterns:
            if re.search(pat, line, re.IGNORECASE):
                is_ambiguous = True
                break
        if not is_ambiguous:
            continue

        # Check within 5 lines for resolution
        has_resolution = False
        for offset in range(-2, 6):
            check_idx = idx + offset
            nearby = prose_dict.get(check_idx, "")
            for rpat in resolution_patterns:
                if re.search(rpat, nearby, re.IGNORECASE):
                    has_resolution = True
                    break
            if has_resolution:
                break

        if not has_resolution:
            violations.append(f"L{idx + 1}: {line.strip()[:60]}")

    if violations:
        return result("auq-ambiguity-unresolved", False,
                       f"Ambiguity without resolution mechanism: "
                       f"{'; '.join(violations[:3])}")
    return result("auq-ambiguity-unresolved", True,
                   "No unresolved ambiguity patterns")


def check_multiselect(prose_lines: list, bundled_indices: set) -> dict:
    """AUQ-MULTISELECT: multiSelect usage has grouping guidance."""
    has_multiselect = False
    for idx, line in prose_lines:
        if idx in bundled_indices:
            continue
        if re.search(r"\bmultiSelect\b", line):
            has_multiselect = True
            break

    if not has_multiselect:
        return result("auq-multiselect-grouping", True,
                       "No multiSelect usage - skipped")

    all_prose = " ".join(line for idx, line in prose_lines
                         if idx not in bundled_indices)
    grouping_patterns = [
        r"\bgroup\s+by\b",
        r"\bpre-select\b",
        r"\bstrength\b",
        r"\bconfidence\b",
        r"\bpriority\b",
        r"\b[Ss]trong\s+signals?\b",
        r"\b[Mm]oderate\s+signals?\b",
    ]
    has_grouping = False
    for pat in grouping_patterns:
        if re.search(pat, all_prose, re.IGNORECASE):
            has_grouping = True
            break

    if has_grouping:
        return result("auq-multiselect-grouping", True,
                       "multiSelect usage has grouping guidance")
    return result("auq-multiselect-grouping", True,
                   "INFO: multiSelect used without grouping guidance "
                   "(group by strength/confidence recommended)")


def check_wizard(prose_lines: list, bundled_indices: set) -> dict:
    """AUQ-WIZARD: Confirmation wizard patterns have explicit termination."""
    all_prose = " ".join(line for idx, line in prose_lines
                         if idx not in bundled_indices)

    # Detect wizard pattern: AskUserQuestion + confirm + loop/repeat
    has_auq = "AskUserQuestion" in all_prose
    has_confirm = bool(re.search(r"\bconfirm\b", all_prose, re.IGNORECASE))
    has_loop = bool(re.search(
        r"\b(loop|repeat|again|until\s+user\s+confirms)\b",
        all_prose, re.IGNORECASE))

    if not (has_auq and has_confirm and has_loop):
        return result("auq-wizard-loop", True,
                       "No confirmation wizard pattern detected - skipped")

    # Check for explicit termination
    termination_patterns = [
        r"\buntil\s+user\s+confirms\b",
        r"\b[Ll]oop\s+until\b",
        r"\brepeat\s+until\b",
        r"\bconfirm\s+and\s+save\b",
        r"\buser\s+picks\b.*\bpresent\s+again\b",
    ]
    has_termination = False
    for pat in termination_patterns:
        if re.search(pat, all_prose, re.IGNORECASE):
            has_termination = True
            break

    if has_termination:
        return result("auq-wizard-loop", True,
                       "Wizard pattern has explicit loop termination")
    return result("auq-wizard-loop", True,
                   "INFO: Wizard pattern detected but loop termination "
                   "condition could be more explicit")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <skill-directory>", file=sys.stderr)
        sys.exit(2)

    skill_dir = sys.argv[1]
    if not os.path.isdir(skill_dir):
        print(f"Error: {skill_dir} is not a directory", file=sys.stderr)
        sys.exit(2)

    skill_md = find_skill_md(skill_dir)
    if not skill_md:
        print(f"Error: No SKILL.md found in {skill_dir}", file=sys.stderr)
        sys.exit(2)

    try:
        content = open(skill_md, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print(f"Error reading {skill_md}: {e}", file=sys.stderr)
        sys.exit(2)

    fm = extract_frontmatter(content)
    body = extract_body(content)
    prose_lines = strip_code_blocks(body)
    bundled_indices = find_bundled_section(prose_lines)
    agent_indices = find_spawned_agent_sections(prose_lines)

    results = []
    total = 0
    passed = 0
    failed = 0

    # AUQ-IMPLICIT (run first to inform AUQ-DECL)
    implicit_result, has_implicit = check_implicit_interaction(
        fm, prose_lines, bundled_indices, agent_indices)

    # AUQ-DECL
    decl_result = check_declaration_match(
        fm, body, prose_lines, bundled_indices, has_implicit)
    results.append(decl_result)

    # AUQ-IMPLICIT
    results.append(implicit_result)

    # AUQ-REQUIRED-ARG
    req_results = check_required_arg_fallback(fm, body, prose_lines)
    results.extend(req_results)

    # AUQ-SPAWNED
    results.append(check_spawned_agent(fm, prose_lines, agent_indices))

    # AUQ-OPTION-STRUCTURE
    results.append(check_option_structure(fm, prose_lines, bundled_indices))

    # AUQ-DESTRUCTIVE
    results.append(check_destructive(fm, prose_lines, bundled_indices))

    # AUQ-AMBIGUITY
    results.append(check_ambiguity(prose_lines, bundled_indices))

    # AUQ-MULTISELECT
    results.append(check_multiselect(prose_lines, bundled_indices))

    # AUQ-WIZARD
    results.append(check_wizard(prose_lines, bundled_indices))

    for r in results:
        emit(r)
        total += 1
        if r["pass"]:
            passed += 1
        else:
            failed += 1

    print(json.dumps({"summary": True, "total": total,
                       "passed": passed, "failed": failed}))

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
