#!/usr/bin/env bash
# validate-frontmatter.sh — Validate SKILL.md frontmatter fields against the skill spec.
#
# Usage:
#   ./validate-frontmatter.sh <skill-directory>
#
# Arguments:
#   skill-directory — Path to a skill directory containing SKILL.md
#
# Output: One JSON object per line with {check, pass, detail}.
#
# Dependencies: bash 4+, grep, sed
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

# --- Extract frontmatter (between first and second ---) ---
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$SKILL_MD" | sed '1d;$d')

# Helper: get a frontmatter field value
get_field() {
  echo "$FRONTMATTER" | grep -E "^${1}:" | head -1 | sed "s/^${1}:[[:space:]]*//"
}

# --- Check: name field present and valid format ---
NAME=$(get_field "name")
DIR_NAME=$(basename "$SKILL_DIR")

if [[ -z "$NAME" ]]; then
  echo "{\"check\": \"name-present\", \"pass\": false, \"detail\": \"Field 'name' is missing from frontmatter\"}"
else
  echo "{\"check\": \"name-present\", \"pass\": true, \"detail\": \"Field 'name' is present\"}"

  # Validate format: lowercase letters, numbers, hyphens; 1-64 chars; no consecutive hyphens; no leading/trailing hyphen
  if [[ ${#NAME} -gt 64 ]]; then
    echo "{\"check\": \"name-format\", \"pass\": false, \"detail\": \"Name '${NAME}' exceeds 64 characters (${#NAME})\"}"
  elif [[ ! "$NAME" =~ ^[a-z0-9-]+$ ]]; then
    echo "{\"check\": \"name-format\", \"pass\": false, \"detail\": \"Name '${NAME}' contains invalid characters (only lowercase letters, numbers, hyphens allowed)\"}"
  elif [[ "$NAME" =~ ^- ]] || [[ "$NAME" =~ -$ ]]; then
    echo "{\"check\": \"name-format\", \"pass\": false, \"detail\": \"Name '${NAME}' must not start or end with a hyphen\"}"
  elif [[ "$NAME" =~ -- ]]; then
    echo "{\"check\": \"name-format\", \"pass\": false, \"detail\": \"Name '${NAME}' contains consecutive hyphens\"}"
  else
    echo "{\"check\": \"name-format\", \"pass\": true, \"detail\": \"Name '${NAME}' matches pattern [a-z0-9-]{1,64}\"}"
  fi

  # Check name matches directory
  if [[ "$NAME" == "$DIR_NAME" ]]; then
    echo "{\"check\": \"name-matches-dir\", \"pass\": true, \"detail\": \"Name '${NAME}' matches directory '${DIR_NAME}'\"}"
  else
    echo "{\"check\": \"name-matches-dir\", \"pass\": false, \"detail\": \"Name '${NAME}' does not match directory '${DIR_NAME}'\"}"
  fi
fi

# --- Check: description field ---
DESCRIPTION=$(get_field "description")

if [[ -z "$DESCRIPTION" ]]; then
  echo "{\"check\": \"description-present\", \"pass\": false, \"detail\": \"Field 'description' is missing from frontmatter\"}"
else
  echo "{\"check\": \"description-present\", \"pass\": true, \"detail\": \"Field 'description' is present\"}"

  # Check for trigger phrases (case-insensitive)
  DESC_LOWER=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')
  if echo "$DESC_LOWER" | grep -qE '\b(when|use|for)\b'; then
    echo "{\"check\": \"description-trigger-phrases\", \"pass\": true, \"detail\": \"Description includes trigger phrase (when/use/for)\"}"
  else
    echo "{\"check\": \"description-trigger-phrases\", \"pass\": false, \"detail\": \"Description should include a trigger phrase (when/use/for) for discoverability\"}"
  fi

  # Check third-person form (should not start with "I can" or "You can")
  if echo "$DESCRIPTION" | grep -qiE '^\s*"?(I can|You can)'; then
    echo "{\"check\": \"description-third-person\", \"pass\": false, \"detail\": \"Description should use third-person form, not 'I can' or 'You can'\"}"
  else
    echo "{\"check\": \"description-third-person\", \"pass\": true, \"detail\": \"Description uses appropriate voice\"}"
  fi
fi

# --- Check: allowed-tools field ---
ALLOWED_TOOLS=$(get_field "allowed-tools")

if [[ -z "$ALLOWED_TOOLS" ]]; then
  echo "{\"check\": \"allowed-tools-present\", \"pass\": false, \"detail\": \"Field 'allowed-tools' is missing from frontmatter\"}"
else
  echo "{\"check\": \"allowed-tools-present\", \"pass\": true, \"detail\": \"Field 'allowed-tools' is present: ${ALLOWED_TOOLS}\"}"
fi

# --- Check: user-invocable field ---
USER_INVOCABLE=$(get_field "user-invocable")

if [[ -z "$USER_INVOCABLE" ]]; then
  echo "{\"check\": \"user-invocable-present\", \"pass\": false, \"detail\": \"Field 'user-invocable' is missing from frontmatter\"}"
else
  if [[ "$USER_INVOCABLE" == "true" ]] || [[ "$USER_INVOCABLE" == "false" ]]; then
    echo "{\"check\": \"user-invocable-present\", \"pass\": true, \"detail\": \"Field 'user-invocable' is '${USER_INVOCABLE}'\"}"
  else
    echo "{\"check\": \"user-invocable-present\", \"pass\": false, \"detail\": \"Field 'user-invocable' must be boolean (true/false), got '${USER_INVOCABLE}'\"}"
  fi
fi
