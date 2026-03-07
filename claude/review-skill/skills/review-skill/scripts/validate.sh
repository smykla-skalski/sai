#!/usr/bin/env bash
# validate.sh — Validate SKILL.md frontmatter fields and directory structure.
#
# Usage:
#   ./validate.sh <skill-directory> [mode]
#
# Modes:
#   all          — Run all checks (default)
#   frontmatter  — Frontmatter field checks only
#   structure    — Directory structure checks only
#
# Output: One JSON object per line:
#   {"check": "<id>", "pass": true|false, "detail": "<message>"}
#
# Final line is always a summary:
#   {"summary": true, "total": N, "passed": N, "failed": N}
#
# Exit code: 0 if all checks pass, 1 if any check fails, 2 if usage error.
#
# Canonical skill layout (per Agent Skills spec):
#
#   skill-name/
#   ├── SKILL.md           (required — entrypoint)
#   ├── references/        (documentation loaded into context on demand)
#   ├── scripts/           (executable code invoked via Bash tool)
#   ├── assets/            (templates, icons, fonts used in output)
#   └── examples/          (example files showing expected format)
#
# All bundled resources live alongside SKILL.md in the skill directory.
# See: https://code.claude.com/docs/en/skills
#      references/skill-structure.md (bundled with review-skill)
#
# Dependencies: bash 4+, awk, grep, sed, wc
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

# ========================
# ARGUMENT PARSING
# ========================
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <skill-directory> [all|frontmatter|structure]" >&2
  exit 2
fi

SKILL_DIR="$1"
MODE="${2:-all}"
SCRIPT_DIR="$(dirname "$0")"

# ========================
# LOAD SHARED LIBRARY (sets globals, helpers, pre-flight)
# ========================
source "${SCRIPT_DIR}/_lib.sh"

# ========================
# LOAD CHECK FUNCTION LIBRARIES (function defs only)
# ========================
source "${SCRIPT_DIR}/check-scripts-dir.sh"
source "${SCRIPT_DIR}/check-references.sh"

# ========================
# DELEGATION HELPER
# ========================
# Re-emit JSON results from a companion script's NDJSON output.
# Args: output_string
reemit_delegate_output() {
  local output="$1"
  while IFS= read -r line; do
    [[ "$line" == *'"summary"'* ]] && continue
    local chk pss dtl
    chk=$(echo "$line" | sed -n 's/.*"check": "\([^"]*\)".*/\1/p')
    pss=$(echo "$line" | sed -nE 's/.*"pass": (true|false).*/\1/p')
    dtl=$(echo "$line" | sed -n 's/.*"detail": "\(.*\)".*$/\1/p')
    [[ -z "$chk" ]] && continue
    emit "$chk" "$pss" "$dtl"
  done <<< "$output"
}

# Re-emit JSON results from an existing standalone companion script.
# Args: script_path, guard_field (skip if guard field is 0 or absent)
delegate_script() {
  local script="$1" guard_field="${2:-}"
  [[ -x "$script" ]] || return 0
  local output stderr_file
  stderr_file=$(mktemp); _TMPFILES+=("$stderr_file")
  output=$("$script" "$SKILL_DIR" 2>"$stderr_file" || true)
  if [[ -z "$output" ]]; then
    local stderr_msg
    stderr_msg=$(head -1 "$stderr_file" 2>/dev/null || true)
    if [[ -n "$stderr_msg" ]]; then
      emit "helper-runtime" "true" "WARN: $(basename "$script") produced no output — ${stderr_msg}"
    fi
    return 0
  fi
  if [[ -n "$guard_field" ]]; then
    local guard_val
    guard_val=$(echo "$output" | tail -1 | sed -n "s/.*\"${guard_field}\": \([0-9]*\).*/\1/p")
    [[ "${guard_val:-0}" -gt 0 ]] || return 0
  fi
  reemit_delegate_output "$output"
}

# Re-emit JSON results from a script with extra CLI args.
# Args: script_path, [script args...]
delegate_script_args() {
  local script="$1"
  shift
  [[ -x "$script" ]] || return 0
  local output
  output=$("$script" "$SKILL_DIR" "$@" 2>/dev/null || true)
  [[ -n "$output" ]] || return 0
  reemit_delegate_output "$output"
}

