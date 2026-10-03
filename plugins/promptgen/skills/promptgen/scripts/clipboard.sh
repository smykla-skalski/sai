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

has_non_ascii() {
  LC_ALL=C grep -q '[^[:print:][:space:]]' <<<"${input}"
}

# Windows clip decodes stdin with the ANSI codepage unless it starts with a
# UTF-16 BOM, which would turn non-ASCII text into mojibake.
emit() {
  if [[ "$1" == utf16 ]]; then
    printf '\xff\xfe'
    printf '%s\n' "${input}" | iconv -f UTF-8 -t UTF-16LE
  else
    printf '%s\n' "${input}"
  fi
}

for candidate in "${candidates[@]}"; do
  read -r -a cmd <<<"${candidate}"
  command -v "${cmd[0]}" >/dev/null 2>&1 || continue
  encoding="utf8"
  if [[ "${cmd[0]}" == clip || "${cmd[0]}" == clip.exe ]]; then
    if command -v iconv >/dev/null 2>&1; then
      encoding="utf16"
    elif has_non_ascii; then
      continue
    fi
  fi
  # xclip, xsel and wl-copy fork a selection owner that inherits stdout and
  # stderr; detaching them keeps the caller from hanging.
  if emit "${encoding}" | "${cmd[@]}" >/dev/null 2>&1; then
    echo "COPIED ${cmd[0]}"
    exit 0
  fi
done

echo "NO_CLIPBOARD_TOOL" >&2
exit 1
