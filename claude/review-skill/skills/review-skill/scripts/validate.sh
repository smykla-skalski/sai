#!/usr/bin/env bash
# validate.sh — Validate SKILL.md frontmatter fields and directory structure.
#
# Usage:
#   bash validate.sh <skill-directory> [mode]
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

# ========================
# ARGUMENT PARSING
# ========================
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <skill-directory> [all|frontmatter|structure]" >&2
  exit 2
fi

SKILL_DIR="$1"
MODE="${2:-all}"
SKILL_MD="${SKILL_DIR}/SKILL.md"

# ========================
# COUNTERS
# ========================
TOTAL=0
PASSED=0
FAILED=0

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
  # Escape backslashes and double quotes for valid JSON
  detail="${detail//\\/\\\\}"
  detail="${detail//\"/\\\"}"
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
  '
}

# Detect the plugin root by walking up from the skill directory looking for
# .claude-plugin/plugin.json. Returns empty string if not found.
find_plugin_root() {
  local dir="$1"
  local i
  for i in 1 2 3 4; do
    dir=$(dirname "$dir")
    if [[ -f "${dir}/.claude-plugin/plugin.json" ]]; then
      echo "$dir"
      return
    fi
  done
  echo ""
}

# ========================
# PRE-FLIGHT
# ========================
if [[ ! -f "$SKILL_MD" ]]; then
  emit "skill-md-exists" "false" "SKILL.md not found in ${SKILL_DIR}"
  echo "{\"summary\": true, \"total\": ${TOTAL}, \"passed\": ${PASSED}, \"failed\": ${FAILED}}"
  exit 1
fi

# Extract frontmatter block (between first and second --- delimiters)
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_MD" | sed '1d;$d')

# Line number where body starts (after second ---)
BODY_START=$(grep -n "^---$" "$SKILL_MD" | sed -n '2p' | cut -d: -f1)

