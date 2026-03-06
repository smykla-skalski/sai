#!/usr/bin/env bash
# check-file-refs.sh - File reference validation functions.
# Source from orchestrator or run standalone: ./check-file-refs.sh <skill-dir>
#
# Functions: check_file_ref_resolves, check_no_backslash_paths,
#   check_no_disallowed_files, check_refs_one_level,
#   check_skill_md_mentions_file, check_ref_link_format
#
# Requires _lib.sh globals: SKILL_BODY, SKILL_DIR, SKILL_MD, PLUGIN_ROOT

# --- file references resolve (C3) ---
check_file_ref_resolves() {
  local REFERENCED_FILES
  REFERENCED_FILES=$(echo "$SKILL_BODY" \
    | { grep -oE '(references/[a-zA-Z0-9._-]+|scripts/[a-zA-Z0-9._-]+|assets/[a-zA-Z0-9._-]+|examples/[a-zA-Z0-9._-]+)' || true; } \
    | { grep -vE '/(\.\.\.|\.\.\.|[a-z]\.md|foo\.|bar\.|baz\.|example\.)' || true; } \
    | sort -u)

  if [[ -n "$REFERENCED_FILES" ]]; then
    while IFS= read -r ref; do
      local CANONICAL_PATH="${SKILL_DIR}/${ref}"
      if [[ -e "$CANONICAL_PATH" ]]; then
        emit "file-ref-resolves" "true" "Reference '${ref}' resolves in skill directory"
      elif [[ -n "$PLUGIN_ROOT" ]] && [[ -e "${PLUGIN_ROOT}/${ref}" ]]; then
        emit "file-ref-resolves" "false" "Reference '${ref}' found at plugin root but not in skill directory — move to ${CANONICAL_PATH}"
      else
        emit "file-ref-resolves" "false" "Reference '${ref}' not found — expected at ${CANONICAL_PATH}"
      fi
    done <<< "$REFERENCED_FILES"
  else
    emit "file-ref-resolves" "true" "No file references found in SKILL.md"
  fi
}

# --- no Windows-style backslash paths (P6) ---
check_no_backslash_paths() {
  local BACKSLASH_PATHS
  BACKSLASH_PATHS=$(echo "$SKILL_BODY" \
    | { grep -oE '(references|scripts|assets|examples)\\[a-zA-Z0-9._-]+' || true; })

  if [[ -n "$BACKSLASH_PATHS" ]]; then
    local FIRST_BP
    FIRST_BP=$(echo "$BACKSLASH_PATHS" | head -1)
    emit "no-backslash-paths" "false" "Windows-style backslash path found: ${FIRST_BP} — use forward slashes"
  else
    emit "no-backslash-paths" "true" "No Windows-style backslash paths found"
  fi
}

# --- no disallowed files in skill directory ---
check_no_disallowed_files() {
  local DISALLOWED_FILES=("README.md" "CHANGELOG.md" "INSTALLATION_GUIDE.md")
  for f in ${DISALLOWED_FILES[@]+"${DISALLOWED_FILES[@]}"}; do
    if [[ -f "${SKILL_DIR}/${f}" ]]; then
      emit "no-disallowed-files" "false" "Disallowed file '${f}' found in skill directory"
    else
      emit "no-disallowed-files" "true" "'${f}' not present (correct)"
    fi
  done
}

# --- references are one level deep (no cross-references between reference files) ---
check_refs_one_level() {
  if [[ -d "${SKILL_DIR}/references" ]]; then
    for ref_file in "${SKILL_DIR}"/references/*; do
      [[ -f "$ref_file" ]] || continue
      local BASENAME STRIPPED
      BASENAME=$(basename "$ref_file")
      STRIPPED=$(sed '/^```/,/^```/d' "$ref_file" | sed 's/"[^"]*"//g; s/`[^`]*`//g')
      local BARE_PARENS
      BARE_PARENS=$(echo "$STRIPPED" | { grep -E '\(references/[a-zA-Z0-9._-]+\)' || true; } \
        | { grep -vE '\]\(references/' || true; })
      if [[ -n "$BARE_PARENS" ]]; then
        emit "refs-one-level" "false" "Reference '${BASENAME}' cross-references other reference files"
      else
        emit "refs-one-level" "true" "Reference '${BASENAME}' does not cross-reference other files"
      fi
    done
  fi
}

# --- SKILL.md mentions all bundled resource files ---
check_skill_md_mentions_file() {
  for subdir in references scripts assets examples; do
    if [[ -d "${SKILL_DIR}/${subdir}" ]]; then
      for file in "${SKILL_DIR}/${subdir}"/*; do
        [[ -f "$file" ]] || continue
        local BASENAME REL_PATH
        BASENAME=$(basename "$file")
        REL_PATH="${subdir}/${BASENAME}"
        if grep -qF "$REL_PATH" "$SKILL_MD" 2>/dev/null; then
          emit "skill-md-mentions-file" "true" "SKILL.md mentions '${REL_PATH}'"
        else
          emit "skill-md-mentions-file" "false" "SKILL.md does not mention '${REL_PATH}' — all bundled files should be referenced"
        fi
      done
    fi
  done
}

# --- reference files use markdown link format for progressive disclosure (I15) ---
check_ref_link_format() {
  local INLINE_CODE_REFS
  INLINE_CODE_REFS=$(echo "$SKILL_BODY" \
    | { grep -oE '`(references|examples)/[a-zA-Z0-9._-]+`' || true; })

  if [[ -n "$INLINE_CODE_REFS" ]]; then
    local INLINE_COUNT FIRST_INLINE
    INLINE_COUNT=$(wc -l <<< "$INLINE_CODE_REFS" | tr -d ' ')
    FIRST_INLINE=$(echo "$INLINE_CODE_REFS" | head -1)
    emit "ref-link-format" "false" "Found ${INLINE_COUNT} inline code reference(s) — use markdown links [file](path) for progressive disclosure — first: ${FIRST_INLINE}"
  else
    emit "ref-link-format" "true" "Reference file paths use markdown link format"
  fi
}

# ========================
# STANDALONE EXECUTION
# ========================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  source "$(dirname "$0")/_lib.sh" "$1"
  check_file_ref_resolves
  check_no_backslash_paths
  check_no_disallowed_files
  check_refs_one_level
  check_skill_md_mentions_file
  check_ref_link_format
  emit_summary
fi
