#!/usr/bin/env bash
# check-config.sh - Configuration and tool usage validation functions.
# Source from orchestrator or run standalone: ./check-config.sh <skill-dir>
#
# Functions: check_persistent_state_xdg, check_allowed_tools_usage,
#   check_side_effect_guard
#
# Requires _lib.sh globals: SKILL_BODY, FRONTMATTER, FULL_BODY

# --- persistent state uses XDG paths, not relative or cache-relative ---
check_persistent_state_xdg() {
  local HAS_STATE_PATTERNS HAS_XDG_PATH
  HAS_STATE_PATTERNS=$(echo "$SKILL_BODY" \
    | grep -cE '\./findings/|\$SKILL_DIR/findings/|\$\{CLAUDE_SKILL_DIR\}/findings/|\.last-run|\.covered-|state stored in|persistent.*state|State Files' || true)
  HAS_XDG_PATH=$(echo "$SKILL_BODY" \
    | grep -cE 'XDG_DATA_HOME|\$HOME/\.local/share' || true)

  if [[ "$HAS_STATE_PATTERNS" -gt 0 ]]; then
    local HAS_BAD_PATHS
    HAS_BAD_PATHS=$(echo "$SKILL_BODY" \
      | grep -cE '\./findings/|\$SKILL_DIR/findings/|\$\{CLAUDE_SKILL_DIR\}/findings/' || true)
    if [[ "$HAS_XDG_PATH" -gt 0 ]]; then
      emit "persistent-state-xdg" "true" "Persistent state uses XDG-compliant path"
    elif [[ "$HAS_BAD_PATHS" -gt 0 ]]; then
      emit "persistent-state-xdg" "false" "Skill uses relative paths (./findings/ or \${CLAUDE_SKILL_DIR}/findings/) for persistent state — use \${XDG_DATA_HOME:-\$HOME/.local/share}/sai/{plugin}/ instead"
    else
      emit "persistent-state-xdg" "true" "State references found but no relative path issues detected"
    fi
  fi
}

# --- allowed-tools only lists tools referenced in the skill (I16) ---
check_allowed_tools_usage() {
  local AT
  AT=$(get_field "allowed-tools")
  if [[ -n "$AT" ]]; then
    local UNUSED_TOOLS=""

    if [[ "$AT" == *Task* ]]; then
      if ! grep -qE '\bTask\b' <<< "$FULL_BODY" \
        && ! grep -qiE '\bagent\b|\bspawn\b|\bsubagent\b' <<< "$FULL_BODY"; then
        UNUSED_TOOLS="${UNUSED_TOOLS}Task "
      fi
    fi

    if [[ "$AT" == *ToolSearch* ]]; then
      if ! grep -qE '\bToolSearch\b' <<< "$FULL_BODY" \
        && ! grep -qiE 'mcp__|select:' <<< "$FULL_BODY"; then
        UNUSED_TOOLS="${UNUSED_TOOLS}ToolSearch "
      fi
    fi

    UNUSED_TOOLS=$(echo "$UNUSED_TOOLS" | xargs)
    if [[ -n "$UNUSED_TOOLS" ]]; then
      emit "allowed-tools-usage" "false" "allowed-tools lists unused tool(s): ${UNUSED_TOOLS} — remove to minimize granted permissions"
    else
      emit "allowed-tools-usage" "true" "No unused high-signal tools detected in allowed-tools"
    fi
  fi
}

# --- side-effect skills have disable-model-invocation guard (I17) ---
check_side_effect_guard() {
  local DMI
  DMI=$(get_field "disable-model-invocation")
  local SIDE_EFFECT_HITS
  SIDE_EFFECT_HITS=$(echo "$FULL_BODY" \
    | grep -ciE 'k3d (cluster|create|delete)|kind (create|delete) cluster|git reset|git branch -[dD]|git apply --cached|git clean -|git push --force|kubectl (delete|drain|cordon)|helm (uninstall|delete)|rm -rf' \
    || true)

  if [[ "$SIDE_EFFECT_HITS" -gt 0 ]]; then
    if [[ "$DMI" == "true" ]]; then
      emit "side-effect-guard" "true" "Side-effect skill has disable-model-invocation: true"
    else
      emit "side-effect-guard" "false" "Skill contains ${SIDE_EFFECT_HITS} side-effect pattern(s) (destructive/infrastructure commands) but lacks disable-model-invocation: true"
    fi
  else
    emit "side-effect-guard" "true" "No side-effect patterns detected"
  fi
}

# ========================
# STANDALONE EXECUTION
# ========================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  source "$(dirname "$0")/_lib.sh" "$1"
  check_persistent_state_xdg
  check_allowed_tools_usage
  check_side_effect_guard
  emit_summary
fi
