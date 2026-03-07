#!/usr/bin/env bash
# check-content.sh - Shell compatibility shim for Python content checks.
#
# - Source mode: exposes check_no_secrets/check_no_useless_echo/check_no_grading_style
#   for validate.sh via delegated NDJSON re-emission.
# - Standalone mode: forwards all args to check-content.py.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_CHECKER="${SCRIPT_DIR}/check-content.py"

_reemit_delegate_output() {
  local output="$1"
  while IFS= read -r line; do
    [[ "$line" == *'"summary"'* ]] && continue
    local chk pss dtl
    chk=$(echo "$line" | sed -n 's/.*"check": "\([^"]*\)".*/\1/p')
    pss=$(echo "$line" | sed -nE 's/.*"pass": (true|false).*/\1/p')
    dtl=$(echo "$line" | sed -n 's/.*"detail": "\(.*\)".*$/\1/p')
    [[ -z "$chk" ]] && continue
    emit "$chk" "$pss" "$dtl"
  done <<< "$output"
}

_run_content_check() {
  local check_name="$1"
  local skill_dir="${SKILL_DIR:-}"
  [[ -x "$PY_CHECKER" ]] || return 0
  [[ -n "$skill_dir" ]] || return 0

  local output
  output=$(python3 "$PY_CHECKER" "$skill_dir" --check "$check_name" 2>/dev/null || true)
  [[ -n "$output" ]] || return 0
  _reemit_delegate_output "$output"
}

check_no_secrets() {
  _run_content_check "no-secrets"
}

check_no_useless_echo() {
  _run_content_check "no-useless-echo"
}

check_no_grading_style() {
  _run_content_check "no-grading-style"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  exec python3 "$PY_CHECKER" "$@"
fi
