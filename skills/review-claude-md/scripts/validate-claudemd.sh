#!/usr/bin/env bash
# validate-claudemd.sh — Validate CLAUDE.md structure and content quality.
#
# Usage:
#   ./validate-claudemd.sh <repo-root>
#
# Arguments:
#   repo-root — Path to the repository root containing CLAUDE.md
#
# Output: One JSON object per line with {check, pass, detail}.
#
# Dependencies: bash 4+, grep, sed, awk
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <repo-root>" >&2
  exit 1
fi

REPO_ROOT="$1"
CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"

if [[ ! -f "$CLAUDE_MD" ]]; then
  echo "{\"check\": \"file-exists\", \"pass\": false, \"detail\": \"CLAUDE.md not found in ${REPO_ROOT}\"}"
  exit 0
fi

CONTENT=$(cat "$CLAUDE_MD")

# --- Check: line-count ---
LINE_COUNT=$(echo "$CONTENT" | wc -l | tr -d ' ')
if [[ "$LINE_COUNT" -le 150 ]]; then
  echo "{\"check\": \"line-count\", \"pass\": true, \"detail\": \"${LINE_COUNT} lines, under 150 limit\"}"
else
  echo "{\"check\": \"line-count\", \"pass\": false, \"detail\": \"${LINE_COUNT} lines, exceeds 150 limit\"}"
fi

# --- Check: readme-duplication ---
README_MD="${REPO_ROOT}/README.md"
if [[ -f "$README_MD" ]]; then
  # Extract first 5 non-empty lines from each file
  CLAUDE_LINES=$(grep -v '^[[:space:]]*$' "$CLAUDE_MD" | head -5)
  README_LINES=$(grep -v '^[[:space:]]*$' "$README_MD" | head -5)

  SHARED=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    if echo "$README_LINES" | grep -qF "$line"; then
      SHARED=$((SHARED + 1))
    fi
  done <<< "$CLAUDE_LINES"

  if [[ "$SHARED" -ge 3 ]]; then
    echo "{\"check\": \"readme-duplication\", \"pass\": false, \"detail\": \"${SHARED}/5 leading lines overlap with README.md — likely duplication\"}"
  else
    echo "{\"check\": \"readme-duplication\", \"pass\": true, \"detail\": \"${SHARED}/5 leading lines shared with README.md\"}"
  fi
else
  echo "{\"check\": \"readme-duplication\", \"pass\": true, \"detail\": \"No README.md found, skipping duplication check\"}"
fi

# --- Check: generic-advice ---
GENERIC_PATTERNS=(
  "write clean code"
  "handle errors gracefully"
  "follow best practices"
  "always add tests"
  "keep code DRY"
  "use meaningful names"
)

GENERIC_FOUND=0
for pattern in "${GENERIC_PATTERNS[@]}"; do
  MATCH=$(grep -in "$pattern" "$CLAUDE_MD" || true)
  if [[ -n "$MATCH" ]]; then
    LINE_NUM=$(echo "$MATCH" | head -1 | cut -d: -f1)
    LINE_TEXT=$(echo "$MATCH" | head -1 | cut -d: -f2- | sed 's/^[[:space:]]*//' | cut -c1-80)
    echo "{\"check\": \"generic-advice\", \"pass\": false, \"detail\": \"Found: '${pattern}' on line ${LINE_NUM}: ${LINE_TEXT}\"}"
    GENERIC_FOUND=$((GENERIC_FOUND + 1))
  fi
done
if [[ "$GENERIC_FOUND" -eq 0 ]]; then
  echo "{\"check\": \"generic-advice\", \"pass\": true, \"detail\": \"No generic advice patterns found\"}"
fi

