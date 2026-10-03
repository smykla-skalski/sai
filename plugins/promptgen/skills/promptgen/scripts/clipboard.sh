#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
if [[ -z "${input//[[:space:]]/}" ]]; then
  echo "EMPTY_INPUT" >&2
  exit 2
fi

candidates=()
case "$(uname -s)" in
  Darwin) candidates=("pbcopy") ;;
  MINGW* | MSYS* | CYGWIN*) candidates=("clip") ;;
  *)
    if [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
      candidates+=("wl-copy")
    fi
    candidates+=("xclip -selection clipboard" "xsel --clipboard --input" "clip.exe")
    ;;
esac

for candidate in "${candidates[@]}"; do
  read -r -a cmd <<<"${candidate}"
  command -v "${cmd[0]}" >/dev/null 2>&1 || continue
  # xclip, xsel and wl-copy fork a selection owner that inherits stdout and
  # stderr; detaching them keeps the caller from hanging.
  if printf '%s\n' "${input}" | "${cmd[@]}" >/dev/null 2>&1; then
    echo "COPIED ${cmd[0]}"
    exit 0
  fi
done

echo "NO_CLIPBOARD_TOOL" >&2
exit 1
