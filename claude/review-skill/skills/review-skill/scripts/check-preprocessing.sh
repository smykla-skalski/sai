#!/usr/bin/env bash
# check-preprocessing.sh — Validate !`command` shell preprocessing directives.
#
# Usage:
#   check-preprocessing.sh <skill-directory>
#
# Output: One JSON object per line:
#   {"check": "<sub-check>", "pass": true|false, "detail": "<message>"}
#
# Final line is always a summary:
#   {"summary": true, "total": N, "passed": N, "failed": N, "directives": N}
#
# Sub-checks:
#   P-ERR   — Commands that depend on external state lack error handling
#   P-OUT   — Commands that could produce large output lack limiting
#   P-SEC   — Commands that might leak secrets via env var expansion
#   P-MUT   — State-changing commands run at load time
#   P-SLOW  — Known slow commands block skill loading
#   P-DUP   — Redundant !`echo "${CLAUDE_SKILL_DIR}..."` wrapping
#   P-HANG  — Commands that wait for interactive input
#   P-SYNTAX — Malformed directive syntax
#
# Exit code: 0 if all pass or no directives found, 1 if any fail, 2 if usage error.
#
# References:
#   https://code.claude.com/docs/en/skills (Inject dynamic context)
#   https://www.365iwebdesign.co.uk/news/2026/01/29/how-to-use-dynamic-context-injection-claude-code/
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
BODY_START=$(awk '/^---$/ { count++; if (count == 2) { print NR + 1; exit } }' "$SKILL_MD")
if [[ -z "$BODY_START" ]]; then
  echo "{\"summary\": true, \"total\": 0, \"passed\": 0, \"failed\": 0, \"directives\": 0}"
  exit 0
fi

# Body with fenced code blocks stripped (we only check directives in prose)
BODY_NO_FENCE=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')

# ========================
# EXTRACT DIRECTIVES
# ========================
# Pattern: !` followed by content followed by closing `
# The ! must not be inside a fenced code block (already stripped above).
# Use grep -oE to extract each directive.
DIRECTIVES=$(echo "$BODY_NO_FENCE" | grep -oE '!`[^`]+`' 2>/dev/null || true)
DIRECTIVE_COUNT=0
if [[ -n "$DIRECTIVES" ]]; then
  DIRECTIVE_COUNT=$(echo "$DIRECTIVES" | wc -l | tr -d ' ')
fi

# If no directives, emit a single pass and exit
if [[ "$DIRECTIVE_COUNT" -eq 0 ]]; then
  echo "{\"summary\": true, \"total\": 0, \"passed\": 0, \"failed\": 0, \"directives\": 0}"
  exit 0
fi

# ========================
# CHECK FUNCTIONS
# ========================

# Extract the command string (strip leading !` and trailing `)
strip_directive() {
  local d="$1"
  d="${d#!\`}"
  d="${d%\`}"
  echo "$d"
}

# Get the primary command (first word, or first command in a pipe chain)
primary_cmd() {
  local cmd="$1"
  # Strip leading whitespace
  cmd="${cmd#"${cmd%%[![:space:]]*}"}"
  # Handle leading [ (test bracket)
  if [[ "$cmd" == "["* ]]; then
    echo "["
    return
  fi
  # Get first word
  echo "$cmd" | awk '{print $1}'
}

# P-ERR: Error handling check
# Commands that depend on external state should have error handling.
check_err() {
  local cmd="$1"
  local pcmd
  pcmd=$(primary_cmd "$cmd")

  # Safe commands that rarely fail — no error handling needed
  case "$pcmd" in
    echo|date|uname|whoami|pwd|hostname|id|basename|dirname|printf|true|mkdir|touch)
      return 0
      ;;
  esac

  # Check for error handling patterns anywhere in the command
  if echo "$cmd" | grep -qE '2>/dev/null|2>&1|\|\|[[:space:]]+(echo|true|printf|:)'; then
    return 0
  fi

  # Conditional pattern: && ... || ...
  if echo "$cmd" | grep -qE '&&.*\|\|'; then
    return 0
  fi

  return 1
}

