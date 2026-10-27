#!/usr/bin/env python3
"""Render all scenes in parallel, build the narration from the clips, stitch one video.

  QUALITY=l ./build.py    l (480p15), m (720p30), h (1080p60, default), k (2160p60)
  OUT=name.mp4 ./build.py the output file; previews get the resolution in the name

Run tts.py first. Ends with narration.py check and exits with its status, so a
non-zero exit means an audio problem.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent
RESOLUTIONS: Final = {"l": "480p15", "m": "720p30", "h": "1080p60", "k": "2160p60"}
MANIM: Final = ("/usr/bin/env", "uv", "tool", "run", "--python", "3.13")
NARRATION: Final = (
    *("/usr/bin/env", "uv", "run", "--quiet", "--python", "3.13", "--with", "numpy"),
    *("python", "narration.py"),
)
FFMPEG: Final = ("/usr/bin/env", "ffmpeg", "-hide_banner")
TARGET_LUFS: Final = -16
TARGET_PEAK: Final = -1.5  # dBTP
TAIL_LINES: Final = 25


def scene_names(video: Path) -> list[str]:
    """Return SCENES from video.py without importing Manim."""
    for node in ast.parse(video.read_text()).body:
        if isinstance(node, ast.Assign):
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "SCENES":
            return list(ast.literal_eval(value))
    msg = f"no SCENES list in {video}"
    raise SystemExit(msg)


def render(scenes: list[str], quality: str) -> None:
    """Render every scene at once, each into media/<Scene>.log; exit on a failure."""
    # Always render fresh: with Manim's partial-movie cache, re-renders dropped
    # narration clips.
    procs = []
    for s in scenes:
        with (ROOT / "media" / f"{s}.log").open("w") as out:
            argv = [*MANIM, "--from", "manim", "manim", f"-q{quality}"]
            argv += ["--disable_caching", "video.py", s]
            # S603: list argv, no shell; the only variables are project paths.
            procs.append(subprocess.Popen(argv, cwd=ROOT, stdout=out, stderr=out))  # noqa: S603
    codes = [p.wait() for p in procs]
    for s, code in zip(scenes, codes, strict=True):
        log = (ROOT / "media" / f"{s}.log").read_text()
        if code or "Traceback" in log:
            print("\n".join(log.splitlines()[-TAIL_LINES:]))
            sys.exit(f"render of {s} failed (media/{s}.log)")
    # Cues reached after their word was spoken: shorten the run_times before them.
    for s in scenes:
        for line in (ROOT / "media" / f"{s}.log").read_text().splitlines():
            if line.startswith("LATE"):
                print(line, flush=True)


def static_gain() -> float:
    """Return one gain for -16 LUFS, lowered if the peak would pass -1.5 dBTP.

    One static gain, not loudnorm's single-pass dynamic mode, which pumps.
    """
    # S603: list argv, no shell; the only variables are project paths.
    probe = subprocess.run(  # noqa: S603
        [
            *FFMPEG,
            "-i",
            "media/narration.wav",
            "-af",
            f"loudnorm=I={TARGET_LUFS}:TP={TARGET_PEAK}:print_format=json",
            "-f",
            "null",
            "-",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    stats = json.loads(re.findall(r"\{[^{}]+\}", probe.stderr)[-1])
    gain = min(
        TARGET_LUFS - float(stats["input_i"]), TARGET_PEAK - float(stats["input_tp"])
    )
    return round(gain, 2)


def main() -> None:
    """Render, mix, mux and check the video."""
    quality = os.environ.get("QUALITY", "h")
    if quality not in RESOLUTIONS:
        sys.exit(f"QUALITY must be one of {', '.join(RESOLUTIONS)}, not {quality!r}")
    res = RESOLUTIONS[quality]
    # Previews get the resolution in the name so they never pass for (or
    # overwrite) the final video.
    suffix = "" if quality == "h" else f"-{res}"
    out = os.environ.get("OUT", f"{ROOT.name}{suffix}.mp4")
    (ROOT / "media").mkdir(exist_ok=True)
    scenes = scene_names(ROOT / "video.py")
    render(scenes, quality)
    videos = ROOT / "media" / "videos" / "video" / res
    concat = "".join(f"file '{videos / s}.mp4'\n" for s in scenes)
    (ROOT / "media" / "video.txt").write_text(concat)
    # S603: list argv, no shell; the only variables are project paths.
    subprocess.run([*NARRATION, "mix", res], cwd=ROOT, check=True)  # noqa: S603
    gain = static_gain()
    # S603: list argv, no shell; the only variables are project paths.
    subprocess.run(  # noqa: S603
        [
            *FFMPEG,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "media/video.txt",
            "-i",
            "media/narration.wav",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-af",
            f"volume={gain}dB",
            "-ar",
            "48000",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out,
        ],
        cwd=ROOT,
        check=True,
    )
    print(f"wrote {out} from {videos.relative_to(ROOT)}/ (gain {gain} dB)", flush=True)
    sys.exit(
        # S603: list argv, no shell; the only variables are project paths.
        subprocess.run(  # noqa: S603
            [*NARRATION, "check", res, out], cwd=ROOT, check=False
        ).returncode
    )


if __name__ == "__main__":
    main()
