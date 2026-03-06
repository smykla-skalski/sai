#!/usr/bin/env bash
# stage-hunk.sh — Non-interactive hunk staging for selective git add without TTY.
#
# Usage:
#   ./stage-hunk.sh --check-deps
#   ./stage-hunk.sh --list [--fallback]
#   ./stage-hunk.sh --hunk H1,H2 [--dry-run] [--fallback]
#   ./stage-hunk.sh --pattern REGEX [--dry-run]
#   ./stage-hunk.sh --file PATH [--dry-run] [--fallback]
#   ./stage-hunk.sh --range FILE:START-END [--dry-run]
#   ./stage-hunk.sh --verify
#
# Modes:
#   --check-deps       Check required dependencies, output JSON status
#   --list             List all unstaged hunks with IDs and previews
#   --hunk H1,H2,...   Stage specific hunks by global sequential ID
#   --pattern REGEX    Stage hunks matching regex (requires patchutils)
#   --file PATH        Stage all hunks for file(s) (comma-separated)
#   --range FILE:S-E   Stage hunks overlapping line range (requires patchutils)
#   --verify           Show staged vs unstaged summary
#
# Flags:
#   --dry-run          Preview staging without applying
#   --fallback         Force fallback mode (no patchutils)
#
# Output: NDJSON (one JSON object per line), final line always a summary.
#
# Exit codes:
#   0  Success
#   1  Runtime error
#   2  Usage error
#   3  Missing dependency (patchutils) — only from --check-deps
#
# Dependencies: git, python3 (for JSON encoding)
# Optional:     patchutils (lsdiff, filterdiff, grepdiff)
set -euo pipefail

# ========================
# HELPERS
# ========================

# Print JSON error to stderr and exit.
die() {
  local msg="$1" code="${2:-1}"
  echo "{\"error\":$(json_str "$msg")}" >&2
  exit "$code"
}

# Emit one NDJSON line to stdout.
emit() {
  echo "$1"
}

# Escape a string for safe embedding inside a JSON string value.
# Handles \, ", and control characters (\n, \t, \r).
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\t'/\\t}"
  s="${s//$'\r'/\\r}"
  printf '%s' "$s"
}

# Safely encode a string as a JSON string value (with quotes).
# Uses python3 for reliable unicode/special-char handling.
json_str() {
  python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$1"
}

# Safely encode a string as a raw JSON string value (without outer quotes).
json_str_raw() {
  python3 -c "import json,sys; print(json.dumps(sys.argv[1])[1:-1])" "$1"
}

# Parse a hunk header line, output: old_start old_count new_start new_count
# Input: @@ -45,8 +45,12 @@ optional context
parse_hunk_header() {
  echo "$1" | sed -n 's/^@@ -\([0-9]*\),*\([0-9]*\) +\([0-9]*\),*\([0-9]*\) @@.*/\1 \2 \3 \4/p'
}

# ========================
# ARGUMENT PARSING
# ========================
MODE=""
HUNK_IDS=""
PATTERN=""
FILE_PATHS=""
RANGE_SPEC=""
DRY_RUN=false
FALLBACK=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-deps) MODE="check-deps"; shift ;;
    --list)       MODE="list"; shift ;;
    --hunk)       MODE="hunk"; HUNK_IDS="${2:-}"; shift 2 || die "missing hunk IDs" 2 ;;
    --pattern)    MODE="pattern"; PATTERN="${2:-}"; shift 2 || die "missing pattern" 2 ;;
    --file)       MODE="file"; FILE_PATHS="${2:-}"; shift 2 || die "missing file path" 2 ;;
    --range)      MODE="range"; RANGE_SPEC="${2:-}"; shift 2 || die "missing range spec" 2 ;;
    --verify)     MODE="verify"; shift ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --fallback)   FALLBACK=true; shift ;;
    *)            die "unknown flag: $1" 2 ;;
  esac
done

[[ -z "$MODE" ]] && die "no mode specified (use --check-deps, --list, --hunk, --pattern, --file, --range, or --verify)" 2

# ========================
# DEPENDENCY CHECK
# ========================
HAS_PATCHUTILS=false
if command -v lsdiff &>/dev/null && command -v filterdiff &>/dev/null; then
  HAS_PATCHUTILS=true
fi