# P-OUT: Output limiting check
# Commands that could produce unbounded output should limit it.
check_out() {
  local cmd="$1"
  local pcmd
  pcmd=$(primary_cmd "$cmd")

  # Commands that always produce bounded output (1-2 lines)
  case "$pcmd" in
    echo|date|uname|whoami|pwd|hostname|id|basename|dirname|printf|true|command)
      return 0
      ;;
  esac

  # Primary command output discarded to /dev/null, only echo/printf produces output
  # Pattern: cmd >/dev/null ... && echo ... || echo ...
  if echo "$cmd" | grep -qE '>/dev/null.*&&[[:space:]]*(echo|printf)'; then
    return 0
  fi

  # test bracket pattern: [ -f ... ] && echo ... || echo ...
  if [[ "$pcmd" == "[" ]] && echo "$cmd" | grep -qE '&&[[:space:]]*(echo|printf)'; then
    return 0
  fi

  # git commands — some are bounded, some aren't
  if [[ "$pcmd" == "git" ]]; then
    local subcmd
    subcmd=$(echo "$cmd" | awk '{print $2}')
    case "$subcmd" in
      # Bounded git commands
      branch|rev-parse|symbolic-ref|remote|for-each-ref|describe|config)
        return 0
        ;;
      # git log with explicit -N limit
      log)
        if echo "$cmd" | grep -qE -- '-[0-9]+|--oneline[[:space:]]+-[0-9]+'; then
          return 0
        fi
        ;;
      # git diff with --stat or --name-only is bounded
      diff)
        if echo "$cmd" | grep -qE -- '--stat|--name-only|--numstat|--shortstat'; then
          return 0
        fi
        ;;
      # git status --short is bounded-ish (one line per file)
      status)
        if echo "$cmd" | grep -qE -- '--short|-s'; then
          return 0
        fi
        ;;
    esac
  fi

  # node/python --version is bounded
  if echo "$cmd" | grep -qE '(node|python|python3|ruby|go|java|rustc|cargo|npm|yarn|pip)[[:space:]]+--version'; then
    return 0
  fi

  # Check for output limiting in pipe chain
  if echo "$cmd" | grep -qE '\|[[:space:]]*(head|tail|grep|wc|awk|sed|cut|sort|uniq|jq)'; then
    return 0
  fi

  # Commands known to produce potentially large output without limiting
  case "$pcmd" in
    cat|find|ls|grep|curl|wget|docker|kubectl|helm|npm|yarn|pip|cargo|make|mysql|psql)
      return 1
      ;;
    gh)
      # gh pr diff can be huge
      if echo "$cmd" | grep -qE 'pr[[:space:]]+diff'; then
        return 1
      fi
      return 0
      ;;
    git)
      # Unconstrained git commands (log without -N, diff without --stat)
      return 1
      ;;
  esac

  # Default: assume bounded for unknown commands
  return 0
}

# P-SEC: Secret leaking check
# Commands should not expose secrets into the prompt.
check_sec() {
  local cmd="$1"

  # Check for env vars with secret-like names being expanded
  # Pattern: $VAR_NAME or ${VAR_NAME} where name contains secret keywords
  if echo "$cmd" | grep -qiE '\$(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE_KEY|AUTH_TOKEN|AWS_SECRET|DB_PASS|MYSQL_PWD|PGPASSWORD|SMTP_PASS)|\$\{[^}]*(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE_KEY|AUTH_TOKEN|AWS_SECRET|DB_PASS|MYSQL_PWD|PGPASSWORD|SMTP_PASS)[^}]*\}'; then
    # Exception: if the command filters out secrets
    if echo "$cmd" | grep -qiE 'grep -v.*(SECRET|KEY|PASSWORD|TOKEN)'; then
      return 0
    fi
    return 1
  fi

  # Check for reading sensitive files
  if echo "$cmd" | grep -qE '(cat|head|tail|less|more)[[:space:]]+(~|\$HOME|\$\{HOME\})/\.(ssh/|aws/credentials|gnupg/)'; then
    return 1
  fi

  # Check for .env file access without filtering
  if echo "$cmd" | grep -qE '(cat|head|tail)[[:space:]]+\.env\b'; then
    if echo "$cmd" | grep -qiE 'grep -v.*(SECRET|KEY|PASSWORD|TOKEN)'; then
      return 0
    fi
    return 1
  fi

  return 0
}

