#!/usr/bin/env bash
# check-references.sh - Reference file and body structure validation functions.
# Source from orchestrator or run standalone: ./check-references.sh <skill-dir>
#
# Functions: check_body_line_count, check_duplicate_codeblocks,
#   check_consistent_phase_numbering, check_long_ref_toc
#
# Requires _lib.sh globals: BODY_START, SKILL_MD, FULL_BODY, SKILL_BODY,
#   SKILL_DIR, _TMPFILES

# --- body line count (<=500) ---
check_body_line_count() {
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
}

# --- duplicated code blocks between SKILL.md and references (P8, informational) ---
check_duplicate_codeblocks() {
  if [[ -d "${SKILL_DIR}/references" ]]; then
    local DUP_COUNT=0
    local DUP_REFS_ARR=()

    local BLOCK_EXTRACT_AWK='
      /^```/ {
        if (in_block) {
          if (lines >= 3) {
            fn = dir "/b_" (++n)
            printf "%s", buf > fn
            close(fn)
          }
          in_block = 0; buf = ""; lines = 0
        } else {
          in_block = 1; buf = ""; lines = 0
        }
        next
      }
      in_block {
        sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, "")
        buf = (buf == "" ? $0 : buf "\n" $0)
        lines++
      }
    '

    # Extract and hash SKILL.md body code blocks
    local SKILL_BLOCK_DIR SKILL_HASH_FILE
    SKILL_BLOCK_DIR=$(mktemp -d); _TMPFILES+=("$SKILL_BLOCK_DIR")
    SKILL_HASH_FILE=$(mktemp); _TMPFILES+=("$SKILL_HASH_FILE")
    echo "$FULL_BODY" \
      | awk -v dir="$SKILL_BLOCK_DIR" "$BLOCK_EXTRACT_AWK"
    for bf in "$SKILL_BLOCK_DIR"/b_*; do
      [[ -f "$bf" ]] || continue
      shasum < "$bf" | cut -d' ' -f1
    done | sort -u > "$SKILL_HASH_FILE"
    rm -rf "$SKILL_BLOCK_DIR"

    if [[ -s "$SKILL_HASH_FILE" ]]; then
      for ref_file in "${SKILL_DIR}"/references/*.md; do
        [[ -f "$ref_file" ]] || continue
        local BASENAME
        BASENAME=$(basename "$ref_file")

        local REF_BLOCK_DIR REF_HASH_FILE
        REF_BLOCK_DIR=$(mktemp -d); _TMPFILES+=("$REF_BLOCK_DIR")
        REF_HASH_FILE=$(mktemp); _TMPFILES+=("$REF_HASH_FILE")
        awk -v dir="$REF_BLOCK_DIR" "$BLOCK_EXTRACT_AWK" "$ref_file"
        for bf in "$REF_BLOCK_DIR"/b_*; do
          [[ -f "$bf" ]] || continue
          shasum < "$bf" | cut -d' ' -f1
        done | sort -u > "$REF_HASH_FILE"
        rm -rf "$REF_BLOCK_DIR"

        local MATCH_COUNT
        MATCH_COUNT=$(comm -12 "$SKILL_HASH_FILE" "$REF_HASH_FILE" 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$MATCH_COUNT" -gt 0 ]]; then
          DUP_COUNT=$((DUP_COUNT + MATCH_COUNT))
          DUP_REFS_ARR+=("$BASENAME")
        fi
        rm -f "$REF_HASH_FILE"
      done
    fi

    rm -f "$SKILL_HASH_FILE"
    if [[ ${#DUP_REFS_ARR[@]} -gt 0 ]]; then
      local DUP_REFS
      DUP_REFS=$(printf '%s ' ${DUP_REFS_ARR[@]+"${DUP_REFS_ARR[@]}"})
      DUP_REFS="${DUP_REFS% }"
      emit "duplicate-codeblocks-info" "true" "INFO: ${DUP_COUNT} code block(s) (3+ lines) shared between SKILL.md and references: ${DUP_REFS} — review whether each is intentional for progressive disclosure"
    else
      emit "duplicate-codeblocks-info" "true" "No shared code blocks between SKILL.md and references"
    fi
  fi
}

# --- consistent phase numbering between SKILL.md and references (I14) ---
check_consistent_phase_numbering() {
  if [[ -d "${SKILL_DIR}/references" ]]; then
    local SKILL_PHASES
    SKILL_PHASES=$(echo "$SKILL_BODY" \
      | { grep -iE '^#{1,4}[[:space:]]+Phase[[:space:]]+[0-9]+' || true; } \
      | { grep -oE '[0-9]+' || true; } \
      | sort -n -u)
    local SKILL_PHASE_COUNT
    SKILL_PHASE_COUNT=$(echo "$SKILL_PHASES" | { grep -c '[0-9]' || true; })

    if [[ "$SKILL_PHASE_COUNT" -ge 2 ]]; then
      for ref_file in "${SKILL_DIR}"/references/*.md; do
        [[ -f "$ref_file" ]] || continue
        local BASENAME
        BASENAME=$(basename "$ref_file")
        local REF_PHASES
        REF_PHASES=$(sed '/^```/,/^```/d' "$ref_file" \
          | { grep -iE '^#{1,4}[[:space:]]+Phase[[:space:]]+[0-9]+' || true; } \
          | { grep -oE '[0-9]+' || true; } \
          | sort -n -u)
        local REF_PHASE_COUNT
        REF_PHASE_COUNT=$(echo "$REF_PHASES" | { grep -c '[0-9]' || true; })

        if [[ "$REF_PHASE_COUNT" -ge 2 ]]; then
          local OVERLAP
          OVERLAP=$(comm -12 <(echo "$SKILL_PHASES") <(echo "$REF_PHASES") 2>/dev/null | { grep -c '[0-9]' || true; })

          if [[ "$OVERLAP" -eq 0 ]]; then
            emit "consistent-phase-numbering" "true" "Phase ranges in '${BASENAME}' and SKILL.md are complementary (no overlap)"
          elif [[ "$SKILL_PHASES" == "$REF_PHASES" ]]; then
            emit "consistent-phase-numbering" "true" "Phase numbers in '${BASENAME}' match SKILL.md"
          else
            local SKILL_LIST REF_LIST
            SKILL_LIST=$(echo "$SKILL_PHASES" | tr '\n' ',' | sed 's/,$//')
            REF_LIST=$(echo "$REF_PHASES" | tr '\n' ',' | sed 's/,$//')
            emit "consistent-phase-numbering" "false" "Phase numbering mismatch: SKILL.md has [${SKILL_LIST}] but ${BASENAME} has [${REF_LIST}] (overlapping phases differ)"
          fi
        fi
      done
    fi
  fi
}

# --- long references (>100 lines) have table of contents ---
check_long_ref_toc() {
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
}

# ========================
# STANDALONE EXECUTION
# ========================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  source "$(dirname "$0")/_lib.sh" "$1"
  check_body_line_count
  check_duplicate_codeblocks
  check_consistent_phase_numbering
  check_long_ref_toc
  emit_summary
fi
