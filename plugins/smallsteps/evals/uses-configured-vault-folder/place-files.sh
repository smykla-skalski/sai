#!/usr/bin/env bash
set -eu
mkdir -p "$HOME/.local/share/sai/smallsteps" "$PWD/vault/Ideas"
printf '%s\n' "$PWD/vault/Ideas" > "$HOME/.local/share/sai/smallsteps/notes-dir"