# P-MUT: State-changing commands check
# Preprocessing runs at load time — no state changes allowed.
check_mut() {
  local cmd="$1"

  # Git write operations
  if echo "$cmd" | grep -qE '\bgit[[:space:]]+(commit|push|reset|checkout|clean|stash|rebase|merge|cherry-pick|tag[[:space:]]|remote[[:space:]]+(add|remove|rm)|branch[[:space:]]+-[dD])'; then
    return 1
  fi

  # Destructive file operations
  if echo "$cmd" | grep -qE '\b(rm|rmdir)[[:space:]]'; then
    return 1
  fi

  # mv is OK for checking existence, bad for moving files
  # Only flag mv when it looks like an actual move (has two args, not a pipe)
  if echo "$cmd" | grep -qE '\bmv[[:space:]]+[^|]+[[:space:]]+[^|]' && ! echo "$cmd" | grep -qE '\|'; then
    return 1
  fi

  # Package manager install/build (side effects)
  if echo "$cmd" | grep -qE '\b(npm|yarn|pnpm)[[:space:]]+(install|add|remove|uninstall|publish)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\b(pip|pip3)[[:space:]]+(install|uninstall)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\b(cargo)[[:space:]]+(install|publish)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bapt-get[[:space:]]+(install|remove|purge)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bbrew[[:space:]]+(install|uninstall|remove)\b'; then
    return 1
  fi

  # Kubernetes write operations
  if echo "$cmd" | grep -qE '\bkubectl[[:space:]]+(apply|create|delete|patch|replace|drain|cordon|taint|rollout)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bhelm[[:space:]]+(install|upgrade|uninstall|delete|rollback)\b'; then
    return 1
  fi

  # Docker write operations
  if echo "$cmd" | grep -qE '\bdocker[[:space:]]+(run|build|push|pull|rm|rmi|stop|kill|restart|create)\b'; then
    return 1
  fi

  # k3d/kind cluster operations
  if echo "$cmd" | grep -qE '\b(k3d|kind)[[:space:]]+(cluster|create|delete)\b'; then
    return 1
  fi

  # mkdir is OK (idempotent directory creation, common in preprocessing)
  # touch is OK (idempotent file creation)
  # chmod/chown are borderline but not destructive

  return 0
}

# P-SLOW: Long-running commands check
# Preprocessing blocks skill loading — keep commands fast.
check_slow() {
  local cmd="$1"

  # Build/test commands (can take minutes)
  if echo "$cmd" | grep -qE '\b(npm|yarn|pnpm)[[:space:]]+(test|run[[:space:]]+build|run[[:space:]]+test|run[[:space:]]+lint)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bcargo[[:space:]]+(build|test|check|clippy)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bgo[[:space:]]+(build|test|vet)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\b(pytest|python[[:space:]]+-m[[:space:]]+pytest|mvn|gradle|make[[:space:]]+test)\b'; then
    return 1
  fi

  # Docker build/pull (network + build time)
  if echo "$cmd" | grep -qE '\bdocker[[:space:]]+(build|pull)\b'; then
    return 1
  fi

  # Git network operations
  if echo "$cmd" | grep -qE '\bgit[[:space:]]+(fetch|pull|clone|push)\b'; then
    return 1
  fi

  # Package installs (network + install time)
  if echo "$cmd" | grep -qE '\b(npm|yarn|pnpm)[[:space:]]+install\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\b(pip|pip3)[[:space:]]+install\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bapt-get[[:space:]]+(install|update|upgrade)\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bbrew[[:space:]]+(install|update|upgrade)\b'; then
    return 1
  fi

  return 0
}

