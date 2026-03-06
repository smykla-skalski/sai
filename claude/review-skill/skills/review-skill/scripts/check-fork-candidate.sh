#!/usr/bin/env bash
# check-fork-candidate.sh — Analyze whether a skill should use context: fork + agent field.
#
# Usage:
#   check-fork-candidate.sh <skill-directory>
#
# Output: One JSON object per line (NDJSON).
#   Signal lines:   {"signal":"<id>","type":"positive|blocker|counter","detected":true|false,"detail":"<msg>"}
#   Summary line:   {"recommendation":"strong|soft|none","positive_count":N,...}
#
# Exit code: 0 if suggestion applies (strong or soft), 1 if no suggestion, 2 if usage error.
#
# Heuristics
# ----------
#
# Positive signals (each indicates the skill benefits from fork):
#
#   P1  High phase count — 5+ numbered phases generate intermediate context
#       that bloats the main conversation. Forking isolates this work.
#
#   P2  Structured output artifact — skill produces a self-contained
#       document, report, or digest with an explicit output section.
#       Fork returns a clean summary to the main conversation.
#       Excludes headers documenting internal wire formats (Script output,
#       JSON output, NDJSON output) which describe data structure, not
#       the skill's final deliverable.
#
#   P3  Data gathering — WebSearch or WebFetch in allowed-tools means heavy
#       intermediate fetching whose raw results pollute context.
#
#   P4  Manual subagent usage — Task in allowed-tools AND body mentions
#       spawning agents. The skill already does fork-like behavior manually;
#       context: fork would be a cleaner first-class mechanism.
#
#   P5  Heavy reference loading — 3+ reference files with 2+ explicit read
#       directives. Each read adds context overhead that fork isolates.
#
#   P6  Self-contained inputs — all input arrives via $ARGUMENTS with no
#       phrases that imply reliance on conversation history or the user's
#       current editor/buffer state. Fork-safe because no conversation
#       history is needed.
#
# Blocking signals (any one prevents the suggestion):
#
#   B1  Already forked — context: fork is already in frontmatter.
#
#   B2  Conversation-dependent — body contains phrases that reference prior
#       conversation context (e.g. "conversation history", "previously
#       discussed", "selected code"). Fork subagents have NO conversation
#       history, so the skill would break.
#
#   B3  Tiny skill — body under 40 lines. The overhead of spawning a
#       subagent is not justified for short skills.
#
#   B4  Background knowledge — user-invocable: false. These are context
#       enrichment skills, not standalone tasks. Fork is for task execution.
#
# Counter-signal (subtracts from effective positive count):
#
#   N1  Side-effect skill — disable-model-invocation: true OR body contains
#       destructive/infrastructure command patterns. These skills need
#       real-time user visibility; fork reduces control during execution
#       because the user only sees a summary after completion.
#
# Decision matrix:
#   Any blocker detected             → none   (skip suggestion)
#   effective_count = positives - N1
#   3+ effective                     → strong (recommend fork)
#   2  effective                     → soft   (consider fork)
#   0-1 effective                    → none   (not worth forking)
#
# Agent type suggestion:
#   WebSearch/WebFetch present       → Explore
#   Default                          → general-purpose
#
# Dependencies: bash 4+, awk, grep, sed, wc
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
  echo "{\"error\": true, \"detail\": \"SKILL.md not found in ${SKILL_DIR}\"}"
  exit 2
fi

# ========================
# EXTRACT FRONTMATTER + BODY
# ========================
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_MD" | sed '1d;$d')
BODY_START=$(grep -n "^---$" "$SKILL_MD" | sed -n '2p' | cut -d: -f1)

if [[ -z "$BODY_START" ]]; then
  echo "{\"error\": true, \"detail\": \"Could not locate frontmatter closing delimiter\"}"
  exit 2
fi

FULL_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD")
# Body with fenced code blocks stripped (for prose analysis only)
SKILL_BODY=$(echo "$FULL_BODY" | sed '/^```/,/^```/d')

# ========================
# HELPERS
# ========================

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

# Emit a signal detection result as JSON.
emit_signal() {
  local id="$1" type="$2" detected="$3" detail="$4"
  detail="${detail//\\/\\\\}"
  detail="${detail//\"/\\\"}"
  echo "{\"signal\": \"${id}\", \"type\": \"${type}\", \"detected\": ${detected}, \"detail\": \"${detail}\"}"
}

# ========================
# COUNTERS
# ========================
POSITIVE_COUNT=0
POSITIVE_IDS=""
BLOCKER_COUNT=0
BLOCKER_IDS=""
COUNTER_COUNT=0

# ========================
# BLOCKER SIGNALS
# ========================

