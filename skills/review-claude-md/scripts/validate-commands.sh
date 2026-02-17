#!/usr/bin/env bash
# validate-commands.sh — Validate commands section in CLAUDE.md.
#
# Usage:
#   ./validate-commands.sh <repo-root>
#
# Arguments:
#   repo-root — Path to the repository root containing CLAUDE.md
#
# Output: One JSON object per line with {check, pass, detail}.
#
# Dependencies: bash 4+, grep
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

# --- Check: has-build ---
BUILD_PATTERNS="make\b|npm run build|cargo build|go build|mvn |gradle |bazel build"
BUILD_MATCH=$(grep -inE "$BUILD_PATTERNS" "$CLAUDE_MD" | head -1 || true)
if [[ -n "$BUILD_MATCH" ]]; then
  LINE_NUM=$(echo "$BUILD_MATCH" | cut -d: -f1)
  echo "{\"check\": \"has-build\", \"pass\": true, \"detail\": \"Build command found on line ${LINE_NUM}\"}"
else
  echo "{\"check\": \"has-build\", \"pass\": false, \"detail\": \"No build command found (looked for make, npm run build, cargo build, go build, mvn, gradle)\"}"
fi

# --- Check: has-test ---
TEST_PATTERNS="npm test|pytest|cargo test|go test|jest|vitest|make test|yarn test|bun test"
TEST_MATCH=$(grep -inE "$TEST_PATTERNS" "$CLAUDE_MD" | head -1 || true)
if [[ -n "$TEST_MATCH" ]]; then
  LINE_NUM=$(echo "$TEST_MATCH" | cut -d: -f1)
  echo "{\"check\": \"has-test\", \"pass\": true, \"detail\": \"Test command found on line ${LINE_NUM}\"}"
else
  echo "{\"check\": \"has-test\", \"pass\": false, \"detail\": \"No test command found (looked for npm test, pytest, cargo test, go test, jest, vitest)\"}"
fi

# --- Check: has-lint ---
LINT_PATTERNS="eslint|biome|ruff|golangci-lint|clippy|prettier|make lint|yarn lint|npm run lint"
LINT_MATCH=$(grep -inE "$LINT_PATTERNS" "$CLAUDE_MD" | head -1 || true)
if [[ -n "$LINT_MATCH" ]]; then
  LINE_NUM=$(echo "$LINT_MATCH" | cut -d: -f1)
  echo "{\"check\": \"has-lint\", \"pass\": true, \"detail\": \"Lint command found on line ${LINE_NUM}\"}"
else
  echo "{\"check\": \"has-lint\", \"pass\": false, \"detail\": \"No lint command found (looked for eslint, biome, ruff, golangci-lint, clippy, prettier)\"}"
fi

# --- Check: has-precommit ---
PRECOMMIT_PATTERNS="pre-commit|precommit|before commit|commit checklist|before pushing|pre commit"
PRECOMMIT_MATCH=$(grep -inE "$PRECOMMIT_PATTERNS" "$CLAUDE_MD" | head -1 || true)
if [[ -n "$PRECOMMIT_MATCH" ]]; then
  LINE_NUM=$(echo "$PRECOMMIT_MATCH" | cut -d: -f1)
  echo "{\"check\": \"has-precommit\", \"pass\": true, \"detail\": \"Pre-commit workflow found on line ${LINE_NUM}\"}"
else
  echo "{\"check\": \"has-precommit\", \"pass\": false, \"detail\": \"No pre-commit workflow or checklist found\"}"
fi

# --- Check: commands-valid ---
INVALID_COUNT=0
VALID_COUNT=0

# Check npm/yarn/bun commands → package.json
if grep -qiE "npm |yarn |bun " "$CLAUDE_MD"; then
  if [[ -f "${REPO_ROOT}/package.json" ]]; then
    VALID_COUNT=$((VALID_COUNT + 1))
  else
    echo "{\"check\": \"commands-valid\", \"pass\": false, \"detail\": \"npm/yarn/bun commands referenced but no package.json found\"}"
    INVALID_COUNT=$((INVALID_COUNT + 1))
  fi
fi

# Check make commands → Makefile
if grep -qiE "\bmake\b" "$CLAUDE_MD"; then
  if [[ -f "${REPO_ROOT}/Makefile" ]] || [[ -f "${REPO_ROOT}/makefile" ]] || [[ -f "${REPO_ROOT}/GNUmakefile" ]]; then
    VALID_COUNT=$((VALID_COUNT + 1))
  else
    echo "{\"check\": \"commands-valid\", \"pass\": false, \"detail\": \"make commands referenced but no Makefile found\"}"
    INVALID_COUNT=$((INVALID_COUNT + 1))
  fi
fi

# Check cargo commands → Cargo.toml
if grep -qiE "cargo " "$CLAUDE_MD"; then
  if [[ -f "${REPO_ROOT}/Cargo.toml" ]]; then
    VALID_COUNT=$((VALID_COUNT + 1))
  else
    echo "{\"check\": \"commands-valid\", \"pass\": false, \"detail\": \"cargo commands referenced but no Cargo.toml found\"}"
    INVALID_COUNT=$((INVALID_COUNT + 1))
  fi
fi

# Check go commands → go.mod
if grep -qiE "go build|go test" "$CLAUDE_MD"; then
  if [[ -f "${REPO_ROOT}/go.mod" ]]; then
    VALID_COUNT=$((VALID_COUNT + 1))
  else
    echo "{\"check\": \"commands-valid\", \"pass\": false, \"detail\": \"go commands referenced but no go.mod found\"}"
    INVALID_COUNT=$((INVALID_COUNT + 1))
  fi
fi

# Check pytest → python project indicators
if grep -qiE "pytest" "$CLAUDE_MD"; then
  if [[ -f "${REPO_ROOT}/pyproject.toml" ]] || [[ -f "${REPO_ROOT}/setup.py" ]] || [[ -f "${REPO_ROOT}/setup.cfg" ]]; then
    VALID_COUNT=$((VALID_COUNT + 1))
  else
    echo "{\"check\": \"commands-valid\", \"pass\": false, \"detail\": \"pytest referenced but no Python project file found (pyproject.toml, setup.py)\"}"
    INVALID_COUNT=$((INVALID_COUNT + 1))
  fi
fi

if [[ "$INVALID_COUNT" -eq 0 ]]; then
  if [[ "$VALID_COUNT" -gt 0 ]]; then
    echo "{\"check\": \"commands-valid\", \"pass\": true, \"detail\": \"${VALID_COUNT} command tool(s) verified against repo files\"}"
  else
    echo "{\"check\": \"commands-valid\", \"pass\": true, \"detail\": \"No tool-specific commands to validate\"}"
  fi
fi
