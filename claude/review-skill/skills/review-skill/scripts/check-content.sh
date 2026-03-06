#!/usr/bin/env bash
# check-content.sh - Content quality validation functions.
# Source from orchestrator or run standalone: ./check-content.sh <skill-dir>
#
# Functions: check_no_secrets, check_no_useless_echo, check_no_grading_style
#
# Requires _lib.sh globals: ALL_SKILL_FILES, SKILL_BODY

# --- no secrets or credentials (C7) ---
check_no_secrets() {
  local SECRET_HIT_FILES_ARR=()

  for sf in ${ALL_SKILL_FILES[@]+"${ALL_SKILL_FILES[@]}"}; do
    local MATCHES
    MATCHES=$(grep -oE 'AKIA[A-Z0-9]{16}|sk-[a-zA-Z0-9]{20,}|-----BEGIN[[:space:]]+(RSA |EC )?(PRIVATE )?KEY-----|Bearer[[:space:]]+[a-zA-Z0-9._-]{20,}' "$sf" 2>/dev/null || true)
    if [[ -n "$MATCHES" ]]; then
      local HAS_REAL="false"
      while IFS= read -r match; do
        if ! echo "$match" | grep -qiE '1234|0000|xxxx|abcdef|example|test|fake|placeholder|your_|INSERT|REPLACE|changeme'; then
          HAS_REAL="true"
          break
        fi
      done <<< "$MATCHES"
      if [[ "$HAS_REAL" == "true" ]]; then
        SECRET_HIT_FILES_ARR+=("$(basename "$sf")")
      fi
    fi
  done

  if [[ ${#SECRET_HIT_FILES_ARR[@]} -gt 0 ]]; then
    local SECRET_HIT_FILES
    SECRET_HIT_FILES=$(printf '%s ' ${SECRET_HIT_FILES_ARR[@]+"${SECRET_HIT_FILES_ARR[@]}"})
    SECRET_HIT_FILES="${SECRET_HIT_FILES% }"
    emit "no-secrets" "false" "Possible secrets or credentials found in: ${SECRET_HIT_FILES}"
  else
    emit "no-secrets" "true" "No secrets or credentials detected"
  fi
}

# --- no useless echo in code blocks (I13) ---
check_no_useless_echo() {
  local USELESS_ECHO_FILES_ARR=()
  local FIRST_ECHO_LINE=""

  for md_file in ${ALL_SKILL_FILES[@]+"${ALL_SKILL_FILES[@]}"}; do
    [[ "$md_file" == *.md ]] || continue
    local ECHO_HITS
    ECHO_HITS=$(awk '
      /^```/ {
        if (in_block) { in_block = 0 }
        else {
          lang = $0; sub(/^```/, "", lang); sub(/[[:space:]].*/, "", lang)
          if (lang == "" || lang == "bash" || lang == "sh" || lang == "shell")
            in_block = 1
        }
        next
      }
      in_block && /\$\(echo / {
        # Skip if the echo wraps a variable expansion — in skills context,
        # the subshell may serve as an agent execution signal even though
        # it is a no-op in pure bash.
        if ($0 !~ /\$\(echo[^)]*\$[A-Za-z_{]/) print
      }
    ' "$md_file" || true)
    if [[ -n "$ECHO_HITS" ]]; then
      USELESS_ECHO_FILES_ARR+=("$(basename "$md_file")")
      if [[ -z "$FIRST_ECHO_LINE" ]]; then
        FIRST_ECHO_LINE=$(echo "$ECHO_HITS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      fi
    fi
  done

  if [[ ${#USELESS_ECHO_FILES_ARR[@]} -gt 0 ]]; then
    local USELESS_ECHO_FILES
    USELESS_ECHO_FILES=$(printf '%s ' ${USELESS_ECHO_FILES_ARR[@]+"${USELESS_ECHO_FILES_ARR[@]}"})
    USELESS_ECHO_FILES="${USELESS_ECHO_FILES% }"
    emit "no-useless-echo" "false" "Useless echo (SC2116) in code blocks: ${USELESS_ECHO_FILES} — first: ${FIRST_ECHO_LINE}"
  else
    emit "no-useless-echo" "true" "No useless echo patterns in code blocks"
  fi
}

# --- no grading/rubric style (C6) ---
check_no_grading_style() {
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
}

# ========================
# STANDALONE EXECUTION
# ========================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  source "$(dirname "$0")/_lib.sh" "$1"
  check_no_secrets
  check_no_useless_echo
  check_no_grading_style
  emit_summary
fi
