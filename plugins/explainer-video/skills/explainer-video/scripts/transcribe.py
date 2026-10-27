#!/usr/bin/env python3
"""Transcribe each narration clip with Whisper and compare it with the script text.

  uv run --quiet --python 3.12 --with faster-whisper python transcribe.py [keys...]

Catches what level checks cannot: mispronounced terms, wrong or dropped words,
garbled takes. Numbers are compared as one "#" token ("ten thousand" = "10 000",
"one percent" = "1%", "point eight" = ".8"), because Whisper writes digits, and
differences in spacing only ("key card" / "keycard", "HTTP3" / "H-T-T-P three")
are ignored. Terms spelled by sound in the script ("Quick" for QUIC) are mapped
back with HEARD in script.py. Judge each remaining flag: some are harmless ("Here
is" spoken as "Here's").

No initial_prompt on purpose: a prompt with the expected terms hides
mispronunciations ("cosine" spoken as "co-zeen" was only caught without one).
Audio is passed as an array because faster-whisper's own file loading breaks with
newer PyAV.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np
import script
from faster_whisper import WhisperModel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ROOT: Final = Path(__file__).parent
FFMPEG: Final = ("/usr/bin/env", "ffmpeg", "-v", "error")
MAX_DIFF: Final = 0.03  # share of differing words that flags a clip
NUMBER_WORDS: Final = frozenset(
    {
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
        "billion",
        "trillion",
        "percent",
    }
)


def words(s: str, heard: Mapping[str, str] | None = None) -> list[str]:
    """Return the normalized tokens of s.

    heard maps Whisper's spelling of a word to the script's ("quic" -> "quick").
    """
    # The script spells acronyms for the voice ("O-I-D-C", "O-Auth"); Whisper writes
    # them as one word.
    s = re.sub(r"\b([a-z])-(?=[a-z])", r"\1", s.lower())
    s = re.sub(r"(?<=[a-z])(?=[0-9])", " ", s)  # "HTTP3" -> "http 3"
    out: list[str] = []
    tokens = re.sub(r"[^a-z0-9 ]", " ", s.replace("-", " ")).split()
    tokens = [x for t in tokens for x in (heard or {}).get(t, t).split()]
    for i, w in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        # "point eight" is the script's spelling of Whisper's ".8"
        is_number = w.isdigit() or w in NUMBER_WORDS
        if is_number or (w == "point" and (nxt.isdigit() or nxt in NUMBER_WORDS)):
            if out and out[-1] == "#":
                continue
            out.append("#")
        else:
            out.append(w)
    return out


def main(keys: Sequence[str]) -> None:
    """Transcribe the clips and print the ones whose words differ from the script."""
    clips = json.loads((ROOT / "audio" / "manifest.json").read_text())
    heard_map = getattr(script, "HEARD", {})
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    flagged = 0
    for key in keys or clips:
        wav = ROOT / "audio" / f"{key}.wav"
        # S603: list argv, no shell; the only variables are project paths.
        out = subprocess.check_output(  # noqa: S603
            [*FFMPEG, "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
        )
        audio = np.frombuffer(out, dtype=np.float32)
        segments, _ = model.transcribe(audio, beam_size=5, language="en")
        heard = " ".join(s.text.strip() for s in segments)
        want, got = words(clips[key]["text"]), words(heard, heard_map)
        sm = difflib.SequenceMatcher(None, want, got)
        diffs = [
            (want[a:b], got[c:d])
            for op, a, b, c, d in sm.get_opcodes()
            if op != "equal"
        ]
        # Spacing only ("key card" -> "keycard", "open id" -> "openid") is Whisper's
        # spelling, not the voice.
        diffs = [(w, g) for w, g in diffs if "".join(w) != "".join(g)]
        flag = sum(max(len(w), len(g)) for w, g in diffs) > MAX_DIFF * len(want)
        flagged += flag
        shown = "; ".join(
            f"{' '.join(w) or '-'} -> {' '.join(g) or '-'}" for w, g in diffs
        )
        print(f"{'CHECK' if flag else 'ok   '} {key:10s} {sm.ratio():.3f} {shown}")
        if flag:
            print(f"        heard: {heard}")
    print(f"{flagged} clip(s) to judge")


if __name__ == "__main__":
    main(sys.argv[1:])
