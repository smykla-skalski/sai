#!/usr/bin/env python3
"""Final narration track and audio QA.

Run with: uv run --quiet --python 3.13 --with numpy python narration.py ...

  clips                    check every clip in audio/ (after tts.py, before rendering)
  mix 1080p60              write media/narration.wav (build.py does this)
  check 1080p60 video.mp4  clips + timeline + final file; exit 1 on any problem
  where 1:31 [1080p60]     which scene, clip and words play at a time in the video

The track is built from the trimmed clips at the times video.py logs (TIMELINE
lines in media/<Scene>.log), not from Manim's scene audio: Manim's mix carries a
21 ms AAC delay and its cache can drop clips. Every threshold below maps to a
defect a listener heard; fix the cause instead of loosening one.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import itertools
import json
import re
import subprocess
import sys
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np
from build import scene_names
from script import BEATS

if TYPE_CHECKING:
    import numpy.typing as npt

    Signal = npt.NDArray[np.float64]

ROOT: Final = Path(__file__).parent
SR: Final = 44100
WIN: Final = SR // 50  # 20 ms
FINE: Final = SR // 200  # 5 ms, for clicks
FINE_S: Final = 0.005  # FINE in seconds, as the click thresholds were tuned
MIX: Final = ROOT / "media" / "narration.wav"
FFMPEG: Final = ("/usr/bin/env", "ffmpeg", "-v", "error")
FFPROBE: Final = ("/usr/bin/env", "ffprobe", "-v", "error")

MAX_GAP: Final = 1.6  # longest stretch without voice anywhere in the video, s
LENGTH_TOLERANCE: Final = 0.002  # clip file against its manifest duration, s
EDGE_DB: Final = -60  # a clip must start and end below this
VOICE_DB: Final = -45  # speech is louder than this
MAX_LEAD: Final = 0.1  # dead air before the first word, s
MAX_TAIL: Final = 0.25  # dead air after the last word, s
SYNC_TOLERANCE: Final = 0.005  # audio against picture, s
DURATION_TOLERANCE: Final = 0.05  # final audio and video against the mix, s
SPEECH_DB: Final = -35  # loud enough in the mix to compare levels
SILENT_DB: Final = -60  # quiet in the mix: the final file must be quiet too
EXTRA_SOUND_DB: Final = -50  # louder than this where the mix is silent: extra sound
MISSING_DB: Final = 10  # quieter than the mix by this much: missing voice
MAX_DRIFT_DB: Final = 3  # level change against the clips at the 99th percentile
MAX_PEAK_DB: Final = -1  # dBFS
SYNC_WINDOW: Final = 60  # seconds of audio cross-correlated to find the offset
SHOWN: Final = 10  # times listed per problem

problems: list[str] = []


CLIPS: Final = json.loads((ROOT / "audio" / "manifest.json").read_text())
SCENES: Final = scene_names(ROOT / "video.py")


def load(path: Path) -> Signal:
    """Return the audio of path as mono float samples at SR."""
    # S603: list argv, no shell; the only variables are project paths.
    out = subprocess.check_output(  # noqa: S603
        [
            *FFMPEG,
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SR),
            "-f",
            "f32le",
            "-",
        ]
    )
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def video_duration(path: Path) -> float:
    """Return the duration of the video stream of path in seconds."""
    # S603: list argv, no shell; the only variables are project paths.
    out = subprocess.check_output(  # noqa: S603
        [
            *FFPROBE,
            *("-select_streams", "v", "-show_entries", "stream=duration"),
            *("-of", "csv=p=0", str(path)),
        ]
    )
    return float(out)


def env(x: Signal, win: int = WIN) -> Signal:
    """Return the level of x in dB per window of win samples."""
    n = len(x) // win
    return 10 * np.log10((x[: n * win].reshape(n, win) ** 2).mean(1) + 1e-12)


def islands(
    db: Signal, step: float, loud: float = -50, max_len: float = 0.3, gap: float = 0.25
) -> list[float]:
    """Return the start times of short sounds with silence on both sides.

    These are clicks and taps; the file edges count as silence.
    """
    on = np.concatenate([[False], db > loud, [False]])
    edges = np.flatnonzero(np.diff(on.astype(int)))
    runs = list(zip(edges[::2], edges[1::2], strict=True))
    found = []
    for k, (a, b) in enumerate(runs):
        before = (a - runs[k - 1][1]) * step if k else np.inf
        after = (runs[k + 1][0] - b) * step if k + 1 < len(runs) else np.inf
        if (b - a) * step <= max_len and before >= gap and after >= gap:
            found.append(round(float(a * step), 3))
    return found


def fail(msg: str) -> None:
    """Record and print one problem."""
    problems.append(msg)
    print("  FAIL", msg)


def timeline(scene: str) -> dict[str, float]:
    """Return {clip key: start time} that the scene logged while rendering."""
    log = (ROOT / "media" / f"{scene}.log").read_text()
    return {k: float(t) for k, t in re.findall(r"TIMELINE (\S+) ([\d.]+)", log)}


def scene_mix(scene: str, length: int) -> Signal:
    """Return the narration of one scene, length samples long."""
    mix = np.zeros(length)
    for key, t0 in timeline(scene).items():
        clip = load(ROOT / "audio" / f"{key}.wav")
        a = round(t0 * SR)
        mix[a : a + len(clip)] += clip[: max(0, length - a)]
    return mix


def full_mix(res: str) -> Signal:
    """Return the narration of the whole video, scene by scene."""
    videos = ROOT / "media" / "videos" / "video" / res
    lengths = [round(video_duration(videos / f"{s}.mp4") * SR) for s in SCENES]
    return np.concatenate(
        [scene_mix(s, n) for s, n in zip(SCENES, lengths, strict=True)]
    )


def write_mix(res: str) -> None:
    """Write the narration of the whole video to media/narration.wav."""
    pcm = (np.clip(full_mix(res), -1, 1) * 32767).astype("<i2")
    with wave.open(str(MIX), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def check_clips() -> None:
    """Check every clip for length, edges, dead air and clicks."""
    print("clips")
    for key, meta in CLIPS.items():
        x = load(ROOT / "audio" / f"{key}.wav")
        if abs(len(x) / SR - meta["dur"]) > LENGTH_TOLERANCE:
            fail(f"{key}: length {len(x) / SR:.3f}s, manifest says {meta['dur']:.3f}s")
        db = env(x, FINE)
        if db[0] > EDGE_DB or db[-1] > EDGE_DB:
            fail(
                f"{key}: starts or ends inside a sound ({db[0]:.0f} / {db[-1]:.0f} dB)"
            )
        loud = np.flatnonzero(db > VOICE_DB)
        lead, tail = loud[0] * FINE_S, (len(db) - loud[-1]) * FINE_S
        if lead > MAX_LEAD or tail > MAX_TAIL:
            fail(f"{key}: dead air at the edges ({lead:.2f}s / {tail:.2f}s)")
        if isl := islands(db, FINE_S):
            fail(f"{key}: isolated short sounds at {isl}")


def check_timeline() -> None:
    """Check that every scene played its clips once, in order, without overlap."""
    print("timeline")
    for scene in SCENES:
        starts = timeline(scene)
        keys = [k for k, _ in BEATS[scene]]
        if list(starts) != keys:
            fail(f"{scene}: narrated {list(starts)}, script has {keys}")
            continue
        for a, b in itertools.pairwise(keys):
            if starts[b] < starts[a] + CLIPS[a]["dur"] - 1e-3:
                fail(f"{scene}: {b} starts before {a} ends")


def check_sync(want: Signal, got: Signal) -> None:
    """Check that the final audio sits within SYNC_TOLERANCE of the picture."""
    n = min(len(got), len(want), SYNC_WINDOW * SR)
    c = np.fft.irfft(
        np.fft.rfft(got[:n], 2 * n) * np.conj(np.fft.rfft(want[:n], 2 * n))
    )
    lag = int(np.argmax(c))
    offset = (lag if lag < n else lag - 2 * n) / SR
    if abs(offset) > SYNC_TOLERANCE:
        fail(f"audio is {offset * 1000:+.0f} ms off the picture")


def check_levels(want: Signal, got: Signal) -> float:
    """Check the final audio against the mix for extra or missing sound; return gain."""
    n = min(len(got), len(want))
    g, w = env(got[:n]), env(want[:n])
    speech = w > SPEECH_DB
    gain = float(np.median(g[speech] - w[speech]))
    extra = np.flatnonzero((w < SILENT_DB) & (g > EXTRA_SOUND_DB + gain))
    missing = np.flatnonzero(speech & (g < w + gain - MISSING_DB))
    for label, idx in [("unexpected sound", extra), ("missing voice", missing)]:
        if len(idx):
            times = sorted({round(float(i * WIN / SR), 1) for i in idx})
            fail(f"{label} at {times[:SHOWN]}s")
    drift = np.percentile(np.abs(g[speech] - w[speech] - gain), 99)
    if drift > MAX_DRIFT_DB:
        fail(f"level differs from the clips by up to {drift:.1f} dB")
    return gain


def check_final(res: str, final: Path) -> None:
    """Check the finished video against the mix built from the clips."""
    print("final")
    want, got = full_mix(res), load(final)
    if abs(video_duration(final) - len(want) / SR) > DURATION_TOLERANCE:
        fail(f"video is {video_duration(final):.2f}s, narration {len(want) / SR:.2f}s")
    if abs(len(got) - len(want)) / SR > DURATION_TOLERANCE:
        fail(f"audio is {len(got) / SR:.2f}s, narration {len(want) / SR:.2f}s")
    check_sync(want, got)
    gain = check_levels(want, got)
    if isl := islands(env(got, FINE), FINE_S):
        fail(f"isolated short sounds at {isl}s")
    n = min(len(got), len(want))
    on = np.flatnonzero(env(want[:n]) > VOICE_DB) * WIN / SR
    for a, b in itertools.pairwise(on):
        if b - a > MAX_GAP:
            fail(f"no voice for {b - a:.1f}s from {a:.1f}s")
    peak = 20 * np.log10(np.abs(got).max())
    if peak > MAX_PEAK_DB:
        fail(f"peak {peak:.1f} dBFS is too close to clipping")
    print(
        f"  {len(got) / SR:.2f}s, gain {gain:+.1f} dB, peak {peak:.1f} dBFS, "
        f"longest pause {np.max(np.diff(on)):.2f}s"
    )


def where(stamp: str, res: str) -> None:
    """Print the scene, clip and words playing at a reported time ("1:31", "91.5")."""
    t = sum(float(p) * 60**i for i, p in enumerate(reversed(stamp.split(":"))))
    start, scene, dur = 0.0, SCENES[-1], 0.0
    for scene in SCENES:
        dur = video_duration(ROOT / "media" / "videos" / "video" / res / f"{scene}.mp4")
        if t < start + dur:
            break
        start += dur
    local = t - start
    print(
        f"{stamp} = {scene} at {local:.2f}s (starts at {start:.2f}s, {dur:.2f}s long)"
    )
    for key, t0 in timeline(scene).items():
        clip_t, meta = local - t0, CLIPS[key]
        mark = ""
        if clip_t < 0:
            state = "not started"
        elif clip_t > meta["dur"]:
            state = "ended"
        else:
            state = "playing"
            i = int(len(meta["text"]) * clip_t / meta["dur"])
            before, after = meta["text"][max(0, i - 30) : i], meta["text"][i : i + 30]
            mark = f'  ~ "...{before}|{after}..."'
        print(f"  {key:10s} {t0:7.2f}-{t0 + meta['dur']:7.2f}s  {state}{mark}")


def main(cmd: str, *args: str) -> None:
    """Run one of the commands in the module docstring."""
    if cmd == "where":
        where(args[0], args[1] if len(args) > 1 else "1080p60")
        return
    if cmd == "mix":
        write_mix(args[0])
        return
    check_clips()
    if cmd == "check":
        check_timeline()
        check_final(args[0], ROOT / args[1])
    print("OK" if not problems else f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main(*sys.argv[1:])