# P-DUP: Redundant CLAUDE_SKILL_DIR wrapping check
# ${CLAUDE_SKILL_DIR} is already a load-time string substitution.
check_dup() {
  local cmd="$1"

  if echo "$cmd" | grep -qE 'echo[[:space:]]+"?\$\{?CLAUDE_SKILL_DIR\}?'; then
    return 1
  fi

  return 0
}

# P-HANG: Interactive/hanging command check
# Preprocessing is non-interactive — commands must not wait for input.
check_hang() {
  local cmd="$1"
  local pcmd
  pcmd=$(primary_cmd "$cmd")

  # Interactive editors
  case "$pcmd" in
    vi|vim|nvim|nano|emacs|less|more|pico)
      return 1
      ;;
  esac

  # ssh without batch mode
  if echo "$cmd" | grep -qE '\bssh\b' && ! echo "$cmd" | grep -qE -- '-o[[:space:]]*BatchMode|StrictHostKeyChecking'; then
    return 1
  fi

  # sudo without -n (non-interactive)
  if echo "$cmd" | grep -qE '\bsudo\b' && ! echo "$cmd" | grep -qE -- '-n\b'; then
    return 1
  fi

  # Interactive database clients without command flag
  if echo "$cmd" | grep -qE '\bmysql\b' && ! echo "$cmd" | grep -qE -- '-e\b'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '\bpsql\b' && ! echo "$cmd" | grep -qE -- '-c\b'; then
    return 1
  fi

  # shell read builtin
  if [[ "$pcmd" == "read" ]]; then
    return 1
  fi

  # ftp without script
  if [[ "$pcmd" == "ftp" ]]; then
    return 1
  fi

  return 0
}

# ========================
# SYNTAX CHECK
# ========================

# Check for malformed directives in the raw body (before code block stripping)
RAW_BODY=$(sed -n "${BODY_START},\$p" "$SKILL_MD" | sed '/^```/,/^```/d')

# Look for unclosed !` (opening !` without closing ` on the same line)
UNCLOSED=$(echo "$RAW_BODY" | grep -n '!`[^`]*$' 2>/dev/null | head -3 || true)
if [[ -n "$UNCLOSED" ]]; then
  FIRST_LINE=$(echo "$UNCLOSED" | head -1 | cut -d: -f1)
  emit "preproc-syntax" "false" "Unclosed preprocessing directive near body line ${FIRST_LINE} — missing closing backtick"
fi

# Look for empty !`` directives
EMPTY_DIR=$(echo "$RAW_BODY" | grep -c '!``' 2>/dev/null || true)
if [[ "$EMPTY_DIR" -gt 0 ]]; then
  emit "preproc-syntax" "false" "Found ${EMPTY_DIR} empty preprocessing directive(s) — !$'\x60\x60' contains no command"
fi

# ========================
# RUN CHECKS ON EACH DIRECTIVE
# ========================
ERR_FAILS=""
OUT_FAILS=""
SEC_FAILS=""
MUT_FAILS=""
SLOW_FAILS=""
DUP_FAILS=""
HANG_FAILS=""

while IFS= read -r directive; do
  [[ -z "$directive" ]] && continue
  cmd=$(strip_directive "$directive")
  [[ -z "$cmd" ]] && continue

  if ! check_err "$cmd"; then
    ERR_FAILS="${ERR_FAILS}${cmd}\n"
  fi

  if ! check_out "$cmd"; then
    OUT_FAILS="${OUT_FAILS}${cmd}\n"
  fi

  if ! check_sec "$cmd"; then
    SEC_FAILS="${SEC_FAILS}${cmd}\n"
  fi

  if ! check_mut "$cmd"; then
    MUT_FAILS="${MUT_FAILS}${cmd}\n"
  fi

  if ! check_slow "$cmd"; then
    SLOW_FAILS="${SLOW_FAILS}${cmd}\n"
  fi

  if ! check_dup "$cmd"; then
    DUP_FAILS="${DUP_FAILS}${cmd}\n"
  fi

  if ! check_hang "$cmd"; then
    HANG_FAILS="${HANG_FAILS}${cmd}\n"
  fi

done <<< "$DIRECTIVES"

# ========================
# EMIT RESULTS
# ========================

