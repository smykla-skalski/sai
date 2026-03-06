#!/usr/bin/env bash
# check-read-gates.sh — Validate reference file read gates in SKILL.md.
#
# Usage:
#   check-read-gates.sh <skill-directory>
#
# Output: One JSON object per line:
#   {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
#
# Final line is always a summary:
#   {"summary": true, "total": N, "passed": N, "failed": N, "refs": N}
#
# Sub-checks:
#   RG-GATE    — Every linked reference has an explicit load directive
#   RG-PASSIVE — No passive weak mentions without a preceding gate
#   RG-ORPHAN  — No files on disk missing from SKILL.md entirely
#   RG-DEAD    — No references listed only in bundled resources section
#   RG-ORDER   — No reference cited before its gate appears
#   RG-PURPOSE — Read gates explain why (not bare path-only gates)
#   RG-FLOW    — Multi-flow skills gate references in each flow
#
# Exit code: 0 if all pass or no refs, 1 if any fail, 2 if usage error.
set -euo pipefail

# ========================
# ARGUMENT PARSING
# ========================
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <skill-directory>" >&2
  exit 2
fi

SKILL_DIR="$1"
SKILL_MD="${SKILL_DIR}/SKILL.md"

if [[ ! -f "$SKILL_MD" ]]; then
  echo "Error: ${SKILL_MD} not found" >&2
  exit 2
fi

# ========================
# COUNTERS
# ========================
TOTAL=0
PASSED=0
FAILED=0

# ========================
# HELPERS
# ========================
emit() {
  local check="$1" pass="$2" detail="$3"
  TOTAL=$((TOTAL + 1))
  if [[ "$pass" == "true" ]]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
  detail="${detail//\\/\\\\}"
  detail="${detail//\"/\\\"}"
  detail="${detail//$'\n'/\\n}"
  detail="${detail//$'\t'/\\t}"
  detail="${detail//$'\r'/\\r}"
  echo "{\"check\": \"${check}\", \"pass\": ${pass}, \"detail\": \"${detail}\"}"
}

