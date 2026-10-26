#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# Python inputs are stored as .py.txt so that repo linters skip these deliberately flawed files.
find . -name '*.py.txt' -exec sh -c 'mv "$1" "${1%.txt}"' _ {} \;