# ========================
# FRONTMATTER CHECKS
# ========================
run_frontmatter() {
  # --- name ---
  local NAME DIR_NAME
  NAME=$(get_field "name")
  DIR_NAME=$(basename "$SKILL_DIR")

  if [[ -z "$NAME" ]]; then
    emit "name-present" "false" "Field 'name' is missing from frontmatter"
  else
    emit "name-present" "true" "Field 'name' is present"

    if [[ ${#NAME} -gt 64 ]]; then
      emit "name-format" "false" "Name '${NAME}' exceeds 64 characters (${#NAME})"
    elif [[ ! "$NAME" =~ ^[a-z0-9-]+$ ]]; then
      emit "name-format" "false" "Name '${NAME}' contains invalid characters (only lowercase, numbers, hyphens)"
    elif [[ "$NAME" =~ ^- ]] || [[ "$NAME" =~ -$ ]]; then
      emit "name-format" "false" "Name '${NAME}' must not start or end with a hyphen"
    elif [[ "$NAME" =~ -- ]]; then
      emit "name-format" "false" "Name '${NAME}' contains consecutive hyphens"
    else
      emit "name-format" "true" "Name '${NAME}' matches pattern [a-z0-9-]{1,64}"
    fi

    if [[ "$NAME" == "$DIR_NAME" ]]; then
      emit "name-matches-dir" "true" "Name '${NAME}' matches directory '${DIR_NAME}'"
    else
      emit "name-matches-dir" "false" "Name '${NAME}' does not match directory '${DIR_NAME}'"
    fi
  fi

  # --- description ---
  local DESCRIPTION
  DESCRIPTION=$(get_field "description")

  if [[ -z "$DESCRIPTION" ]]; then
    emit "description-present" "false" "Field 'description' is missing from frontmatter"
  else
    emit "description-present" "true" "Field 'description' is present"

    if [[ ${#DESCRIPTION} -gt 1024 ]]; then
      emit "description-length" "false" "Description is ${#DESCRIPTION} chars, exceeds 1024-char limit"
    else
      emit "description-length" "true" "Description is ${#DESCRIPTION} chars (limit 1024)"
    fi

    local DMI
    DMI=$(get_field "disable-model-invocation")
    if [[ "$DMI" == "true" ]]; then
      emit "description-trigger-phrases" "true" "Trigger phrases not required (disable-model-invocation: true)"
    else
      local DESC_LOWER
      DESC_LOWER=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')
      if echo "$DESC_LOWER" | grep -qE '\b(when|use|for)\b'; then
        emit "description-trigger-phrases" "true" "Description includes trigger phrase (when/use/for)"
      else
        emit "description-trigger-phrases" "false" "Description should include a trigger phrase (when/use/for) for discoverability"
      fi
    fi

    if echo "$DESCRIPTION" | grep -qiE '^\s*"?(I can|You can)'; then
      emit "description-third-person" "false" "Description should use third-person form, not 'I can' or 'You can'"
    else
      emit "description-third-person" "true" "Description uses appropriate voice"
    fi
  fi

  # --- allowed-tools ---
  local ALLOWED_TOOLS
  ALLOWED_TOOLS=$(get_field "allowed-tools")

  if [[ -z "$ALLOWED_TOOLS" ]]; then
    emit "allowed-tools-present" "false" "Field 'allowed-tools' is missing from frontmatter"
  else
    emit "allowed-tools-present" "true" "Field 'allowed-tools' is present: ${ALLOWED_TOOLS}"
  fi

  # --- user-invocable ---
  local USER_INVOCABLE
  USER_INVOCABLE=$(get_field "user-invocable")

  if [[ -z "$USER_INVOCABLE" ]]; then
    emit "user-invocable-present" "false" "Field 'user-invocable' is missing from frontmatter"
  else
    if [[ "$USER_INVOCABLE" == "true" ]] || [[ "$USER_INVOCABLE" == "false" ]]; then
      emit "user-invocable-present" "true" "Field 'user-invocable' is '${USER_INVOCABLE}'"
    else
      emit "user-invocable-present" "false" "Field 'user-invocable' must be boolean (true/false), got '${USER_INVOCABLE}'"
    fi
  fi
}

# ========================
# STRUCTURE CHECKS
# ========================
run_structure() {
  local HAS_PYTHON3=1
  if ! command -v python3 &>/dev/null; then
    HAS_PYTHON3=0
    emit "helper-runtime" "true" "WARN: python3 not found - python-based checks skipped"
  fi

  local FILE_REFS_SCRIPT
  FILE_REFS_SCRIPT="${SCRIPT_DIR}/check-file-refs.py"

  local CONTENT_SCRIPT
  CONTENT_SCRIPT="${SCRIPT_DIR}/check-content.py"

  local CONFIG_SCRIPT
  CONFIG_SCRIPT="${SCRIPT_DIR}/check-config.py"

  # Function calls in exact current emission order
  check_body_line_count
  delegate_script_args "$FILE_REFS_SCRIPT" --check file-ref-resolves
  check_script_invocation_prefix
  check_no_bash_prefix
  check_script_executable
  delegate_script_args "$CONTENT_SCRIPT" --check no-secrets
  delegate_script_args "$FILE_REFS_SCRIPT" --check no-backslash-paths
  delegate_script_args "$CONTENT_SCRIPT" --check no-useless-echo
  check_duplicate_codeblocks
  check_consistent_phase_numbering
  delegate_script_args "$FILE_REFS_SCRIPT" --check no-disallowed-files
  delegate_script_args "$FILE_REFS_SCRIPT" --check refs-one-level
  check_long_ref_toc
  delegate_script_args "$CONFIG_SCRIPT" --check persistent-state-xdg
  delegate_script_args "$CONTENT_SCRIPT" --check no-grading-style
  delegate_script_args "$FILE_REFS_SCRIPT" --check skill-md-mentions-file
  delegate_script_args "$FILE_REFS_SCRIPT" --check ref-link-format

  # Existing companion scripts (delegation)
  delegate_script "${SCRIPT_DIR}/check-read-gates.sh" "refs"

  delegate_script_args "$CONFIG_SCRIPT" --check allowed-tools-usage
  delegate_script_args "$CONFIG_SCRIPT" --check side-effect-guard

  delegate_script "${SCRIPT_DIR}/check-preprocessing.py" "directives"

  # --- shell script static analysis (I20) ---
  local LINT_SCRIPT SCRIPTS_DIR
  LINT_SCRIPT="${SCRIPT_DIR}/lint-scripts.py"
  SCRIPTS_DIR="${SKILL_DIR}/scripts"
  if [[ "$HAS_PYTHON3" -eq 0 ]]; then
    :  # skipped (no python3)
  elif [[ ! -d "$SCRIPTS_DIR" ]]; then
    emit "script-lint" "true" "No scripts/ directory"
  elif [[ -x "$LINT_SCRIPT" ]]; then
    local LINT_OUTPUT LINT_SUMMARY LINT_CRITS LINT_MEDS LINT_TOTAL
    LINT_OUTPUT=$(python3 "$LINT_SCRIPT" "$SCRIPTS_DIR" --json --severity medium 2>/dev/null || true)
    LINT_SUMMARY=$(echo "$LINT_OUTPUT" | tail -1)
    LINT_TOTAL=$(echo "$LINT_SUMMARY" | sed -n 's/.*"findings": \([0-9]*\).*/\1/p')
    LINT_TOTAL="${LINT_TOTAL:-0}"
    LINT_CRITS=$(echo "$LINT_OUTPUT" | grep -c '"severity": "critical"' || true)
    LINT_MEDS=$(echo "$LINT_OUTPUT" | grep -c '"severity": "medium"' || true)

    if [[ "$LINT_TOTAL" -eq 0 ]]; then
      emit "script-lint" "true" "No critical/medium findings in scripts/"
    else
      local LINT_DETAIL_PARTS=("scripts/ has ${LINT_CRITS} critical, ${LINT_MEDS} medium finding(s)")
      local LINT_TOP
      LINT_TOP=$(echo "$LINT_OUTPUT" | { grep -v '"summary"' || true; } | head -3 \
        | sed -n 's/.*"check": "\([^"]*\)".*"message": "\([^"]*\)".*/\1: \2/p' \
        | tr '\n' '; ' | sed 's/; $//')
      [[ -n "$LINT_TOP" ]] && LINT_DETAIL_PARTS+=(" — ${LINT_TOP}")
      local LINT_DETAIL
      LINT_DETAIL=$(printf '%s' ${LINT_DETAIL_PARTS[@]+"${LINT_DETAIL_PARTS[@]}"})
      emit "script-lint" "false" "${LINT_DETAIL}"
    fi
  fi

  # --- AskUserQuestion usage validation (I21) ---
  local AUQ_SCRIPT
  AUQ_SCRIPT="${SCRIPT_DIR}/check-ask-user.py"
  if [[ "$HAS_PYTHON3" -eq 0 ]]; then
    :  # skipped (no python3)
  elif [[ -x "$AUQ_SCRIPT" ]]; then
    local AUQ_OUTPUT AUQ_SUMMARY AUQ_TOTAL
    AUQ_OUTPUT=$(python3 "$AUQ_SCRIPT" "$SKILL_DIR" 2>/dev/null || true)
    AUQ_SUMMARY=$(echo "$AUQ_OUTPUT" | tail -1)
    AUQ_TOTAL=$(echo "$AUQ_SUMMARY" | sed -n 's/.*"total": \([0-9]*\).*/\1/p')
    AUQ_TOTAL="${AUQ_TOTAL:-0}"

    if [[ "$AUQ_TOTAL" -gt 0 ]]; then
      while IFS= read -r line; do
        [[ "$line" == *'"summary"'* ]] && continue
        local AQ_CHECK AQ_PASS AQ_DETAIL
        AQ_CHECK=$(echo "$line" | sed -n 's/.*"check": "\([^"]*\)".*/\1/p')
        AQ_PASS=$(echo "$line" | sed -nE 's/.*"pass": (true|false).*/\1/p')
        AQ_DETAIL=$(echo "$line" | sed -n 's/.*"detail": "\(.*\)".*$/\1/p')
        [[ -z "$AQ_CHECK" ]] && continue
        emit "$AQ_CHECK" "$AQ_PASS" "$AQ_DETAIL"
      done <<< "$AUQ_OUTPUT"
    fi
  fi

  # --- flag coverage (I22) ---
  delegate_script_args "${SCRIPT_DIR}/check-flag-coverage.py"

  # --- hooks validation (I23) ---
  if [[ "$HAS_PYTHON3" -eq 1 ]]; then
    delegate_script "${SCRIPT_DIR}/check-hooks.py"
  fi

  # --- fork candidate analysis (P9, informational) ---
  local FORK_SCRIPT
  FORK_SCRIPT="${SCRIPT_DIR}/check-fork-candidate.py"
  if [[ -x "$FORK_SCRIPT" ]]; then
    local FORK_RESULT
    FORK_RESULT=$(python3 "$FORK_SCRIPT" "$SKILL_DIR" 2>/dev/null | tail -1 || true)
    local FORK_REC FORK_DETAIL
    FORK_REC=$(echo "$FORK_RESULT" | sed -n 's/.*"recommendation": "\([^"]*\)".*/\1/p')
    FORK_DETAIL=$(echo "$FORK_RESULT" | sed -n 's/.*"detail": "\(.*\)".*$/\1/p')

    if [[ "$FORK_REC" == "strong" ]] || [[ "$FORK_REC" == "soft" ]]; then
      emit "fork-candidate-info" "true" "INFO: ${FORK_DETAIL}"
    else
      emit "fork-candidate-info" "true" "No fork recommendation — ${FORK_DETAIL}"
    fi
  fi
}

# ========================
# MAIN
# ========================
case "$MODE" in
  all)         run_frontmatter; run_structure ;;
  frontmatter) run_frontmatter ;;
  structure)   run_structure ;;
  *)
    echo "Unknown mode: ${MODE} (valid: all, frontmatter, structure)" >&2
    exit 2
    ;;
esac

# Always emit a summary as the final line
printf '{"summary": true, "total": %d, "passed": %d, "failed": %d}\n' "$TOTAL" "$PASSED" "$FAILED"

# Exit 0 if all passed, 1 if any failed
[[ "$FAILED" -eq 0 ]]