# ========================
# EXTRACT BODY (skip frontmatter)
# ========================
BODY_START=$(awk '
  /^---$/ && !got_minus { count++; if (count == 2) { print NR + 1; exit } }
  /^--- a\// { got_minus = 1; next }
  /^\+\+\+/ && got_minus { got_plus = 1; got_minus = 0; next }
' "$SKILL_MD")
if [[ -z "$BODY_START" ]]; then
  echo "{\"summary\": true, \"total\": 0, \"passed\": 0, \"failed\": 0, \"refs\": 0}"
  exit 0
fi

# Body with fenced code blocks removed (for existence checks).
# Only strips blocks starting at column 0 — indented code blocks survive.
[[ -n "$BODY_START" ]] || exit 0
BODY_STRIPPED=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')

# Prose lines with original line numbers (for ordering checks).
# Strips fenced code blocks starting at column 0.
BODY_NUMBERED=$(awk -v start="$BODY_START" '
  NR < start { next }
  /^```/ { fence = !fence; next }
  fence { next }
  { printf "%d:%s\n", NR, $0 }
' "$SKILL_MD")

# Full file content (for orphan check — refs can appear in frontmatter too)
FULL_FILE=$(cat "$SKILL_MD")

# ========================
# REFERENCE INVENTORY
# ========================

# Linked: markdown links (references/*.md) and (examples/*.md) from body
LINKED_REFS=$(echo "$BODY_STRIPPED" \
  | grep -oE '\((references|examples)/[a-zA-Z0-9._-]+\.md\)' \
  | sed 's/^(//;s/)$//' \
  | sort -u || true)

# Disk: actual files in references/ and examples/
DISK_REFS=""
for subdir in references examples; do
  if [[ -d "${SKILL_DIR}/${subdir}" ]]; then
    for f in "${SKILL_DIR}/${subdir}"/*.md; do
      [[ -f "$f" ]] || continue
      DISK_REFS="${DISK_REFS}${subdir}/$(basename "$f")"$'\n'
    done
  fi
done
DISK_REFS=$(echo "$DISK_REFS" | grep -v '^$' | sort -u || true)

# Union of linked + disk
ALL_REFS=$(printf '%s\n%s\n' "$LINKED_REFS" "$DISK_REFS" | grep -v '^$' | sort -u || true)

REF_COUNT=0
if [[ -n "$ALL_REFS" ]]; then
  REF_COUNT=$(echo "$ALL_REFS" | wc -l | tr -d ' ')
fi

# If no refs at all, emit summary and exit
if [[ "$REF_COUNT" -eq 0 ]]; then
  echo "{\"summary\": true, \"total\": 0, \"passed\": 0, \"failed\": 0, \"refs\": 0}"
  exit 0
fi

# ========================
# BUNDLED RESOURCES SECTION
# ========================
# Find "## Bundled" header in BODY_NUMBERED, track range to next ## or EOF.
BUNDLED_START=""
BUNDLED_END=""
BUNDLED_START=$(echo "$BODY_NUMBERED" | grep -nE '^[0-9]+:## Bundled' | head -1 | cut -d: -f1 || true)

if [[ -n "$BUNDLED_START" ]]; then
  # Get the original line number of the bundled header
  BUNDLED_ORIG_LINE=$(echo "$BODY_NUMBERED" | sed -n "${BUNDLED_START}p" | cut -d: -f1)
  # Find the next ## header after the bundled section
  BUNDLED_END=$(echo "$BODY_NUMBERED" | awk -F: -v bstart="$BUNDLED_ORIG_LINE" '
    $1 > bstart && $2 ~ /^## [^#]/ { print $1; exit }
  ')
  if [[ -z "$BUNDLED_END" ]]; then
    # Bundled section extends to EOF
    BUNDLED_END=999999
  fi
fi

# Helper: check if a line number falls within the bundled section
in_bundled() {
  local line="$1"
  if [[ -z "$BUNDLED_START" ]]; then
    return 1
  fi
  [[ "$line" -ge "$BUNDLED_ORIG_LINE" && "$line" -lt "$BUNDLED_END" ]]
}

# ========================
# ALTERNATIVE FLOW DETECTION (for RG-FLOW)
# ========================
# Heuristic: multiple "## Workflow" headers, or headers containing
# "mode" / "alternative" / "fallback".
WORKFLOW_HEADERS=$(echo "$BODY_NUMBERED" | grep -iE '^[0-9]+:## .*[Ww]orkflow' || true)
WORKFLOW_COUNT=0
if [[ -n "$WORKFLOW_HEADERS" ]]; then
  WORKFLOW_COUNT=$(echo "$WORKFLOW_HEADERS" | wc -l | tr -d ' ')
fi

MODE_HEADERS=$(echo "$BODY_NUMBERED" | grep -iE '^[0-9]+:##+ .*(mode|alternative|fallback)' || true)
IS_MULTI_FLOW="false"
if [[ "$WORKFLOW_COUNT" -ge 2 ]] || [[ -n "$MODE_HEADERS" ]]; then
  IS_MULTI_FLOW="true"
fi

# Build a list of flow sections: line ranges for each workflow/mode section
# Each entry: START_LINE:END_LINE:HEADER_TEXT
FLOW_SECTIONS=""
if [[ "$IS_MULTI_FLOW" == "true" ]]; then
  # Collect all ## Workflow headers with their line numbers
  FLOW_HEADER_LINES=$(echo "$BODY_NUMBERED" | grep -iE '^[0-9]+:## .*[Ww]orkflow' | while IFS=: read -r lnum rest; do
    echo "$lnum"
  done || true)

  if [[ -n "$FLOW_HEADER_LINES" ]]; then
    PREV_LINE=""
    PREV_TEXT=""
    while IFS= read -r line; do
      ORIG_LINE=$(echo "$line" | cut -d: -f1)
      HEADER_TEXT=$(echo "$line" | cut -d: -f2-)
      if [[ -n "$PREV_LINE" ]]; then
        FLOW_SECTIONS="${FLOW_SECTIONS}${PREV_LINE}:${ORIG_LINE}:${PREV_TEXT}"$'\n'
      fi
      PREV_LINE="$ORIG_LINE"
      PREV_TEXT="$HEADER_TEXT"
    done <<< "$(echo "$BODY_NUMBERED" | grep -iE '^[0-9]+:## .*[Ww]orkflow')"
    # Last section extends to EOF
    if [[ -n "$PREV_LINE" ]]; then
      FLOW_SECTIONS="${FLOW_SECTIONS}${PREV_LINE}:999999:${PREV_TEXT}"$'\n'
    fi
  fi
fi

# ========================
# CHECK FUNCTIONS
# ========================

# For a given ref path, find the first gate line number in BODY_NUMBERED
find_gate_line() {
  local ref="$1"
  local escaped
  escaped=$(echo "$ref" | sed 's/\./\\./g')
  echo "$BODY_NUMBERED" | grep -iE '(Read|Contents of|path to|Load)[[:space:]]' | grep -iF "$ref" | head -1 | cut -d: -f1 || true
}

# For a given ref path, check if it has any gate in BODY_STRIPPED
has_gate() {
  local ref="$1"
  echo "$BODY_STRIPPED" | grep -iE '(Read|Contents of|path to|Load)[[:space:]]' | grep -qiF "$ref"
}

# For a given ref, find passive mentions with line numbers (non-gate, non-bundled)
find_passive_mentions() {
  local ref="$1"
  # Find lines mentioning the ref that are NOT gates
  echo "$BODY_NUMBERED" | grep -iF "$ref" | while IFS= read -r line; do
    local lnum
    lnum=$(echo "$line" | cut -d: -f1)
    local content
    content=$(echo "$line" | cut -d: -f2-)
    # Skip if this line is a gate
    if echo "$content" | grep -iE '(Read|Contents of|path to|Load)[[:space:]]' | grep -qiF "$ref"; then
      continue
    fi
    # Skip if in bundled section
    if in_bundled "$lnum"; then
      continue
    fi
    # Check if it matches passive patterns
    # "from" is passive UNLESS preceded by "Contents"
    if echo "$content" | grep -iE '(See|are in|is in|Consult|per|available in|described in|defined in|documented in)' | grep -qiF "$ref"; then
      echo "$lnum"
    elif echo "$content" | grep -iE 'from' | grep -iF "$ref" | grep -qviE 'Contents from'; then
      echo "$lnum"
    fi
  done || true
}

# For a given ref, find all non-gate, non-bundled mention line numbers
find_use_lines() {
  local ref="$1"
  echo "$BODY_NUMBERED" | grep -iF "$ref" | while IFS= read -r line; do
    local lnum
    lnum=$(echo "$line" | cut -d: -f1)
    local content
    content=$(echo "$line" | cut -d: -f2-)
    # Skip gates
    if echo "$content" | grep -iE '(Read|Contents of|path to|Load)[[:space:]]' | grep -qiF "$ref"; then
      continue
    fi
    # Skip bundled
    if in_bundled "$lnum"; then
      continue
    fi
    echo "$lnum"
  done || true
}

# ========================
# RG-GATE: ref-gate-present
# ========================
GATE_FAILS=""
while IFS= read -r ref; do
  [[ -z "$ref" ]] && continue
  # Only check refs that are linked (appear in markdown links in the body)
  if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
    continue
  fi
  if ! has_gate "$ref"; then
    GATE_FAILS="${GATE_FAILS} ${ref}"
  fi
done <<< "$ALL_REFS"
GATE_FAILS=$(echo "$GATE_FAILS" | xargs)

if [[ -n "$GATE_FAILS" ]]; then
  GATE_COUNT=$(echo "$GATE_FAILS" | wc -w | tr -d ' ')
  emit "ref-gate-present" "false" "${GATE_COUNT} reference(s) linked without explicit load directive (Read, Contents of, path to, Load): ${GATE_FAILS}"
else
  emit "ref-gate-present" "true" "All linked references have explicit load directives"
fi

# ========================
# RG-PASSIVE: ref-passive-mention
# ========================
PASSIVE_FAILS=""
PASSIVE_DETAIL=""
while IFS= read -r ref; do
  [[ -z "$ref" ]] && continue
  if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
    continue
  fi
  PASSIVES=$(find_passive_mentions "$ref")
  if [[ -n "$PASSIVES" ]]; then
    GATE_LINE=$(find_gate_line "$ref")
    # Only flag passive mentions that appear BEFORE the gate
    while IFS= read -r pline; do
      [[ -z "$pline" ]] && continue
      if [[ -z "$GATE_LINE" ]] || [[ "$pline" -lt "$GATE_LINE" ]]; then
        PASSIVE_FAILS="${PASSIVE_FAILS} ${ref}"
        PASSIVE_DETAIL="${PASSIVE_DETAIL} ${ref}:L${pline}"
        break
      fi
    done <<< "$PASSIVES"
  fi
done <<< "$ALL_REFS"
PASSIVE_FAILS=$(echo "$PASSIVE_FAILS" | xargs)
PASSIVE_DETAIL=$(echo "$PASSIVE_DETAIL" | xargs)

if [[ -n "$PASSIVE_FAILS" ]]; then
  PASSIVE_COUNT=$(echo "$PASSIVE_FAILS" | tr ' ' '\n' | sort -u | wc -l | tr -d ' ')
  emit "ref-passive-mention" "false" "${PASSIVE_COUNT} reference(s) have passive mentions before their gate: ${PASSIVE_DETAIL}"
else
  emit "ref-passive-mention" "true" "No passive weak mentions found before gates"
fi

# ========================
# RG-ORPHAN: ref-orphan-file
# ========================
ORPHAN_FAILS=""
while IFS= read -r ref; do
  [[ -z "$ref" ]] && continue
  # Only check disk refs — orphans are files that exist but aren't mentioned
  if ! echo "$DISK_REFS" | grep -qF "$ref"; then
    continue
  fi
  # Check if mentioned ANYWHERE in the full file (not just body)
  if ! echo "$FULL_FILE" | grep -qF "$ref"; then
    ORPHAN_FAILS="${ORPHAN_FAILS} ${ref}"
  fi
done <<< "$ALL_REFS"
ORPHAN_FAILS=$(echo "$ORPHAN_FAILS" | xargs)

if [[ -n "$ORPHAN_FAILS" ]]; then
  ORPHAN_COUNT=$(echo "$ORPHAN_FAILS" | wc -w | tr -d ' ')
  emit "ref-orphan-file" "false" "${ORPHAN_COUNT} file(s) on disk not mentioned in SKILL.md: ${ORPHAN_FAILS}"
else
  emit "ref-orphan-file" "true" "All disk files are mentioned in SKILL.md"
fi

# ========================
# RG-DEAD: ref-dead-listing
# ========================
DEAD_FAILS=""
if [[ -n "$BUNDLED_START" ]]; then
  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
      continue
    fi
    # Skip refs already flagged as orphan (disjoint by definition)
    if echo "$ORPHAN_FAILS" | grep -qF "$ref" 2>/dev/null; then
      continue
    fi
    _escaped=$(echo "$ref" | sed 's/\./\\./g')
    # Check if ref appears in body OUTSIDE the bundled section
    HAS_OUTSIDE="false"
    while IFS= read -r _dl; do
      [[ -z "$_dl" ]] && continue
      _dlnum=$(echo "$_dl" | cut -d: -f1)
      if ! in_bundled "$_dlnum"; then
        HAS_OUTSIDE="true"
        break
      fi
    done <<< "$(echo "$BODY_NUMBERED" | grep -iE "${_escaped}" || true)"
    if [[ "$HAS_OUTSIDE" == "false" ]]; then
      DEAD_FAILS="${DEAD_FAILS} ${ref}"
    fi
  done <<< "$ALL_REFS"
fi
DEAD_FAILS=$(echo "$DEAD_FAILS" | xargs)

if [[ -n "$DEAD_FAILS" ]]; then
  DEAD_COUNT=$(echo "$DEAD_FAILS" | wc -w | tr -d ' ')
  emit "ref-dead-listing" "false" "${DEAD_COUNT} reference(s) only appear in bundled resources section, never used in workflow: ${DEAD_FAILS}"
else
  emit "ref-dead-listing" "true" "No dead bundled-only listings found"
fi

# ========================
# RG-ORDER: ref-use-before-gate
# ========================
ORDER_FAILS=""
ORDER_DETAIL=""
while IFS= read -r ref; do
  [[ -z "$ref" ]] && continue
  if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
    continue
  fi
  GATE_LINE=$(find_gate_line "$ref")
  # Only check refs that HAVE a gate (ungated refs caught by RG-GATE)
  if [[ -z "$GATE_LINE" ]]; then
    continue
  fi
  # Find non-gate, non-bundled uses before the gate line
  USE_LINES=$(find_use_lines "$ref")
  if [[ -n "$USE_LINES" ]]; then
    FIRST_USE=$(echo "$USE_LINES" | head -1)
    if [[ -n "$FIRST_USE" ]] && [[ "$FIRST_USE" -lt "$GATE_LINE" ]]; then
      ORDER_FAILS="${ORDER_FAILS} ${ref}"
      ORDER_DETAIL="${ORDER_DETAIL} ${ref}:used-L${FIRST_USE}<gate-L${GATE_LINE}"
    fi
  fi
done <<< "$ALL_REFS"
ORDER_FAILS=$(echo "$ORDER_FAILS" | xargs)
ORDER_DETAIL=$(echo "$ORDER_DETAIL" | xargs)

if [[ -n "$ORDER_FAILS" ]]; then
  ORDER_COUNT=$(echo "$ORDER_FAILS" | wc -w | tr -d ' ')
  emit "ref-use-before-gate" "false" "${ORDER_COUNT} reference(s) cited before their gate: ${ORDER_DETAIL}"
else
  emit "ref-use-before-gate" "true" "All references are gated before first use"
fi

# ========================
# RG-PURPOSE: ref-gate-purpose
# ========================
PURPOSE_FAILS=""
while IFS= read -r ref; do
  [[ -z "$ref" ]] && continue
  if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
    continue
  fi
  GATE_LINE=$(find_gate_line "$ref")
  if [[ -z "$GATE_LINE" ]]; then
    continue
  fi
  # Get the full gate line content
  GATE_CONTENT=$(echo "$BODY_NUMBERED" | grep -E "^${GATE_LINE}:" | head -1 | cut -d: -f2-)
  if [[ -z "$GATE_CONTENT" ]]; then
    continue
  fi
  # Check if the line has substantive trailing text after the ref path.
  _escaped=$(echo "$ref" | sed 's/\./\\./g')
  # Get text after the ref link (after the closing paren of the markdown link)
  AFTER_REF=$(echo "$GATE_CONTENT" | sed -nE "s|.*${_escaped}\)\.?[[:space:]]*(.*)|\1|p")
  # Also check for purpose text before the ref: "Read X for Y" patterns where
  # "for Y" comes after the ref, or "before starting" comes after
  if [[ -z "$AFTER_REF" ]] || [[ "$AFTER_REF" =~ ^\.?$ ]]; then
    # Line ends with just the ref path (+ optional period) — check for
    # accepted trailing patterns within the full line
    if echo "$GATE_CONTENT" | grep -qiE "(for |before |in full|when |, then |to understand|to learn)"; then
      continue
    fi
    PURPOSE_FAILS="${PURPOSE_FAILS} ${ref}"
  fi
done <<< "$ALL_REFS"
PURPOSE_FAILS=$(echo "$PURPOSE_FAILS" | xargs)

if [[ -n "$PURPOSE_FAILS" ]]; then
  PURPOSE_COUNT=$(echo "$PURPOSE_FAILS" | wc -w | tr -d ' ')
  emit "ref-gate-purpose" "false" "${PURPOSE_COUNT} gate(s) lack purpose text (why to read): ${PURPOSE_FAILS}"
else
  emit "ref-gate-purpose" "true" "All read gates explain their purpose"
fi

# ========================
# RG-FLOW: ref-flow-coverage
# ========================
if [[ "$IS_MULTI_FLOW" == "true" ]] && [[ -n "$FLOW_SECTIONS" ]]; then
  FLOW_FAILS=""
  FLOW_DETAIL=""

  while IFS= read -r ref; do
    [[ -z "$ref" ]] && continue
    if ! echo "$LINKED_REFS" | grep -qF "$ref"; then
      continue
    fi
    _escaped=$(echo "$ref" | sed 's/\./\\./g')

    # Find which flow sections mention this ref (non-bundled)
    MENTIONED_FLOWS=""
    GATED_FLOWS=""
    while IFS= read -r section; do
      [[ -z "$section" ]] && continue
      SEC_START=$(echo "$section" | cut -d: -f1)
      SEC_END=$(echo "$section" | cut -d: -f2)
      SEC_NAME=$(echo "$section" | cut -d: -f3-)

      # Check if ref is mentioned in this flow section
      HAS_MENTION="false"
      HAS_GATE="false"
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        lnum=$(echo "$line" | cut -d: -f1)
        content=$(echo "$line" | cut -d: -f2-)
        if [[ "$lnum" -ge "$SEC_START" ]] && [[ "$lnum" -lt "$SEC_END" ]]; then
          if echo "$content" | grep -qiE "${_escaped}"; then
            HAS_MENTION="true"
            if echo "$content" | grep -qiE "${GATE_PATTERN}.*${_escaped}"; then
              HAS_GATE="true"
            fi
          fi
        fi
      done <<< "$(echo "$BODY_NUMBERED" | grep -iE "${_escaped}" || true)"

      if [[ "$HAS_MENTION" == "true" ]]; then
        MENTIONED_FLOWS="${MENTIONED_FLOWS}${SEC_NAME}"$'\n'
        if [[ "$HAS_GATE" == "true" ]]; then
          GATED_FLOWS="${GATED_FLOWS}${SEC_NAME}"$'\n'
        fi
      fi
    done <<< "$FLOW_SECTIONS"

    MENTION_COUNT=$(echo "$MENTIONED_FLOWS" | grep -c '[^ ]' || true)
    GATE_COUNT_F=$(echo "$GATED_FLOWS" | grep -c '[^ ]' || true)

    # If ref is mentioned in multiple flows but not gated in all of them
    if [[ "$MENTION_COUNT" -ge 2 ]] && [[ "$GATE_COUNT_F" -lt "$MENTION_COUNT" ]]; then
      FLOW_FAILS="${FLOW_FAILS} ${ref}"
      FLOW_DETAIL="${FLOW_DETAIL} ${ref}:gated-in-${GATE_COUNT_F}-of-${MENTION_COUNT}-flows"
    fi
  done <<< "$ALL_REFS"
  FLOW_FAILS=$(echo "$FLOW_FAILS" | xargs)
  FLOW_DETAIL=$(echo "$FLOW_DETAIL" | xargs)

  if [[ -n "$FLOW_FAILS" ]]; then
    FLOW_COUNT=$(echo "$FLOW_FAILS" | wc -w | tr -d ' ')
    emit "ref-flow-coverage" "false" "${FLOW_COUNT} reference(s) not gated in all workflow flows: ${FLOW_DETAIL}"
  else
    emit "ref-flow-coverage" "true" "All references gated in each workflow flow"
  fi
else
  emit "ref-flow-coverage" "true" "Single-flow skill, flow coverage check not applicable"
fi

# ========================
# SUMMARY
# ========================
echo "{\"summary\": true, \"total\": ${TOTAL}, \"passed\": ${PASSED}, \"failed\": ${FAILED}, \"refs\": ${REF_COUNT}}"

[[ "$FAILED" -eq 0 ]]
