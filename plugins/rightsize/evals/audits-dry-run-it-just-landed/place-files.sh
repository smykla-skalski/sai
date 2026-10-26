#!/usr/bin/env bash
# A repo with one recorded change, so that the change the agent makes and
# records during the run is the only work the audit should find.
set -eu
cp -R "$(dirname "$0")/files/." .
# Python inputs are stored as .py.txt so that repo linters skip these deliberately flawed files.
find . -name '*.py.txt' -exec sh -c 'mv "$1" "${1%.txt}"' _ {} \;
git init -q
git config user.name dev
git config user.email dev@example.com
git config commit.gpgsign false
git add -A
git commit -qm "Send overdue invoice reminders"
