#!/usr/bin/env bash
# validate-structure.sh — Validate skill directory structure and file references.
#
# Usage:
#   ./validate-structure.sh <skill-directory>
#
# Arguments:
#   skill-directory — Path to a skill directory containing SKILL.md
#
# Output: One JSON object per line with {check, pass, detail}.
#
# Dependencies: bash 4+, grep, sed, wc
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <skill-directory>" >&2
  exit 1
fi

SKILL_DIR="$1"
SKILL_MD="${SKILL_DIR}/SKILL.md"

if [[ ! -f "$SKILL_MD" ]]; then
  echo "{\"check\": \"skill-md-exists\", \"pass\": false, \"detail\": \"SKILL.md not found in ${SKILL_DIR}\"}"
  exit 0
fi

# --- Check: SKILL.md body line count (≤500) ---
# Body starts after the closing --- of frontmatter
BODY_START=$(grep -n "^---$" "$SKILL_MD" | sed -n '2p' | cut -d: -f1)

if [[ -n "$BODY_START" ]]; then
  TOTAL_LINES=$(wc -l < "$SKILL_MD" | tr -d ' ')
  BODY_LINES=$(( TOTAL_LINES - BODY_START ))
  if [[ "$BODY_LINES" -le 500 ]]; then
    echo "{\"check\": \"body-line-count\", \"pass\": true, \"detail\": \"SKILL.md body is ${BODY_LINES} lines (limit 500)\"}"
  else
    echo "{\"check\": \"body-line-count\", \"pass\": false, \"detail\": \"SKILL.md body is ${BODY_LINES} lines, exceeds 500-line limit\"}"
  fi
else
  echo "{\"check\": \"body-line-count\", \"pass\": false, \"detail\": \"Could not locate frontmatter closing delimiter\"}"
fi

# --- Check: file references resolve ---
# Strip fenced code blocks (``` ... ```) to avoid matching example paths, then scan for references.
# Also filter out obvious placeholder/example filenames (single-letter, "foo", "...").
SKILL_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')
REF_PATTERNS='(references/[a-zA-Z0-9._-]+|scripts/[a-zA-Z0-9._-]+)'
REFERENCED_FILES=$(echo "$SKILL_BODY" | grep -oE "$REF_PATTERNS" \
  | grep -vE '/(\.\.\.|\.\.\.|[a-z]\.md|foo\.|bar\.|baz\.|example\.)' \
  | sort -u || true)

ALL_REFS_RESOLVE=true
if [[ -n "$REFERENCED_FILES" ]]; then
  while IFS= read -r ref; do
    FULL_PATH="${SKILL_DIR}/${ref}"
    if [[ -e "$FULL_PATH" ]]; then
      echo "{\"check\": \"file-ref-resolves\", \"pass\": true, \"detail\": \"Reference '${ref}' resolves to existing file\"}"
    else
      echo "{\"check\": \"file-ref-resolves\", \"pass\": false, \"detail\": \"Reference '${ref}' does not resolve — file not found\"}"
      ALL_REFS_RESOLVE=false
    fi
  done <<< "$REFERENCED_FILES"
else
  echo "{\"check\": \"file-ref-resolves\", \"pass\": true, \"detail\": \"No file references found in SKILL.md\"}"
fi

# --- Check: no disallowed files (README.md, CHANGELOG.md, INSTALLATION_GUIDE.md) ---
DISALLOWED_FILES=("README.md" "CHANGELOG.md" "INSTALLATION_GUIDE.md")
for f in "${DISALLOWED_FILES[@]}"; do
  if [[ -f "${SKILL_DIR}/${f}" ]]; then
    echo "{\"check\": \"no-disallowed-files\", \"pass\": false, \"detail\": \"Disallowed file '${f}' found in skill directory\"}"
  else
    echo "{\"check\": \"no-disallowed-files\", \"pass\": true, \"detail\": \"'${f}' not present (correct)\"}"
  fi
done

# --- Check: references are one level deep (no reference referencing another reference) ---
if [[ -d "${SKILL_DIR}/references" ]]; then
  for ref_file in "${SKILL_DIR}"/references/*; do
    [[ -f "$ref_file" ]] || continue
    BASENAME=$(basename "$ref_file")
    # Strip code blocks and quoted strings, then check for actual cross-references
    STRIPPED=$(sed '/^```/,/^```/d' "$ref_file" | sed 's/"[^"]*"//g')
    if echo "$STRIPPED" | grep -qE '\(references/[a-zA-Z0-9._-]+\)' 2>/dev/null; then
      echo "{\"check\": \"refs-one-level\", \"pass\": false, \"detail\": \"Reference '${BASENAME}' contains references to other reference files\"}"
    else
      echo "{\"check\": \"refs-one-level\", \"pass\": true, \"detail\": \"Reference '${BASENAME}' does not reference other reference files\"}"
    fi
  done
fi

# --- Check: long references (>100 lines) have table of contents ---
if [[ -d "${SKILL_DIR}/references" ]]; then
  for ref_file in "${SKILL_DIR}"/references/*; do
    [[ -f "$ref_file" ]] || continue
    BASENAME=$(basename "$ref_file")
    LINE_COUNT=$(wc -l < "$ref_file" | tr -d ' ')
    if [[ "$LINE_COUNT" -gt 100 ]]; then
      if grep -qE '^#{1,2} Contents' "$ref_file" 2>/dev/null; then
        echo "{\"check\": \"long-ref-toc\", \"pass\": true, \"detail\": \"Reference '${BASENAME}' (${LINE_COUNT} lines) has table of contents\"}"
      else
        echo "{\"check\": \"long-ref-toc\", \"pass\": false, \"detail\": \"Reference '${BASENAME}' (${LINE_COUNT} lines) exceeds 100 lines but lacks '# Contents' or '## Contents'\"}"
      fi
    fi
  done
fi

# --- Check: SKILL.md mentions all files in references/ and scripts/ ---
for subdir in references scripts; do
  if [[ -d "${SKILL_DIR}/${subdir}" ]]; then
    for file in "${SKILL_DIR}/${subdir}"/*; do
      [[ -f "$file" ]] || continue
      BASENAME=$(basename "$file")
      REL_PATH="${subdir}/${BASENAME}"
      if grep -q "$REL_PATH" "$SKILL_MD" 2>/dev/null; then
        echo "{\"check\": \"skill-md-mentions-file\", \"pass\": true, \"detail\": \"SKILL.md mentions '${REL_PATH}'\"}"
      else
        echo "{\"check\": \"skill-md-mentions-file\", \"pass\": false, \"detail\": \"SKILL.md does not mention '${REL_PATH}' — all support files should be referenced\"}"
      fi
    done
  fi
done