if [[ "$MODE" == "check-deps" ]]; then
  # git
  if command -v git &>/dev/null; then
    emit '{"dep":"git","found":true}'
  else
    emit '{"dep":"git","found":false,"install":"Install git from https://git-scm.com"}'
  fi
  # python3
  if command -v python3 &>/dev/null; then
    emit '{"dep":"python3","found":true}'
  else
    emit '{"dep":"python3","found":false,"install":"Install Python 3"}'
  fi
  # patchutils
  if [[ "$HAS_PATCHUTILS" == "true" ]]; then
    emit '{"dep":"patchutils","found":true}'
  else
    emit '{"dep":"patchutils","found":false,"install":"brew install patchutils (macOS) or apt install patchutils (Debian/Ubuntu)"}'
    exit 3
  fi
  exit 0
fi

# Determine effective mode
if [[ "$FALLBACK" == "true" ]] || [[ "$HAS_PATCHUTILS" == "false" ]]; then
  FALLBACK=true
fi

# Modes that require patchutils
if [[ "$FALLBACK" == "true" ]]; then
  if [[ "$MODE" == "pattern" ]]; then
    die "--pattern mode requires patchutils (grepdiff). Install with: brew install patchutils" 1
  fi
  if [[ "$MODE" == "range" ]]; then
    die "--range mode requires patchutils (filterdiff). Install with: brew install patchutils" 1
  fi
fi

# Pre-flight: must be in a git repo
git rev-parse --git-dir &>/dev/null || die "not inside a git repository" 1

# ========================
# DIFF CAPTURE
# ========================

# Get the full unstaged diff. Handle intent-to-add for new untracked files.
DIFF=$(git diff)
if [[ -z "$DIFF" ]]; then
  emit '{"error":"no_unstaged_changes","detail":"git diff is empty"}'
  exit 0
fi

# ========================
# HUNK INDEX BUILDER
# ========================
# Builds a global hunk index: H1, H2, ... assigned by alphabetical file order,
# then by position within the file.
#
# Each entry stored as: HUNK_ID<US>FILE<US>HUNK_NUM_IN_FILE<US>OLD_START<US>OLD_COUNT<US>NEW_START<US>NEW_COUNT<US>ADDED<US>REMOVED<US>PREVIEW
# where <US> is ASCII unit separator (\x1f) to avoid collision with diff content (pipes, colons, etc.)
#
# Works in both patchutils and fallback modes.

FS=$'\x1f'  # field separator for hunk index

