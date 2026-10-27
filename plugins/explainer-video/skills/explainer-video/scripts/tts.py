#!/usr/bin/env python3
"""Render narration clips with ElevenLabs into audio/. Needs ELEVEN_API_KEY.

Clips are cached in audio/manifest.json and rendered again only when their text
changes or their key is passed on the command line (python3 tts.py emb_1 rr_2) to
get a new take. Every take costs ElevenLabs characters, so retake only the clips a
check flagged. ELEVEN_VOICE_ID and ELEVEN_MODEL override the voice and model.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import array
import json
import os
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Final

from script import BEATS

if TYPE_CHECKING:
    from collections.abc import Collection

VOICE: Final = os.environ.get("ELEVEN_VOICE_ID", "iP95p4xoKVk53GoZ742B")  # Chris
MODEL: Final = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
OUT: Final = Path(__file__).parent / "audio"
MANIFEST: Final = OUT / "manifest.json"
SR: Final = 44100
WINDOW: Final = SR // 200  # 5 ms
MERGE_DIP: Final = 20  # windows: dips under 100 ms stay inside the speech
SHORT_SOUND: Final = 30  # windows: an edge sound under 150 ms ...
LONG_SILENCE: Final = 40  # ... separated by over 200 ms of silence is a click
TIMEOUT: Final = 120
FFMPEG: Final = ("/usr/bin/env", "ffmpeg")


def synth(text: str, prev: str, nxt: str, path: Path) -> None:
    """Write the ElevenLabs take of text, voiced in context, to path as MP3."""
    body = {"text": text, "model_id": MODEL, "previous_text": prev, "next_text": nxt}
    headers = {
        "xi-api-key": os.environ["ELEVEN_API_KEY"],
        "Content-Type": "application/json",
    }
    with urllib.request.urlopen(
        urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}"
            "?output_format=mp3_44100_128",
            data=json.dumps(body).encode(),
            headers=headers,
        ),
        timeout=TIMEOUT,
    ) as r:
        path.write_bytes(r.read())


def trim(
    src: Path,
    dst: Path,
    threshold_db: float = -45,
    lead: float = 0.05,
    tail: float = 0.15,
) -> float:
    """Cut the edge silence ElevenLabs adds and fade both cuts; return the duration.

    Takes carry up to 1.5 s of edge silence (dead air in the video), and some end
    with a lone click about 1 s after the last word, so short sounds separated from
    the speech by silence at either edge are cut too. Done sample-exact here:
    ffmpeg's silenceremove+areverse trick leaves a 50 ms speech fragment at the end.
    """
    # S603: list argv, no shell; the only variables are project paths.
    raw = subprocess.check_output(  # noqa: S603
        [
            *FFMPEG,
            "-v",
            "error",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(SR),
            "-f",
            "s16le",
            "-",
        ]
    )
    pcm = array.array("h", raw)
    limit = (32768 * 10 ** (threshold_db / 20)) ** 2 * WINDOW
    loud = [
        i
        for i in range(len(pcm) // WINDOW)
        if sum(v * v for v in pcm[i * WINDOW : (i + 1) * WINDOW]) > limit
    ]
    runs: list[list[int]] = []  # [first, last] loud windows
    for i in loud:
        if runs and i - runs[-1][1] <= MERGE_DIP:
            runs[-1][1] = i
        else:
            runs.append([i, i])

    def is_click(sound: list[int], gap: int) -> bool:
        return sound[1] - sound[0] < SHORT_SOUND and gap > LONG_SILENCE

    while len(runs) > 1 and is_click(runs[-1], runs[-1][0] - runs[-2][1]):
        runs.pop()
    while len(runs) > 1 and is_click(runs[0], runs[1][0] - runs[0][1]):
        runs.pop(0)
    start = runs[0][0] * WINDOW - int(lead * SR)
    end = (runs[-1][1] + 1) * WINDOW + int(tail * SR)
    out = array.array("h", bytes(2 * max(0, -start)))  # some takes speak at sample 0
    out += pcm[max(0, start) : min(len(pcm), end)]
    fade_in, fade_out = int(0.01 * SR), int(0.03 * SR)
    for i in range(fade_in):
        out[i] = out[i] * i // fade_in
    for i in range(fade_out):
        out[-1 - i] = out[-1 - i] * i // fade_out
    with wave.open(str(dst), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(out.tobytes())
    return len(out) / SR


def main(redo: Collection[str]) -> None:
    """Voice new, changed and redo clips; trim any clip without a WAV."""
    OUT.mkdir(exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    beats = [b for scene in BEATS.values() for b in scene]
    for i, (key, text) in enumerate(beats):
        mp3, wav = OUT / f"{key}.mp3", OUT / f"{key}.wav"
        if key in redo or manifest.get(key, {}).get("text") != text or not mp3.exists():
            prev = beats[i - 1][1] if i else ""
            nxt = beats[i + 1][1] if i + 1 < len(beats) else ""
            synth(text, prev, nxt, mp3)
        elif wav.exists():
            continue
        manifest[key] = {"text": text, "dur": trim(mp3, wav)}
        MANIFEST.write_text(json.dumps(manifest, indent=1))
        print(f"{key}: {manifest[key]['dur']:.1f}s")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
