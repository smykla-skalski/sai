#!/usr/bin/env python3
"""Contact sheets for visual review: 4x4 frames, one sheet per started 40 s of a scene.

  ./sheets.py [480p15|1080p60] [out-dir]

Writes <out-dir>/<Scene>-<n>.png (default media/sheets), a frame every 2.5 s or
less: fewer frames missed short states (a label shown for 3 s in a 66 s scene).
Read every sheet: cut-off text, overlaps, leftovers, empty frames.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path
from typing import Final

from build import scene_names

ROOT: Final = Path(__file__).resolve().parent
SECONDS_PER_SHEET: Final = 40
TILES: Final = 16


def main(res: str = "480p15", out: str = "media/sheets") -> None:
    """Write the contact sheets of every scene and print their paths."""
    out_dir = ROOT / out
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in scene_names(ROOT / "video.py"):
        video = ROOT / "media" / "videos" / "video" / res / f"{s}.mp4"
        # S603: list argv, no shell; the only variables are project paths.
        probe = subprocess.check_output(  # noqa: S603
            [
                "/usr/bin/env",
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video),
            ],
            text=True,
        )
        d = float(probe)
        n = math.ceil(d / SECONDS_PER_SHEET)
        for old in [out_dir / f"{s}.png", *out_dir.glob(f"{s}-*.png")]:
            old.unlink(missing_ok=True)
        # S603: list argv, no shell; the only variables are project paths.
        subprocess.run(  # noqa: S603
            [
                "/usr/bin/env",
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(video),
                "-vf",
                f"fps={TILES * n}/{d},scale=480:270,tile=4x4",
                "-frames:v",
                str(n),
                str(out_dir / f"{s}-%d.png"),
            ],
            check=True,
        )
        for sheet in sorted(out_dir.glob(f"{s}-*.png")):
            print(sheet.relative_to(ROOT))


if __name__ == "__main__":
    main(*sys.argv[1:])