# P-ERR
ERR_COUNT=$(echo -e "$ERR_FAILS" | grep -c '[^ ]' || true)
if [[ "$ERR_COUNT" -gt 0 ]]; then
  FIRST_ERR=$(echo -e "$ERR_FAILS" | head -1)
  emit "preproc-err-handling" "false" "${ERR_COUNT} directive(s) lack error handling (2>/dev/null, || echo fallback) — first: ${FIRST_ERR}"
else
  emit "preproc-err-handling" "true" "All preprocessing directives have error handling or use safe commands"
fi

# P-OUT
OUT_COUNT=$(echo -e "$OUT_FAILS" | grep -c '[^ ]' || true)
if [[ "$OUT_COUNT" -gt 0 ]]; then
  FIRST_OUT=$(echo -e "$OUT_FAILS" | head -1)
  emit "preproc-output-limit" "false" "${OUT_COUNT} directive(s) could produce large output without limiting (| head, | tail) — first: ${FIRST_OUT}"
else
  emit "preproc-output-limit" "true" "All preprocessing directives produce bounded output or use limiting"
fi

# P-SEC
SEC_COUNT=$(echo -e "$SEC_FAILS" | grep -c '[^ ]' || true)
if [[ "$SEC_COUNT" -gt 0 ]]; then
  FIRST_SEC=$(echo -e "$SEC_FAILS" | head -1)
  emit "preproc-secret-leak" "false" "${SEC_COUNT} directive(s) may leak secrets via env var expansion — first: ${FIRST_SEC}"
else
  emit "preproc-secret-leak" "true" "No secret-leaking patterns detected in preprocessing directives"
fi

# P-MUT
MUT_COUNT=$(echo -e "$MUT_FAILS" | grep -c '[^ ]' || true)
if [[ "$MUT_COUNT" -gt 0 ]]; then
  FIRST_MUT=$(echo -e "$MUT_FAILS" | head -1)
  emit "preproc-mutation" "false" "${MUT_COUNT} directive(s) contain state-changing commands that run at load time — first: ${FIRST_MUT}"
else
  emit "preproc-mutation" "true" "No state-changing commands in preprocessing directives"
fi

# P-SLOW
SLOW_COUNT=$(echo -e "$SLOW_FAILS" | grep -c '[^ ]' || true)
if [[ "$SLOW_COUNT" -gt 0 ]]; then
  FIRST_SLOW=$(echo -e "$SLOW_FAILS" | head -1)
  emit "preproc-slow-cmd" "false" "${SLOW_COUNT} directive(s) contain slow commands that block skill loading — first: ${FIRST_SLOW}"
else
  emit "preproc-slow-cmd" "true" "No slow commands detected in preprocessing directives"
fi

# P-DUP
DUP_COUNT=$(echo -e "$DUP_FAILS" | grep -c '[^ ]' || true)
if [[ "$DUP_COUNT" -gt 0 ]]; then
  emit "preproc-redundant-skilldir" "false" "${DUP_COUNT} directive(s) wrap CLAUDE_SKILL_DIR in echo — redundant, already a load-time substitution"
else
  emit "preproc-redundant-skilldir" "true" "No redundant CLAUDE_SKILL_DIR wrapping in preprocessing directives"
fi

# P-HANG
HANG_COUNT=$(echo -e "$HANG_FAILS" | grep -c '[^ ]' || true)
if [[ "$HANG_COUNT" -gt 0 ]]; then
  FIRST_HANG=$(echo -e "$HANG_FAILS" | head -1)
  emit "preproc-interactive" "false" "${HANG_COUNT} directive(s) may hang waiting for input — first: ${FIRST_HANG}"
else
  emit "preproc-interactive" "true" "No interactive/hanging commands in preprocessing directives"
fi

# ========================
# SUMMARY
# ========================
echo "{\"summary\": true, \"total\": ${TOTAL}, \"passed\": ${PASSED}, \"failed\": ${FAILED}, \"directives\": ${DIRECTIVE_COUNT}}"

[[ "$FAILED" -eq 0 ]]
