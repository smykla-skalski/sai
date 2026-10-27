#!/usr/bin/env bash
# The run needs a real ElevenLabs key; it never enters the repository.
set -eu
umask 077
printf '%s\n' "${ELEVEN_API_KEY:?set ELEVEN_API_KEY to an ElevenLabs API key}" > eleven.key
