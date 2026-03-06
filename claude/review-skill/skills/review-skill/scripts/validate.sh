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
      emit "script-invocation-prefix" "false" "Found ${BARE_COUNT} script reference(s) without \$SKILL_DIR prefix — use \"\$SKILL_DIR/scripts/...\" — first: ${FIRST_BAD}"
    else
      emit "script-invocation-prefix" "true" "All script references use \$SKILL_DIR prefix"
    fi
  fi

  # --- no bash prefix on script invocations ---
  # Scripts must be invoked directly ("$SKILL_DIR/scripts/..."), never via
  # bash "$SKILL_DIR/scripts/...". Scripts should have the executable bit set.
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    local BASH_PREFIX_REFS
    BASH_PREFIX_REFS=$(sed -n "${BODY_START},\$p" "$SKILL_MD" \
      | awk '/^```/{f=!f;next} f && /^\s*bash\s+/' \
      || true)

    if [[ -n "$BASH_PREFIX_REFS" ]]; then
      local BASH_COUNT FIRST_BASH
      BASH_COUNT=$(echo "$BASH_PREFIX_REFS" | wc -l | tr -d ' ')
      FIRST_BASH=$(echo "$BASH_PREFIX_REFS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      emit "no-bash-prefix" "false" "Found ${BASH_COUNT} script invocation(s) using bash prefix — invoke directly via \"\$SKILL_DIR/scripts/...\" and set executable bit — first: ${FIRST_BASH}"
    else
      emit "no-bash-prefix" "true" "No bash-prefixed script invocations found"
    fi
  fi

  # --- scripts have executable bit set ---
  if [[ -d "${SKILL_DIR}/scripts" ]]; then
    for script_file in "${SKILL_DIR}/scripts"/*; do
      [[ -f "$script_file" ]] || continue
      local SCRIPT_BASENAME
      SCRIPT_BASENAME=$(basename "$script_file")
      if [[ -x "$script_file" ]]; then
        emit "script-executable" "true" "Script '${SCRIPT_BASENAME}' has executable bit set"
      else
        emit "script-executable" "false" "Script '${SCRIPT_BASENAME}' missing executable bit — run chmod +x"
      fi
    done
  fi

  # --- no secrets or credentials (C7) ---
  # Scan SKILL.md and all bundled files for common secret patterns.
  # Filter out obvious placeholders (sequential digits, hex patterns,
  # placeholder words) — real secrets have high entropy.
  local SECRET_PATTERN='AKIA[A-Z0-9]{16}|sk-[a-zA-Z0-9]{20,}|-----BEGIN[[:space:]]+(RSA |EC )?(PRIVATE )?KEY-----|Bearer[[:space:]]+[a-zA-Z0-9._-]{20,}'
  local PLACEHOLDER_PATTERN='1234|0000|xxxx|abcdef|example|test|fake|placeholder|your_|INSERT|REPLACE|changeme'
  local SECRET_HIT_FILES=""

  local ALL_SKILL_FILES="$SKILL_MD"
  for subdir in references scripts assets examples; do
    if [[ -d "${SKILL_DIR}/${subdir}" ]]; then
      for f in "${SKILL_DIR}/${subdir}"/*; do
        [[ -f "$f" ]] && ALL_SKILL_FILES="$ALL_SKILL_FILES $f"
      done
    fi
  done

  for sf in $ALL_SKILL_FILES; do
    local MATCHES
    MATCHES=$(grep -oE "$SECRET_PATTERN" "$sf" 2>/dev/null || true)
    if [[ -n "$MATCHES" ]]; then
      # Check if any match looks real (not a placeholder)
      local HAS_REAL="false"
      while IFS= read -r match; do
        if ! echo "$match" | grep -qiE "$PLACEHOLDER_PATTERN"; then
          HAS_REAL="true"
          break
        fi
      done <<< "$MATCHES"
      if [[ "$HAS_REAL" == "true" ]]; then
        SECRET_HIT_FILES="$SECRET_HIT_FILES $(basename "$sf")"
      fi
    fi
  done

  SECRET_HIT_FILES=$(echo "$SECRET_HIT_FILES" | xargs)
  if [[ -n "$SECRET_HIT_FILES" ]]; then
    emit "no-secrets" "false" "Possible secrets or credentials found in: ${SECRET_HIT_FILES}"
  else
    emit "no-secrets" "true" "No secrets or credentials detected"
  fi

  # --- no Windows-style backslash paths (P6) ---
  local BACKSLASH_PATHS
  BACKSLASH_PATHS=$(echo "$SKILL_BODY" \
    | grep -oE '(references|scripts|assets|examples)\\[a-zA-Z0-9._-]+' \
    || true)

  if [[ -n "$BACKSLASH_PATHS" ]]; then
    local FIRST_BP
    FIRST_BP=$(echo "$BACKSLASH_PATHS" | head -1)
    emit "no-backslash-paths" "false" "Windows-style backslash path found: ${FIRST_BP} — use forward slashes"
  else
    emit "no-backslash-paths" "true" "No Windows-style backslash paths found"
  fi

  # --- no useless echo in code blocks (I13) ---
  # ShellCheck SC2116: $(echo "value") is the same as "value".
  # Scan bash/sh code blocks in all .md files for this anti-pattern.
  # See: https://www.shellcheck.net/wiki/SC2116
  local USELESS_ECHO_FILES=""
  local FIRST_ECHO_LINE=""

  for md_file in $ALL_SKILL_FILES; do
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
      in_block && /\$\(echo / { print }
    ' "$md_file" || true)
    if [[ -n "$ECHO_HITS" ]]; then
      USELESS_ECHO_FILES="$USELESS_ECHO_FILES $(basename "$md_file")"
      if [[ -z "$FIRST_ECHO_LINE" ]]; then
        FIRST_ECHO_LINE=$(echo "$ECHO_HITS" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-80)
      fi
    fi
  done

  USELESS_ECHO_FILES=$(echo "$USELESS_ECHO_FILES" | xargs)
  if [[ -n "$USELESS_ECHO_FILES" ]]; then
    emit "no-useless-echo" "false" "Useless echo (SC2116) in code blocks: ${USELESS_ECHO_FILES} — first: ${FIRST_ECHO_LINE}"
  else
    emit "no-useless-echo" "true" "No useless echo patterns in code blocks"
  fi

  # --- no duplicated code blocks between SKILL.md and references (I14) ---
  # "The context window is a public good" — Anthropic Best Practices.
  # Code blocks (3+ lines) in SKILL.md that appear verbatim in references waste context.
  # See: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  if [[ -d "${SKILL_DIR}/references" ]]; then
    local DUP_COUNT=0
    local DUP_REFS=""

    # Awk extracts fenced code blocks (3+ lines) into numbered temp files.
    # Uses temp directory + awk file output to avoid NUL-pipe issues on macOS bash.
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
    SKILL_BLOCK_DIR=$(mktemp -d)
    SKILL_HASH_FILE=$(mktemp)
    sed -n "${BODY_START},\$p" "$SKILL_MD" \
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
        REF_BLOCK_DIR=$(mktemp -d)
        REF_HASH_FILE=$(mktemp)
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
          DUP_REFS="$DUP_REFS ${BASENAME}"
        fi
        rm -f "$REF_HASH_FILE"
      done
    fi

    rm -f "$SKILL_HASH_FILE"
    DUP_REFS=$(echo "$DUP_REFS" | xargs)
    if [[ -n "$DUP_REFS" ]]; then
      emit "no-duplicate-codeblocks" "false" "Found ${DUP_COUNT} code block(s) (3+ lines) duplicated between SKILL.md and references: ${DUP_REFS}"
    else
      emit "no-duplicate-codeblocks" "true" "No duplicated code blocks between SKILL.md and references"
    fi
  fi

  # --- consistent phase numbering between SKILL.md and references (I15) ---
  # "Use consistent terminology" — Anthropic Best Practices.
  # If SKILL.md and a reference both define numbered phases via headers,
  # the phase numbers must match.
  # See: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  if [[ -d "${SKILL_DIR}/references" ]]; then
    local SKILL_PHASES
    SKILL_PHASES=$(sed -n "${BODY_START},\$p" "$SKILL_MD" \
      | sed '/^```/,/^```/d' \
      | grep -iE '^#{1,4}[[:space:]]+Phase[[:space:]]+[0-9]+' \
      | grep -oE '[0-9]+' \
      | sort -n -u || true)
    local SKILL_PHASE_COUNT
    SKILL_PHASE_COUNT=$(echo "$SKILL_PHASES" | { grep -c '[0-9]' || true; })

    if [[ "$SKILL_PHASE_COUNT" -ge 2 ]]; then
      for ref_file in "${SKILL_DIR}"/references/*.md; do
        [[ -f "$ref_file" ]] || continue
        local BASENAME
        BASENAME=$(basename "$ref_file")
        local REF_PHASES
        REF_PHASES=$(sed '/^```/,/^```/d' "$ref_file" \
          | grep -iE '^#{1,4}[[:space:]]+Phase[[:space:]]+[0-9]+' \
          | grep -oE '[0-9]+' \
          | sort -n -u || true)
        local REF_PHASE_COUNT
        REF_PHASE_COUNT=$(echo "$REF_PHASES" | { grep -c '[0-9]' || true; })

        if [[ "$REF_PHASE_COUNT" -ge 2 ]]; then
          if [[ "$SKILL_PHASES" != "$REF_PHASES" ]]; then
            local SKILL_LIST REF_LIST
            SKILL_LIST=$(echo "$SKILL_PHASES" | tr '\n' ',' | sed 's/,$//')
            REF_LIST=$(echo "$REF_PHASES" | tr '\n' ',' | sed 's/,$//')
            emit "consistent-phase-numbering" "false" "Phase numbering mismatch: SKILL.md has [${SKILL_LIST}] but ${BASENAME} has [${REF_LIST}]"
          else
            emit "consistent-phase-numbering" "true" "Phase numbers in '${BASENAME}' match SKILL.md"
          fi
        fi
      done
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
