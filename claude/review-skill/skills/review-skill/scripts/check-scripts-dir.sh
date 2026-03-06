#!/usr/bin/env bash
# check-scripts-dir.sh - Script invocation and permission validation functions.
# Source from orchestrator or run standalone: ./check-scripts-dir.sh <skill-dir>
#
# Functions: check_script_invocation_prefix, check_no_bash_prefix,
#   check_script_executable
#
# Requires _lib.sh globals: SKILL_DIR, SKILL_BODY, FULL_BODY

# --- script invocations use ${CLAUDE_SKILL_DIR} or $SKILL_DIR prefix (I6) ---
check_script_invocation_prefix() {
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    local BARE_REFS
    BARE_REFS=$(echo "$SKILL_BODY" \
      | { grep -E 'scripts/[a-zA-Z0-9._-]+\.sh' || true; } \
      | { grep -vE '^\s*#{1,6}\s' || true; } \
      | { grep -vE '\$SKILL_DIR|\$\{CLAUDE_SKILL_DIR\}' || true; })

    if [[ -n "$BARE_REFS" ]]; then
      local BARE_COUNT FIRST_BAD
      BARE_COUNT=$(wc -l <<< "$BARE_REFS" | tr -d ' ')
      FIRST_BAD=$(echo "$BARE_REFS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      emit "script-invocation-prefix" "false" "Found ${BARE_COUNT} script reference(s) without \${CLAUDE_SKILL_DIR} prefix — use \"\${CLAUDE_SKILL_DIR}/scripts/...\" — first: ${FIRST_BAD}"
    else
      emit "script-invocation-prefix" "true" "All script references use \${CLAUDE_SKILL_DIR} prefix"
    fi
  fi
}

# --- no bash prefix on script invocations ---
check_no_bash_prefix() {
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    local BASH_PREFIX_REFS
    BASH_PREFIX_REFS=$(echo "$FULL_BODY" \
      | awk '/^```/{f=!f;next} f && /^\s*bash\s+/' \
      || true)

    if [[ -n "$BASH_PREFIX_REFS" ]]; then
      local BASH_COUNT FIRST_BASH
      BASH_COUNT=$(wc -l <<< "$BASH_PREFIX_REFS" | tr -d ' ')
      FIRST_BASH=$(echo "$BASH_PREFIX_REFS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      emit "no-bash-prefix" "false" "Found ${BASH_COUNT} script invocation(s) using bash prefix — invoke directly via \"\${CLAUDE_SKILL_DIR}/scripts/...\" and set executable bit — first: ${FIRST_BASH}"
    else
      emit "no-bash-prefix" "true" "No bash-prefixed script invocations found"
    fi
  fi
}

# --- scripts have executable bit set ---
check_script_executable() {
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    for script_file in "${SKILL_DIR}/scripts"/*; do
      [[ -f "$script_file" ]] || continue
      local SCRIPT_BASENAME
      SCRIPT_BASENAME=$(basename "$script_file")
      if [[ -x "$script_file" ]]; then
        emit "script-executable" "true" "Script '${SCRIPT_BASENAME}' has executable bit set"
      else
        emit "script-executable" "false" "Script '${SCRIPT_BASENAME}' missing executable bit — run chmod +x"
      fi
    done
  fi
}

# ========================
# STANDALONE EXECUTION
# ========================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  source "$(dirname "$0")/_lib.sh" "$1"
  check_script_invocation_prefix
  check_no_bash_prefix
  check_script_executable
  emit_summary
fi