# --- B1: Already forked ---
CONTEXT_FIELD=$(get_field "context")
if [[ "$CONTEXT_FIELD" == "fork" ]]; then
  emit_signal "B1" "blocker" "true" "Skill already uses context: fork"
  BLOCKER_COUNT=$((BLOCKER_COUNT + 1))
  BLOCKER_IDS="${BLOCKER_IDS}B1 "
else
  emit_signal "B1" "blocker" "false" "No context: fork in frontmatter"
fi

# --- B2: Conversation-dependent ---
# High-confidence phrases that require conversation history to function.
# Deliberately narrow to avoid false positives on self-referential language
# within the skill itself ("the criteria above" refers to the skill, not chat).
CONV_PATTERNS='conversation (context|history)|previous(ly)? (message|discussed|mentioned)|selected (code|text|block|content)|what (you|the user) (said|asked|want|mentioned)|from (the|our) (conversation|discussion|chat)'
CONV_HITS=$(echo "$SKILL_BODY" | grep -ciE "$CONV_PATTERNS" || true)

if [[ "$CONV_HITS" -gt 0 ]]; then
  FIRST_HIT=$(echo "$SKILL_BODY" | grep -iE "$CONV_PATTERNS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
  emit_signal "B2" "blocker" "true" "Conversation-dependent: ${FIRST_HIT}"
  BLOCKER_COUNT=$((BLOCKER_COUNT + 1))
  BLOCKER_IDS="${BLOCKER_IDS}B2 "
else
  emit_signal "B2" "blocker" "false" "No conversation-dependent phrases found"
fi

# --- B3: Tiny skill ---
TOTAL_LINES=$(wc -l < "$SKILL_MD" | tr -d ' ')
BODY_LINES=$(( TOTAL_LINES - BODY_START ))

if [[ "$BODY_LINES" -lt 40 ]]; then
  emit_signal "B3" "blocker" "true" "Body is ${BODY_LINES} lines (under 40) — fork overhead not justified"
  BLOCKER_COUNT=$((BLOCKER_COUNT + 1))
  BLOCKER_IDS="${BLOCKER_IDS}B3 "
else
  emit_signal "B3" "blocker" "false" "Body is ${BODY_LINES} lines"
fi

# --- B4: Background knowledge ---
USER_INVOCABLE=$(get_field "user-invocable")

if [[ "$USER_INVOCABLE" == "false" ]]; then
  emit_signal "B4" "blocker" "true" "user-invocable: false — context enrichment, not a standalone task"
  BLOCKER_COUNT=$((BLOCKER_COUNT + 1))
  BLOCKER_IDS="${BLOCKER_IDS}B4 "
else
  emit_signal "B4" "blocker" "false" "Skill is user-invocable"
fi

# ========================
# POSITIVE SIGNALS
# ========================

# --- P1: High phase count ---
# Count distinct "Phase N" or "Step N" headers (##-#### levels) outside code blocks.
PHASE_COUNT=$(echo "$SKILL_BODY" \
  | grep -ciE '^#{1,4}[[:space:]]+(Phase|Step)[[:space:]]+[0-9]+' || true)

if [[ "$PHASE_COUNT" -ge 5 ]]; then
  emit_signal "P1" "positive" "true" "${PHASE_COUNT} numbered phases — multi-phase workflow generates intermediate context"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P1 "
else
  emit_signal "P1" "positive" "false" "${PHASE_COUNT} numbered phases (threshold: 5)"
fi

# --- P2: Structured output artifact ---
# Look for section headers indicating the skill produces a self-contained
# document: Output, Report, Template, Artifact, Digest, Verdict.
# Exclude headers documenting internal wire/data formats — these describe
# script output structure (e.g. "Script output format", "JSON output"),
# not the skill's final deliverable returned to the user.
OUTPUT_KEYWORDS='Output|Report|Template|Artifact|Digest|Verdict'
EXCLUDE_PREFIX='(Script|JSON|NDJSON|Wire|Data|API|Log|Raw|Parse)'
OUTPUT_HEADERS=$(echo "$SKILL_BODY" \
  | grep -iE "^#{1,4}[[:space:]].*(${OUTPUT_KEYWORDS})" \
  || true)
# Filter out internal format documentation headers
if [[ -n "$OUTPUT_HEADERS" ]]; then
  OUTPUT_FILTERED=$(echo "$OUTPUT_HEADERS" \
    | grep -viE "${EXCLUDE_PREFIX}[[:space:]]+(output|format)" \
    || true)
else
  OUTPUT_FILTERED=""
fi
OUTPUT_COUNT=$(echo "$OUTPUT_FILTERED" | { grep -c '[^[:space:]]' || true; })

if [[ "$OUTPUT_COUNT" -gt 0 ]]; then
  FIRST_HEADER=$(echo "$OUTPUT_FILTERED" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-60)
  emit_signal "P2" "positive" "true" "Has structured output section: ${FIRST_HEADER}"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P2 "
else
  emit_signal "P2" "positive" "false" "No structured output/report/template section found"
fi

# --- P3: Data gathering ---
# WebSearch/WebFetch in allowed-tools or body indicates heavy intermediate
# fetching. Each search result bloats the main context window.
ALLOWED_TOOLS=$(get_field "allowed-tools")
AT_WEBSEARCH=$(echo "$ALLOWED_TOOLS" | grep -c 'WebSearch' || true)
AT_WEBFETCH=$(echo "$ALLOWED_TOOLS" | grep -c 'WebFetch' || true)
BODY_WEB=$(echo "$SKILL_BODY" | grep -ciE '\bWebSearch\b|\bWebFetch\b' || true)

if [[ $((AT_WEBSEARCH + AT_WEBFETCH + BODY_WEB)) -gt 0 ]]; then
  emit_signal "P3" "positive" "true" "Uses WebSearch/WebFetch — intermediate fetch results pollute context"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P3 "
else
  emit_signal "P3" "positive" "false" "No WebSearch/WebFetch usage detected"
fi

# --- P4: Manual subagent usage ---
# Task in allowed-tools + body mentions spawning/creating agents. The skill
# already isolates work into subagents manually — context: fork would replace
# this pattern with a first-class mechanism.
AT_TASK=$(echo "$ALLOWED_TOOLS" | grep -cw 'Task' || true)
BODY_SPAWN=$(echo "$SKILL_BODY" \
  | grep -ciE '\bspawn\b.*\bagent\b|\bagent\b.*\bspawn\b|\bTaskCreate\b|\bTask tool\b|\bsubagent\b' || true)
BODY_SPAWN2=$(echo "$SKILL_BODY" \
  | grep -ciE '\b(spawn|create|launch)\b.*(agent|task)\b' || true)

if [[ "$AT_TASK" -gt 0 ]] && [[ $((BODY_SPAWN + BODY_SPAWN2)) -gt 0 ]]; then
  emit_signal "P4" "positive" "true" "Task in allowed-tools + body spawns agents — already doing fork-like behavior manually"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P4 "
else
  if [[ "$AT_TASK" -gt 0 ]]; then
    emit_signal "P4" "positive" "false" "Task in allowed-tools but no spawn/agent keywords in body"
  else
    emit_signal "P4" "positive" "false" "No Task tool or agent spawning detected"
  fi
fi

# --- P5: Heavy reference loading ---
# 3+ reference files AND 2+ explicit read directives. Each reference read
# during execution adds material to the context window. Fork isolates all
# of this from the main conversation.
REF_COUNT=0
if [[ -d "${SKILL_DIR}/references" ]]; then
  REF_COUNT=$(find "${SKILL_DIR}/references" -maxdepth 1 -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
fi
READ_DIRECTIVES=$(echo "$SKILL_BODY" | grep -ciE '\b[Rr]ead\b.*references/' || true)

if [[ "$REF_COUNT" -ge 3 ]] && [[ "$READ_DIRECTIVES" -ge 2 ]]; then
  emit_signal "P5" "positive" "true" "${REF_COUNT} reference files + ${READ_DIRECTIVES} read directives — heavy context loading"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P5 "
else
  emit_signal "P5" "positive" "false" "${REF_COUNT} reference files, ${READ_DIRECTIVES} read directives (threshold: 3 files + 2 directives)"
fi

# --- P6: Self-contained inputs ---
# Skill explicitly parses $ARGUMENTS AND body does not contain phrases
# implying reliance on the user's current editor state or active file.
# These phrases are weaker than B2 blockers — they suggest implicit input
# from the session rather than hard conversation dependency.
HAS_ARGUMENTS=$(echo "$FULL_BODY" | grep -c '\$ARGUMENTS' || true)
IMPLICIT_INPUT=$(echo "$SKILL_BODY" \
  | grep -ciE '\b(current|active) (file|buffer|selection|PR|pull request|branch)\b|\bthis (file|code|PR|function|branch)\b' || true)

if [[ "$HAS_ARGUMENTS" -gt 0 ]] && [[ "$IMPLICIT_INPUT" -eq 0 ]]; then
  emit_signal "P6" "positive" "true" "All input via \$ARGUMENTS, no implicit session dependency"
  POSITIVE_COUNT=$((POSITIVE_COUNT + 1))
  POSITIVE_IDS="${POSITIVE_IDS}P6 "
elif [[ "$IMPLICIT_INPUT" -gt 0 ]]; then
  emit_signal "P6" "positive" "false" "Body references implicit session context (current file, this PR, etc.)"
else
  emit_signal "P6" "positive" "false" "No explicit \$ARGUMENTS parsing — input source unclear"
fi

# ========================
# COUNTER-SIGNAL
# ========================

# --- N1: Side-effect skill ---
# Skills with disable-model-invocation: true OR destructive command patterns
# need real-time user visibility. Fork summarizes results after completion,
# reducing the user's ability to intervene during execution.
DMI=$(get_field "disable-model-invocation")
SIDE_EFFECT_PATTERN='k3d (cluster|create|delete)|kind (create|delete) cluster|git reset|git branch -[dD]|git apply --cached|git clean -|git push --force|kubectl (delete|drain|cordon)|helm (uninstall|delete)|rm -rf'
SIDE_EFFECT_HITS=$(echo "$FULL_BODY" | grep -ciE "$SIDE_EFFECT_PATTERN" || true)

if [[ "$DMI" == "true" ]] || [[ "$SIDE_EFFECT_HITS" -gt 0 ]]; then
  local_detail=""
  if [[ "$DMI" == "true" ]] && [[ "$SIDE_EFFECT_HITS" -gt 0 ]]; then
    local_detail="disable-model-invocation: true + ${SIDE_EFFECT_HITS} destructive pattern(s)"
  elif [[ "$DMI" == "true" ]]; then
    local_detail="disable-model-invocation: true"
  else
    local_detail="${SIDE_EFFECT_HITS} destructive command pattern(s)"
  fi
  emit_signal "N1" "counter" "true" "Side-effect skill (${local_detail}) — fork reduces user visibility during execution"
  COUNTER_COUNT=1
else
  emit_signal "N1" "counter" "false" "No side-effect indicators"
fi

# ========================
# AGENT TYPE SUGGESTION
# ========================
AGENT_TYPE="general-purpose"
AGENT_REASON="default for task execution"

if [[ $((AT_WEBSEARCH + AT_WEBFETCH + BODY_WEB)) -gt 0 ]]; then
  AGENT_TYPE="Explore"
  AGENT_REASON="research-heavy skill benefits from Explore agent"
fi

# ========================
# DECISION
# ========================
BLOCKER_IDS=$(echo "$BLOCKER_IDS" | xargs)
POSITIVE_IDS=$(echo "$POSITIVE_IDS" | xargs)

EFFECTIVE_COUNT=$((POSITIVE_COUNT - COUNTER_COUNT))
if [[ "$EFFECTIVE_COUNT" -lt 0 ]]; then
  EFFECTIVE_COUNT=0
fi

RECOMMENDATION="none"
DETAIL=""

if [[ "$BLOCKER_COUNT" -gt 0 ]]; then
  RECOMMENDATION="none"
  DETAIL="Blocked by ${BLOCKER_IDS}. Not a fork candidate."
elif [[ "$EFFECTIVE_COUNT" -ge 3 ]]; then
  RECOMMENDATION="strong"
  DETAIL="Strong candidate for context: fork (${POSITIVE_COUNT} signals: ${POSITIVE_IDS}"
  if [[ "$COUNTER_COUNT" -gt 0 ]]; then
    DETAIL="${DETAIL}, minus N1 counter = ${EFFECTIVE_COUNT} effective"
  fi
  DETAIL="${DETAIL}). Add to frontmatter: context: fork, agent: ${AGENT_TYPE}. ${AGENT_REASON^}."
elif [[ "$EFFECTIVE_COUNT" -ge 2 ]]; then
  RECOMMENDATION="soft"
  DETAIL="Consider context: fork (${POSITIVE_COUNT} signals: ${POSITIVE_IDS}"
  if [[ "$COUNTER_COUNT" -gt 0 ]]; then
    DETAIL="${DETAIL}, minus N1 counter = ${EFFECTIVE_COUNT} effective"
  fi
  DETAIL="${DETAIL}). Fork would isolate intermediate work from the main context. Suggested agent: ${AGENT_TYPE}."
else
  DETAIL="Only ${EFFECTIVE_COUNT} effective signal(s)"
  if [[ "$COUNTER_COUNT" -gt 0 ]]; then
    DETAIL="${DETAIL} (${POSITIVE_COUNT} positive minus N1 counter)"
  fi
  DETAIL="${DETAIL} — fork overhead likely not justified."
fi

# Escape for JSON
DETAIL="${DETAIL//\\/\\\\}"
DETAIL="${DETAIL//\"/\\\"}"

echo "{\"recommendation\": \"${RECOMMENDATION}\", \"positive_count\": ${POSITIVE_COUNT}, \"effective_count\": ${EFFECTIVE_COUNT}, \"positive_ids\": \"${POSITIVE_IDS}\", \"blocker_count\": ${BLOCKER_COUNT}, \"blocker_ids\": \"${BLOCKER_IDS}\", \"counter_count\": ${COUNTER_COUNT}, \"agent_type\": \"${AGENT_TYPE}\", \"detail\": \"${DETAIL}\"}"

# Exit 0 if suggestion applies, 1 if not
[[ "$RECOMMENDATION" != "none" ]]