# Detect plugin root (if skill is inside a plugin)
PLUGIN_ROOT=$(find_plugin_root "$SKILL_DIR")

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

    local DESC_LOWER
    DESC_LOWER=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')
    if echo "$DESC_LOWER" | grep -qE '\b(when|use|for)\b'; then
      emit "description-trigger-phrases" "true" "Description includes trigger phrase (when/use/for)"
    else
      emit "description-trigger-phrases" "false" "Description should include a trigger phrase (when/use/for) for discoverability"
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
  # --- body line count (<=500) ---
  if [[ -n "$BODY_START" ]]; then
    local TOTAL_LINES BODY_LINES
    TOTAL_LINES=$(wc -l < "$SKILL_MD" | tr -d ' ')
    BODY_LINES=$(( TOTAL_LINES - BODY_START ))
    if [[ "$BODY_LINES" -le 500 ]]; then
      emit "body-line-count" "true" "SKILL.md body is ${BODY_LINES} lines (limit 500)"
    else
      emit "body-line-count" "false" "SKILL.md body is ${BODY_LINES} lines, exceeds 500-line limit"
    fi
  else
    emit "body-line-count" "false" "Could not locate frontmatter closing delimiter"
  fi

  # --- file references resolve ---
  # Extract body text, strip fenced code blocks to avoid matching example paths.
  # Per the Agent Skills spec, bundled resources (references/, scripts/, assets/,
  # examples/) belong alongside SKILL.md in the skill directory. If a reference
  # is not found there but exists at the plugin root, report it as misplaced.
  local SKILL_BODY REFERENCED_FILES
  SKILL_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')
  REFERENCED_FILES=$(echo "$SKILL_BODY" \
    | grep -oE '(references/[a-zA-Z0-9._-]+|scripts/[a-zA-Z0-9._-]+|assets/[a-zA-Z0-9._-]+|examples/[a-zA-Z0-9._-]+)' \
    | grep -vE '/(\.\.\.|\.\.\.|[a-z]\.md|foo\.|bar\.|baz\.|example\.)' \
    | sort -u || true)

  if [[ -n "$REFERENCED_FILES" ]]; then
    while IFS= read -r ref; do
      local CANONICAL_PATH="${SKILL_DIR}/${ref}"
      if [[ -e "$CANONICAL_PATH" ]]; then
        # Found at canonical location (alongside SKILL.md)
        emit "file-ref-resolves" "true" "Reference '${ref}' resolves in skill directory"
      elif [[ -n "$PLUGIN_ROOT" ]] && [[ -e "${PLUGIN_ROOT}/${ref}" ]]; then
        # Found at plugin root but not in skill dir — misplaced
        emit "file-ref-resolves" "false" "Reference '${ref}' found at plugin root but not in skill directory — move to ${CANONICAL_PATH}"
      else
        # Not found anywhere
        emit "file-ref-resolves" "false" "Reference '${ref}' not found — expected at ${CANONICAL_PATH}"
      fi
    done <<< "$REFERENCED_FILES"
  else
    emit "file-ref-resolves" "true" "No file references found in SKILL.md"
  fi

  # --- script invocations use $SKILL_DIR prefix (I6) ---
  # If the skill has a scripts/ directory, check that script references in the
  # body use $SKILL_DIR/scripts/ — bare paths like `scripts/foo.sh` resolve
  # relative to the wrong directory in plugin cache.
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    # Find lines mentioning scripts/*.sh without $SKILL_DIR prefix.
    # Exclude markdown headers (### `scripts/...`) which are documentation.
    local BARE_REFS
    BARE_REFS=$(echo "$SKILL_BODY" \
      | grep -E 'scripts/[a-zA-Z0-9._-]+\.sh' \
      | grep -vE '^\s*#{1,6}\s' \
      | grep -vE '\$SKILL_DIR' \
      || true)

    if [[ -n "$BARE_REFS" ]]; then
      local BARE_COUNT FIRST_BAD
      BARE_COUNT=$(echo "$BARE_REFS" | wc -l | tr -d ' ')
      FIRST_BAD=$(echo "$BARE_REFS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      emit "script-invocation-prefix" "false" "Found ${BARE_COUNT} script reference(s) without \$SKILL_DIR prefix — use bash \"\$SKILL_DIR/scripts/...\" — first: ${FIRST_BAD}"
    else
      emit "script-invocation-prefix" "true" "All script references use \$SKILL_DIR prefix"
    fi
  fi

  # --- no disallowed files in skill directory ---
  local DISALLOWED_FILES=("README.md" "CHANGELOG.md" "INSTALLATION_GUIDE.md")
  for f in "${DISALLOWED_FILES[@]}"; do
    if [[ -f "${SKILL_DIR}/${f}" ]]; then
      emit "no-disallowed-files" "false" "Disallowed file '${f}' found in skill directory"
    else
      emit "no-disallowed-files" "true" "'${f}' not present (correct)"
    fi
  done

  # --- references are one level deep (no cross-references between reference files) ---
  if [[ -d "${SKILL_DIR}/references" ]]; then
    for ref_file in "${SKILL_DIR}"/references/*; do
      [[ -f "$ref_file" ]] || continue
      local BASENAME STRIPPED
      BASENAME=$(basename "$ref_file")
      STRIPPED=$(sed '/^```/,/^```/d' "$ref_file" | sed 's/"[^"]*"//g')
      if echo "$STRIPPED" | grep -qE '\(references/[a-zA-Z0-9._-]+\)' 2>/dev/null; then
        emit "refs-one-level" "false" "Reference '${BASENAME}' cross-references other reference files"
      else
        emit "refs-one-level" "true" "Reference '${BASENAME}' does not cross-reference other files"
      fi
    done
  fi

  # --- long references (>100 lines) have table of contents ---
  if [[ -d "${SKILL_DIR}/references" ]]; then
    for ref_file in "${SKILL_DIR}"/references/*; do
      [[ -f "$ref_file" ]] || continue
      local BASENAME LINE_COUNT
      BASENAME=$(basename "$ref_file")
      LINE_COUNT=$(wc -l < "$ref_file" | tr -d ' ')
      if [[ "$LINE_COUNT" -gt 100 ]]; then
        if grep -qE '^#{1,2} Contents' "$ref_file" 2>/dev/null; then
          emit "long-ref-toc" "true" "Reference '${BASENAME}' (${LINE_COUNT} lines) has table of contents"
        else
          emit "long-ref-toc" "false" "Reference '${BASENAME}' (${LINE_COUNT} lines) exceeds 100 lines but has no '# Contents' heading"
        fi
      fi
    done
  fi

  # --- persistent state uses XDG paths, not relative or cache-relative ---
  # If the skill writes persistent state (findings/, .last-run, .covered-stories,
  # state files, artifacts), it must use XDG_DATA_HOME, not relative paths.
  # Plugin cache directories are replaced on version updates.
  local HAS_STATE_PATTERNS HAS_XDG_PATH
  HAS_STATE_PATTERNS=$(echo "$SKILL_BODY" \
    | grep -cE '\./findings/|\$SKILL_DIR/findings/|\.last-run|\.covered-|state stored in|persistent.*state|State Files' || true)
  HAS_XDG_PATH=$(echo "$SKILL_BODY" \
    | grep -cE 'XDG_DATA_HOME|\$HOME/\.local/share' || true)

  if [[ "$HAS_STATE_PATTERNS" -gt 0 ]]; then
    # Skill appears to use persistent state — check for proper XDG paths.
    # Prioritize XDG detection: if XDG paths are present, the skill is doing the
    # right thing and any ./findings/ mentions are likely warnings, not actual usage.
    local HAS_BAD_PATHS
    HAS_BAD_PATHS=$(echo "$SKILL_BODY" \
      | grep -cE '\./findings/|\$SKILL_DIR/findings/' || true)
    if [[ "$HAS_XDG_PATH" -gt 0 ]]; then
      emit "persistent-state-xdg" "true" "Persistent state uses XDG-compliant path"
    elif [[ "$HAS_BAD_PATHS" -gt 0 ]]; then
      emit "persistent-state-xdg" "false" "Skill uses relative paths (./findings/ or \$SKILL_DIR/findings/) for persistent state — use \${XDG_DATA_HOME:-\$HOME/.local/share}/sai/{plugin}/ instead"
    else
      emit "persistent-state-xdg" "true" "State references found but no relative path issues detected"
    fi
  fi

  # --- no grading/rubric style (C6) ---
  # Skills should give imperative instructions, not scoring rubrics with point
  # values, percentage weights, or letter grades. Require 2+ signals to fail.
  local GRADING_SIGNALS=0
  local GRADING_EVIDENCE=""

  # Point values: "10 points", "5 pts"
  if echo "$SKILL_BODY" | grep -qiE '\b[0-9]+\s+(points?|pts)\b'; then
    GRADING_SIGNALS=$((GRADING_SIGNALS + 1))
    GRADING_EVIDENCE="${GRADING_EVIDENCE}point-values "
  fi

  # Score/rating numeric assignments: "score: 4", "rating: 3"
  if echo "$SKILL_BODY" | grep -qiE '\b(score|rating)\s*:\s*[0-9]'; then
    GRADING_SIGNALS=$((GRADING_SIGNALS + 1))
    GRADING_EVIDENCE="${GRADING_EVIDENCE}score-assignments "
  fi

  # Percentage weights: "30% weight", "weight: 25%"
  if echo "$SKILL_BODY" | grep -qiE '\b[0-9]+%\s*(weight|of total)|\bweight[s]?\s*:?\s*[0-9]+%'; then
    GRADING_SIGNALS=$((GRADING_SIGNALS + 1))
    GRADING_EVIDENCE="${GRADING_EVIDENCE}percentage-weights "
  fi

  # Letter grade scales: "Grade: A", "A (90-100)"
  if echo "$SKILL_BODY" | grep -qiE '\bgrade\s*:?\s*[A-F]\b|\b[A-F]\s*\([0-9]+-[0-9]+'; then
    GRADING_SIGNALS=$((GRADING_SIGNALS + 1))
    GRADING_EVIDENCE="${GRADING_EVIDENCE}letter-grades "
  fi

  # Rubric keywords: "rubric", "scoring matrix", "grading scale/criteria"
  if echo "$SKILL_BODY" | grep -qiE '\brubric\b|\bscoring\s+matrix\b|\bgrading\s+(scale|criteria)\b'; then
    GRADING_SIGNALS=$((GRADING_SIGNALS + 1))
    GRADING_EVIDENCE="${GRADING_EVIDENCE}rubric-keywords "
  fi

  GRADING_EVIDENCE="${GRADING_EVIDENCE% }"

  if [[ "$GRADING_SIGNALS" -ge 2 ]]; then
    emit "no-grading-style" "false" "Grading/rubric style detected (${GRADING_SIGNALS} signals: ${GRADING_EVIDENCE}) — restructure as imperative workflow"
  else
    emit "no-grading-style" "true" "No grading/rubric style detected"
  fi

  # --- SKILL.md mentions all bundled resource files ---
  for subdir in references scripts assets examples; do
    if [[ -d "${SKILL_DIR}/${subdir}" ]]; then
      for file in "${SKILL_DIR}/${subdir}"/*; do
        [[ -f "$file" ]] || continue
        local BASENAME REL_PATH
        BASENAME=$(basename "$file")
        REL_PATH="${subdir}/${BASENAME}"
        if grep -q "$REL_PATH" "$SKILL_MD" 2>/dev/null; then
          emit "skill-md-mentions-file" "true" "SKILL.md mentions '${REL_PATH}'"
        else
          emit "skill-md-mentions-file" "false" "SKILL.md does not mention '${REL_PATH}' — all bundled files should be referenced"
        fi
      done
    fi
  done
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
echo "{\"summary\": true, \"total\": ${TOTAL}, \"passed\": ${PASSED}, \"failed\": ${FAILED}}"

# Exit 0 if all passed, 1 if any failed
[[ "$FAILED" -eq 0 ]]
