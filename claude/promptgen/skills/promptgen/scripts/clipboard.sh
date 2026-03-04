#!/usr/bin/env bash
set -euo pipefail
if command -v pbcopy >/dev/null 2>&1; then
  pbcopy
elif command -v xclip >/dev/null 2>&1; then
  xclip -selection clipboard
elif command -v xsel >/dev/null 2>&1; then
  xsel --clipboard --input
else
  echo "NO_CLIPBOARD_TOOL" >&2
  exit 1
fi
