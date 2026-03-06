#!/usr/bin/env bash
# _lib.sh - Shared infrastructure for review-skill validation scripts.
# Source this file; do not execute directly.
#
# Usage from orchestrator:
#   SKILL_DIR="/path/to/skill"
#   source "${SCRIPT_DIR}/_lib.sh"
#
# Usage from standalone check script:
#   source "$(dirname "$0")/_lib.sh" "$1"
#
# Provides: emit(), get_field(), find_plugin_root(), _cleanup_tmp(),
#           emit_summary()
#
# Sets globals: SKILL_MD, FRONTMATTER, BODY_START, SKILL_BODY, FULL_BODY,
#               PLUGIN_ROOT, ALL_SKILL_FILES, TOTAL, PASSED, FAILED

# Accept SKILL_DIR from positional arg (standalone mode) or from caller
if [[ $# -ge 1 ]] && [[ -n "${1:-}" ]]; then
  SKILL_DIR="$1"
fi

if [[ -z "${SKILL_DIR:-}" ]]; then
  echo "Error: SKILL_DIR not set. Pass as argument or set before sourcing." >&2
  return 1 2>/dev/null || exit 1
fi

# ========================
# COUNTERS (preserve caller's values if already set)
# ========================
: "${TOTAL:=0}"
: "${PASSED:=0}"
: "${FAILED:=0}"

# ========================
# TEMP FILE CLEANUP
# ========================
_TMPFILES=()
_cleanup_tmp() {
  for _t in "${_TMPFILES[@]+"${_TMPFILES[@]}"}"; do
    if [[ -d "$_t" ]]; then
      rm -rf "$_t"
    elif [[ -f "$_t" ]]; then
      rm -f "$_t"
    fi
  done
}
trap _cleanup_tmp EXIT

# ========================
# HELPERS
# ========================

# Emit a single check result as JSON.
emit() {
  local check="$1" pass="$2" detail="$3"
  TOTAL=$((TOTAL + 1))
  if [[ "$pass" == "true" ]]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
  # Escape for valid JSON: backslashes, double quotes, and control chars
  detail="${detail//\\/\\\\}"
  detail="${detail//\"/\\\"}"
  detail="${detail//$'\n'/\\n}"
  detail="${detail//$'\t'/\\t}"
  detail="${detail//$'\r'/\\r}"
  echo "{\"check\": \"${check}\", \"pass\": ${pass}, \"detail\": \"${detail}\"}"
}

# Extract a YAML frontmatter field value.
# Handles single-line values, block scalars (>- > | |-), and YAML lists.
get_field() {
  local field="$1"
  echo "$FRONTMATTER" | awk -v f="$field" '
    BEGIN { found = 0; block = 0; buf = "" }
    !found && $0 ~ "^"f":" {
      found = 1
      val = $0
      sub("^"f":[[:space:]]*", "", val)
      if (val ~ /^[>|]-?[[:space:]]*$/ || val == "") {
        block = 1
        next
      }
      print val
      exit
    }
    found && block && /^[[:space:]]/ {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/^- /, "", line)
      buf = buf (buf ? " " : "") line
    }
    found && block && !/^[[:space:]]/ {
      print buf
      exit
    }
    END { if (block && buf != "") print buf }
  ' | sed 's/^["'"'"']//; s/["'"'"']$//'
}

# Detect the plugin root by walking up from the skill directory looking for
# .claude-plugin/plugin.json. Returns empty string if not found.
find_plugin_root() {
  local dir="$1"
  local _i
  for _i in 1 2 3 4; do
    dir=$(dirname "$dir")
    if [[ -f "${dir}/.claude-plugin/plugin.json" ]]; then
      echo "$dir"
      return
    fi
  done
  echo ""
}

# Emit summary JSON and return exit code.
emit_summary() {
  echo "{\"summary\": true, \"total\": ${TOTAL}, \"passed\": ${PASSED}, \"failed\": ${FAILED}}"
  [[ "$FAILED" -eq 0 ]]
}

# ========================
# PRE-FLIGHT & STATE EXTRACTION
# ========================
SKILL_MD="${SKILL_DIR}/SKILL.md"

if [[ ! -f "$SKILL_MD" ]]; then
  emit "skill-md-exists" "false" "SKILL.md not found in ${SKILL_DIR}"
  emit_summary
  return 1 2>/dev/null || exit 1
fi

# Extract frontmatter block (between first and second --- delimiters)
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_MD" | sed '1d;$d')

# Line number where body starts (after second ---)
BODY_START=$(grep -n "^---$" "$SKILL_MD" | sed -n '2p' | cut -d: -f1)

# Detect plugin root (if skill is inside a plugin)
# shellcheck disable=SC2034  # consumed by sourcing scripts
PLUGIN_ROOT=$(find_plugin_root "$SKILL_DIR")

# Extract body text: SKILL_BODY has code blocks stripped, FULL_BODY keeps them
if [[ -n "$BODY_START" ]]; then
  # shellcheck disable=SC2034
  SKILL_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')
  # shellcheck disable=SC2034
  FULL_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD")
else
  # shellcheck disable=SC2034
  SKILL_BODY=$(sed '/^```/,/^```/d' "$SKILL_MD")
  # shellcheck disable=SC2034
  FULL_BODY=$(cat "$SKILL_MD")
fi

# Build array of all files in the skill directory (SKILL.md + subdirs)
ALL_SKILL_FILES=("$SKILL_MD")
for _subdir in references scripts assets examples; do
  if [[ -d "${SKILL_DIR}/${_subdir}" ]]; then
    for _f in "${SKILL_DIR}/${_subdir}"/*; do
      [[ -f "$_f" ]] && ALL_SKILL_FILES+=("$_f")
    done
  fi
done
