#!/usr/bin/env bash
# Commit the base app, then leave the change uncommitted so that a bare
# /rightsize has only the working tree to audit.
set -eu
src="$(dirname "$0")/files"
# Python inputs are stored as .py.txt so that repo linters skip these deliberately flawed files.
unpack() { find . -name '*.py.txt' -exec sh -c 'mv "$1" "${1%.txt}"' _ {} \; ; }
cp -R "$src/base/." .
unpack
git init -q
git add -A
git -c user.name=dev -c user.email=dev@example.com -c commit.gpgsign=false \
  commit -qm "Send overdue invoice reminders"
cp -R "$src/change/." .
unpack
rm remind/mailer.py tests/test_mailer.py