# --- Check: long-code-blocks ---
LONG_BLOCKS=0
IN_BLOCK=0
BLOCK_LINES=0
BLOCK_START=0
LINE_NUM=0
while IFS= read -r line; do
  LINE_NUM=$((LINE_NUM + 1))
  if [[ "$line" =~ ^\`\`\` ]]; then
    if [[ "$IN_BLOCK" -eq 0 ]]; then
      IN_BLOCK=1
      BLOCK_LINES=0
      BLOCK_START=$LINE_NUM
    else
      IN_BLOCK=0
      if [[ "$BLOCK_LINES" -gt 10 ]]; then
        echo "{\"check\": \"long-code-blocks\", \"pass\": false, \"detail\": \"Code block starting at line ${BLOCK_START} is ${BLOCK_LINES} lines (>10)\"}"
        LONG_BLOCKS=$((LONG_BLOCKS + 1))
      fi
    fi
  elif [[ "$IN_BLOCK" -eq 1 ]]; then
    BLOCK_LINES=$((BLOCK_LINES + 1))
  fi
done <<< "$CONTENT"
if [[ "$LONG_BLOCKS" -eq 0 ]]; then
  echo "{\"check\": \"long-code-blocks\", \"pass\": true, \"detail\": \"No code blocks exceed 10 lines\"}"
fi

# --- Check: bullets-vs-paragraphs ---
BULLET_LINES=0
PARA_LINES=0
CONSEC_PLAIN=0
while IFS= read -r line; do
  # Skip blank lines, headings, code fences
  if [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^#+\  ]] || [[ "$line" =~ ^\`\`\` ]]; then
    if [[ "$CONSEC_PLAIN" -ge 3 ]]; then
      PARA_LINES=$((PARA_LINES + CONSEC_PLAIN))
    fi
    CONSEC_PLAIN=0
    continue
  fi
  # Bullet lines: starts with - or * or numbered list
  if [[ "$line" =~ ^[[:space:]]*[-*] ]] || [[ "$line" =~ ^[[:space:]]*[0-9]+\. ]]; then
    if [[ "$CONSEC_PLAIN" -ge 3 ]]; then
      PARA_LINES=$((PARA_LINES + CONSEC_PLAIN))
    fi
    CONSEC_PLAIN=0
    BULLET_LINES=$((BULLET_LINES + 1))
  else
    CONSEC_PLAIN=$((CONSEC_PLAIN + 1))
  fi
done <<< "$CONTENT"
# Flush remaining
if [[ "$CONSEC_PLAIN" -ge 3 ]]; then
  PARA_LINES=$((PARA_LINES + CONSEC_PLAIN))
fi

TOTAL=$((BULLET_LINES + PARA_LINES))
if [[ "$TOTAL" -eq 0 ]]; then
  echo "{\"check\": \"bullets-vs-paragraphs\", \"pass\": true, \"detail\": \"No bullet or paragraph content detected\"}"
else
  RATIO=$((BULLET_LINES * 100 / TOTAL))
  if [[ "$RATIO" -gt 60 ]]; then
    echo "{\"check\": \"bullets-vs-paragraphs\", \"pass\": true, \"detail\": \"Bullet ratio ${RATIO}% (${BULLET_LINES} bullet lines, ${PARA_LINES} paragraph lines)\"}"
  else
    echo "{\"check\": \"bullets-vs-paragraphs\", \"pass\": false, \"detail\": \"Bullet ratio ${RATIO}% (${BULLET_LINES} bullet lines, ${PARA_LINES} paragraph lines) — prefer >60%\"}"
  fi
fi

# --- Check: modularization ---
if [[ "$LINE_COUNT" -gt 150 ]]; then
  if [[ -d "${REPO_ROOT}/.claude/rules" ]]; then
    echo "{\"check\": \"modularization\", \"pass\": true, \"detail\": \"CLAUDE.md is ${LINE_COUNT} lines but .claude/rules/ exists for modular rules\"}"
  else
    echo "{\"check\": \"modularization\", \"pass\": false, \"detail\": \"CLAUDE.md is ${LINE_COUNT} lines with no .claude/rules/ directory — consider splitting into modular rules\"}"
  fi
else
  echo "{\"check\": \"modularization\", \"pass\": true, \"detail\": \"CLAUDE.md is ${LINE_COUNT} lines, under modularization threshold\"}"
fi