build_hunk_index() {
  local diff_text="$1"
  local hunk_id=0
  local current_file=""
  local hunk_num=0
  local in_hunk=false
  local old_start=0 old_count=0 new_start=0 new_count=0
  local added=0 removed=0
  local preview=""
  local first_add_seen=false

  # We need to process files in alphabetical order for stable IDs.
  # First, extract file list and sort, then process each file's diff.
  if [[ "$HAS_PATCHUTILS" == "true" ]] && [[ "$FALLBACK" == "false" ]]; then
    local files
    files=$(echo "$diff_text" | lsdiff --strip=1 | sort)
  else
    local files
    files=$(echo "$diff_text" | { grep -E '^diff --git' || true; } | sed 's|^diff --git a/\(.*\) b/.*|\1|' | sort)
  fi

  [[ -z "$files" ]] && return

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    # Check for binary file
    if { echo "$diff_text" | grep "^Binary files" || true; } | grep -qF "$file"; then
      continue
    fi

    # Extract this file's diff section
    local file_diff
    if [[ "$HAS_PATCHUTILS" == "true" ]] && [[ "$FALLBACK" == "false" ]]; then
      file_diff=$(echo "$diff_text" | filterdiff -i "a/${file}" 2>/dev/null) || continue
    else
      # Fallback: awk-based extraction
      file_diff=$(echo "$diff_text" | awk -v target="$file" '
        /^diff --git/ {
          if (found) exit
          # Extract file path from "diff --git a/PATH b/PATH"
          f = $0
          sub(/^diff --git a\//, "", f)
          sub(/ b\/.*/, "", f)
          if (f == target) { found=1 }
        }
        found { print }
      ')
      [[ -z "$file_diff" ]] && continue
    fi

    hunk_num=0

    while IFS= read -r line; do
      if [[ "$line" =~ ^@@\ - ]]; then
        # Emit previous hunk if any
        if [[ "$in_hunk" == "true" ]]; then
          hunk_id=$((hunk_id + 1))
          local preview_escaped
          preview_escaped=$(json_str_raw "$preview")
          echo "H${hunk_id}${FS}${current_file}${FS}${hunk_num}${FS}${old_start}${FS}${old_count}${FS}${new_start}${FS}${new_count}${FS}${added}${FS}${removed}${FS}${preview_escaped}"
        fi

        in_hunk=true
        hunk_num=$((hunk_num + 1))
        current_file="$file"
        added=0
        removed=0
        preview=""
        first_add_seen=false

        local parsed
        parsed=$(parse_hunk_header "$line")
        old_start=$(echo "$parsed" | awk '{print $1}')
        old_count=$(echo "$parsed" | awk '{v=$2; print (v=="" ? 1 : v)}')
        new_start=$(echo "$parsed" | awk '{print $3}')
        new_count=$(echo "$parsed" | awk '{v=$4; print (v=="" ? 1 : v)}')
      elif [[ "$in_hunk" == "true" ]]; then
        if [[ "$line" =~ ^\+ ]] && [[ ! "$line" =~ ^\+\+\+ ]]; then
          added=$((added + 1))
          if [[ "$first_add_seen" == "false" ]]; then
            preview="${line:0:120}"
            first_add_seen=true
          fi
        elif [[ "$line" =~ ^- ]] && [[ ! "$line" =~ ^--- ]]; then
          removed=$((removed + 1))
          if [[ "$first_add_seen" == "false" ]] && [[ -z "$preview" ]]; then
            preview="${line:0:120}"
          fi
        fi
      fi
    done <<< "$file_diff"

    # Emit last hunk for this file
    if [[ "$in_hunk" == "true" ]]; then
      hunk_id=$((hunk_id + 1))
      local preview_escaped
      preview_escaped=$(json_str_raw "$preview")
      echo "H${hunk_id}${FS}${current_file}${FS}${hunk_num}${FS}${old_start}${FS}${old_count}${FS}${new_start}${FS}${new_count}${FS}${added}${FS}${removed}${FS}${preview_escaped}"
      in_hunk=false
    fi
  done <<< "$files"
}

# Build the index once
HUNK_INDEX=$(build_hunk_index "$DIFF")

if [[ -z "$HUNK_INDEX" ]]; then
  emit '{"error":"no_hunks","detail":"diff exists but no parseable hunks found (binary files only?)"}'
  exit 0
fi

TOTAL_HUNKS=$(wc -l <<< "$HUNK_INDEX" | tr -d ' ')

# ========================
# LIST MODE
# ========================
if [[ "$MODE" == "list" ]]; then
  while IFS="$FS" read -r id file hunk_num os oc ns nc added removed preview; do
    local_file=$(json_str "$file")
    local_preview=$(json_str "$preview")
    emit "{\"id\":\"${id}\",\"file\":${local_file},\"hunk_num\":${hunk_num},\"old_start\":${os},\"old_count\":${oc},\"new_start\":${ns},\"new_count\":${nc},\"added\":${added},\"removed\":${removed},\"preview\":${local_preview}}"
  done <<< "$HUNK_INDEX"
  fb="false"
  [[ "$FALLBACK" == "true" ]] && fb="true"
  emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"mode\":\"list\",\"fallback\":${fb}}"
  exit 0
fi

# ========================
# VERIFY MODE
# ========================
if [[ "$MODE" == "verify" ]]; then
  staged_files=$(git diff --cached --name-only | sort)
  unstaged_files=$(git diff --name-only | sort)
  staged_count=$(echo "$staged_files" | grep -c . || true)
  unstaged_count=$(echo "$unstaged_files" | grep -c . || true)

  # Staged hunks count
  staged_diff=$(git diff --cached)
  if [[ -n "$staged_diff" ]]; then
    staged_hunks=$(echo "$staged_diff" | grep -c '^@@ ' || true)
  else
    staged_hunks=0
  fi

  # Unstaged hunks count
  unstaged_hunks=$(echo "$DIFF" | grep -c '^@@ ' || true)

  emit "{\"staged_files\":${staged_count},\"unstaged_files\":${unstaged_count},\"staged_hunks\":${staged_hunks},\"unstaged_hunks\":${unstaged_hunks}}"

  # Per-file detail
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    s_hunks=0
    u_hunks=0
    if [[ -n "$staged_diff" ]]; then
      if [[ "$FALLBACK" == "false" ]]; then
        local filtered
        filtered=$(echo "$staged_diff" | filterdiff -i "a/${f}" 2>/dev/null) || true
        s_hunks=$(echo "$filtered" | grep -c '^@@ ' || true)
      else
        s_hunks=$(echo "$staged_diff" | awk -v target="$f" '/^diff --git/{found=0; f=$0; sub(/^diff --git a\//,"",f); sub(/ b\/.*/,"",f); if(f==target)found=1} found && /^@@ /{c++} END{print c+0}')
      fi
    fi
    u_hunks=$(echo "$DIFF" | awk -v target="$f" '/^diff --git/{found=0; f=$0; sub(/^diff --git a\//,"",f); sub(/ b\/.*/,"",f); if(f==target)found=1} found && /^@@ /{c++} END{print c+0}')
    local_f=$(json_str "$f")
    emit "{\"file\":${local_f},\"staged_hunks\":${s_hunks},\"unstaged_hunks\":${u_hunks}}"
  done < <(echo -e "${staged_files}\n${unstaged_files}" | sort -u)

  emit "{\"summary\":true,\"mode\":\"verify\"}"
  exit 0
fi

# ========================
# STAGING HELPERS
# ========================

# Extract a single hunk patch suitable for git apply.
# Args: file, hunk_num_in_file
# Outputs: a valid unified diff patch for that single hunk.
extract_hunk_patch() {
  local file="$1" hunk_num="$2"

  if [[ "$FALLBACK" == "false" ]]; then
    echo "$DIFF" | filterdiff -i "a/${file}" --hunks="${hunk_num}" 2>/dev/null
  else
    # Fallback: awk-based extraction
    echo "$DIFF" | awk -v target="$file" -v target_hunk="$hunk_num" '
      /^diff --git/ {
        f = $0
        sub(/^diff --git a\//, "", f)
        sub(/ b\/.*/, "", f)
        if (f == target) {
          found = 1
          hunk_count = 0
          header = $0
          got_minus = 0
          got_plus = 0
        } else {
          found = 0
        }
      }
      # Only match --- as file header before we have seen +++ and @@
      found && !got_minus && /^---/ {
        minus_line = $0
        got_minus = 1
        next
      }
      found && got_minus && !got_plus && /^\+\+\+/ {
        plus_line = $0
        got_plus = 1
        next
      }
      found && got_plus && /^@@ / {
        hunk_count++
        if (hunk_count == target_hunk) {
          in_target = 1
          print header
          print minus_line
          print plus_line
          print $0
          next
        } else {
          in_target = 0
        }
      }
      found && in_target && !/^diff --git/ && !/^@@ / {
        print
      }
      found && in_target && /^diff --git/ {
        exit
      }
    '
  fi
}

# Apply a patch to the index. Returns 0 on success, 1 on failure.
# Sets APPLY_STDERR with captured error output for diagnostics.
APPLY_STDERR=""
apply_patch() {
  local patch="$1"
  [[ -z "$patch" ]] && return 1
  APPLY_STDERR=$(echo "$patch" | git apply --cached 2>&1) && return 0
  # Check for index lock
  if echo "$APPLY_STDERR" | grep -qF "index.lock"; then
    emit "{\"error\":\"index_locked\",\"detail\":$(json_str "$APPLY_STDERR")}"
    return 1
  fi
  return 1
}

# Stage a list of hunk entries (from HUNK_INDEX format).
# Outputs NDJSON per hunk result.
# Returns number of failures via global STAGE_FAILED.
STAGE_FAILED=0
STAGE_OK=0

stage_hunks() {
  local entries="$1"
  STAGE_FAILED=0
  STAGE_OK=0

  # Group by file for bulk application
  local files
  files=$(echo "$entries" | awk -F"$FS" '{print $2}' | sort -u)

  while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    # Get all hunk entries for this file
    local file_entries
    file_entries=$(echo "$entries" | awk -F"$FS" -v f="$file" '$2 == f')

    # Collect per-file hunk numbers
    local hunk_nums
    hunk_nums=$(echo "$file_entries" | awk -F"$FS" '{print $3}' | tr '\n' ',' | sed 's/,$//')

    if [[ "$DRY_RUN" == "true" ]]; then
      # Dry run - just report what would happen
      while IFS="$FS" read -r id f hn os oc ns nc added removed preview; do
        local_f=$(json_str "$f")
        emit "{\"id\":\"${id}\",\"file\":${local_f},\"action\":\"would_stage\",\"status\":\"dry_run\"}"
        STAGE_OK=$((STAGE_OK + 1))
      done <<< "$file_entries"
      continue
    fi

    # Try bulk apply via filterdiff (patchutils only - produces valid multi-hunk patch).
    # Fallback mode skips bulk and goes straight to per-hunk since concatenating
    # individual patches produces duplicate diff headers that git apply rejects.
    local bulk_ok=false
    if [[ "$FALLBACK" == "false" ]]; then
      local bulk_patch
      bulk_patch=$(echo "$DIFF" | filterdiff -i "a/${file}" --hunks="${hunk_nums}" 2>/dev/null) || true
      if [[ -n "$bulk_patch" ]] && apply_patch "$bulk_patch"; then
        bulk_ok=true
        while IFS="$FS" read -r id f hn os oc ns nc added removed preview; do
          local_f=$(json_str "$f")
          emit "{\"id\":\"${id}\",\"file\":${local_f},\"action\":\"staged\",\"status\":\"ok\"}"
          STAGE_OK=$((STAGE_OK + 1))
        done <<< "$file_entries"
      fi
    fi

    # Per-hunk fallback (always used in fallback mode, or when bulk apply fails)
    if [[ "$bulk_ok" == "false" ]]; then
      while IFS="$FS" read -r id f hn os oc ns nc added removed preview; do
        APPLY_STDERR=""
        local_f=$(json_str "$f")
        local hunk_patch
        hunk_patch=$(extract_hunk_patch "$f" "$hn")
        if [[ -n "$hunk_patch" ]] && apply_patch "$hunk_patch"; then
          emit "{\"id\":\"${id}\",\"file\":${local_f},\"action\":\"staged\",\"status\":\"ok\"}"
          STAGE_OK=$((STAGE_OK + 1))
        else
          local err_detail
          err_detail=$(json_str "$APPLY_STDERR")
          emit "{\"id\":\"${id}\",\"file\":${local_f},\"action\":\"stage_failed\",\"status\":\"error\",\"detail\":${err_detail}}"
          STAGE_FAILED=$((STAGE_FAILED + 1))
        fi
      done <<< "$file_entries"
    fi
  done <<< "$files"
}

# Map a local hunk index (from a filtered diff) back to global HUNK_INDEX entries
# by matching file + per-file hunk number. Outputs matching global entries.
map_to_global_ids() {
  local matched_index="$1"
  local result=""
  while IFS="$FS" read -r mid mfile mhn mos moc mns mnc madded mremoved mpreview; do
    local global_entry
    # Match by file + old_start (not hunk_num) — grepdiff returns a subset so
    # per-file hunk numbers in the matched diff don't match the original diff.
    global_entry=$(echo "$HUNK_INDEX" | awk -F"$FS" -v f="$mfile" -v os="$mos" '$2==f && $4==os' || true)
    if [[ -n "$global_entry" ]]; then
      if [[ -z "$result" ]]; then
        result="$global_entry"
      else
        result="${result}
${global_entry}"
      fi
    fi
  done <<< "$matched_index"
  echo "$result"
}

# ========================
# HUNK MODE
# ========================
if [[ "$MODE" == "hunk" ]]; then
  [[ -z "$HUNK_IDS" ]] && die "no hunk IDs specified" 2

  # Parse comma-separated IDs
  IFS=',' read -ra requested_ids <<< "$HUNK_IDS"

  # Validate IDs and collect matching entries
  matched_entries=""
  bad_ids=""
  for rid in ${requested_ids[@]+"${requested_ids[@]}"}; do
    rid=$(echo "$rid" | tr -d ' ')
    entry=$(echo "$HUNK_INDEX" | grep -F "${rid}${FS}" || true)
    if [[ -z "$entry" ]]; then
      bad_ids="${bad_ids}${rid},"
    else
      if [[ -z "$matched_entries" ]]; then
        matched_entries="$entry"
      else
        matched_entries="${matched_entries}
${entry}"
      fi
    fi
  done

  # Report bad IDs
  if [[ -n "$bad_ids" ]]; then
    bad_ids="${bad_ids%,}"
    emit "{\"warning\":\"invalid_hunk_ids\",\"ids\":\"${bad_ids}\",\"valid_range\":\"H1-H${TOTAL_HUNKS}\"}"
  fi

  if [[ -z "$matched_entries" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"no valid hunk IDs\"}"
    exit 1
  fi

  stage_hunks "$matched_entries"

  fb="false"
  [[ "$FALLBACK" == "true" ]] && fb="true"
  emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":${STAGE_OK},\"failed\":${STAGE_FAILED},\"dry_run\":${DRY_RUN},\"fallback\":${fb}}"
  [[ "$STAGE_FAILED" -eq 0 ]]
  exit
fi

# ========================
# FILE MODE
# ========================
if [[ "$MODE" == "file" ]]; then
  [[ -z "$FILE_PATHS" ]] && die "no file paths specified" 2

  IFS=',' read -ra requested_files <<< "$FILE_PATHS"

  matched_entries=""
  bad_files=""
  for rf in ${requested_files[@]+"${requested_files[@]}"}; do
    # trim surrounding whitespace only (preserve internal spaces in paths)
    rf=$(echo "$rf" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    entries=$(echo "$HUNK_INDEX" | awk -F"$FS" -v f="$rf" '$2 == f' || true)
    if [[ -z "$entries" ]]; then
      bad_files="${bad_files}${rf},"
    else
      if [[ -z "$matched_entries" ]]; then
        matched_entries="$entries"
      else
        matched_entries="${matched_entries}
${entries}"
      fi
    fi
  done

  if [[ -n "$bad_files" ]]; then
    bad_files="${bad_files%,}"
    bad_files_json=$(json_str "$bad_files")
    emit "{\"warning\":\"files_not_in_diff\",\"files\":${bad_files_json}}"
  fi

  if [[ -z "$matched_entries" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"no matching files in diff\"}"
    exit 1
  fi

  stage_hunks "$matched_entries"

  fb="false"
  [[ "$FALLBACK" == "true" ]] && fb="true"
  emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":${STAGE_OK},\"failed\":${STAGE_FAILED},\"dry_run\":${DRY_RUN},\"fallback\":${fb}}"
  [[ "$STAGE_FAILED" -eq 0 ]]
  exit
fi

# ========================
# PATTERN MODE (patchutils only)
# ========================
if [[ "$MODE" == "pattern" ]]; then
  [[ -z "$PATTERN" ]] && die "no pattern specified" 2

  # Use grepdiff to find hunks matching the pattern
  matched_diff=$(echo "$DIFF" | grepdiff -E "$PATTERN" --output-matching=hunk 2>/dev/null) || true

  if [[ -z "$matched_diff" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"no hunks match pattern\"}"
    exit 0
  fi

  # Build index of matched hunks to find their global IDs
  matched_index=$(build_hunk_index "$matched_diff")

  if [[ -z "$matched_index" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"no parseable hunks match pattern\"}"
    exit 0
  fi

  # Map matched hunks back to global IDs by file+hunk_num
  final_entries=$(map_to_global_ids "$matched_index")

  if [[ -z "$final_entries" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"matched hunks could not be mapped to global IDs\"}"
    exit 0
  fi

  stage_hunks "$final_entries"

  emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":${STAGE_OK},\"failed\":${STAGE_FAILED},\"dry_run\":${DRY_RUN},\"fallback\":false}"
  [[ "$STAGE_FAILED" -eq 0 ]]
  exit
fi

# ========================
# RANGE MODE (patchutils only)
# ========================
if [[ "$MODE" == "range" ]]; then
  [[ -z "$RANGE_SPEC" ]] && die "no range specified" 2

  # Parse FILE:START-END — use parameter expansion to handle colons in filenames
  range_lines="${RANGE_SPEC##*:}"
  range_file="${RANGE_SPEC%:${range_lines}}"
  range_start=$(echo "$range_lines" | cut -d- -f1)
  range_end=$(echo "$range_lines" | cut -d- -f2)

  [[ -z "$range_file" ]] && die "invalid range spec: missing file" 2
  [[ -z "$range_start" ]] && die "invalid range spec: missing start line" 2
  [[ -z "$range_end" ]] && die "invalid range spec: missing end line" 2

  # Use filterdiff --lines to find overlapping hunks
  matched_diff=$(echo "$DIFF" | filterdiff -i "a/${range_file}" --lines="${range_start}-${range_end}" 2>/dev/null) || true

  if [[ -z "$matched_diff" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"no hunks overlap range ${range_start}-${range_end} in ${range_file}\"}"
    exit 0
  fi

  # Build index of matched hunks
  matched_index=$(build_hunk_index "$matched_diff")

  # Map back to global IDs
  final_entries=$(map_to_global_ids "$matched_index")

  if [[ -z "$final_entries" ]]; then
    emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":0,\"failed\":0,\"dry_run\":${DRY_RUN},\"error\":\"matched hunks could not be mapped to global IDs\"}"
    exit 0
  fi

  stage_hunks "$final_entries"

  emit "{\"summary\":true,\"total_hunks\":${TOTAL_HUNKS},\"staged\":${STAGE_OK},\"failed\":${STAGE_FAILED},\"dry_run\":${DRY_RUN},\"fallback\":false}"
  [[ "$STAGE_FAILED" -eq 0 ]]
  exit
fi
