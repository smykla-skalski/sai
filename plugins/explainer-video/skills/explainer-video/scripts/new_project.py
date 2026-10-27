#!/usr/bin/env python3
"""Scaffold or refresh an explainer-video project: pipeline, fonts, tool check.

  new_project.py <project-dir>

Shared code (the pipeline scripts and explainer.py) is always refreshed, so fixes in
the skill reach old projects; script.py and video.py are copied only if missing.
A refresh also migrates a project made by an older version of the skill: it removes
the shell scripts that build.py and sheets.py replace, and gives a video.py that
gets Manim's names through explainer.py its own `from manim import *`.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

SKILL: Final = Path(__file__).resolve().parent.parent
PIPELINE: Final = ("tts.py", "narration.py", "build.py", "transcribe.py", "sheets.py")
STARTERS: Final = ("script.py", "video.py")
FONTS: Final = ("cmunrm.otf", "cmunbx.otf", "cmunti.otf", "cmuntt.otf")
TOOLS: Final = ("ffmpeg", "ffprobe", "uv", "python3")
TIMEOUT: Final = 300
# Shared files that older versions copied into projects; build.py and sheets.py
# replace them.
RETIRED: Final = ("build.sh", "sheets.sh")
STAR_EXPLAINER: Final = re.compile(r"^from explainer import \*", re.MULTILINE)
STAR_MANIM: Final = re.compile(r"^from manim import \*", re.MULTILINE)


def fetch_fonts(fonts: Path) -> None:
    """Copy the CMU fonts from CTAN into fonts/.

    CMU Serif is the Computer Modern look of 3b1b videos. LaTeX is not needed:
    Manim's Text renders it through Pango.
    """
    with urllib.request.urlopen(
        "https://mirrors.ctan.org/fonts/cm-unicode.zip", timeout=TIMEOUT
    ) as r:
        archive = zipfile.ZipFile(io.BytesIO(r.read()))
    for name in archive.namelist():
        if Path(name).name in FONTS:
            (fonts / Path(name).name).write_bytes(archive.read(name))


def migrate_video(video: Path) -> bool:
    """Give an old video.py its own `from manim import *`; return True if changed.

    explainer.py used to re-export all of Manim, so old video.py files get Manim's
    names only through `from explainer import *`. The new import goes above that
    line: explainer's helpers then still win where Manim has the same name (unit),
    as they did before.
    """
    if not video.exists():
        return False
    text = video.read_text()
    star = STAR_EXPLAINER.search(text)
    if star is None or STAR_MANIM.search(text):
        return False
    video.write_text(
        f"{text[: star.start()]}from manim import *\n{text[star.start() :]}"
    )
    return True


def retire_old_scripts(root: Path) -> list[str]:
    """Remove the shared shell scripts of older versions; return their names.

    They were shared code that every refresh overwrote, so they hold no user edits.
    """
    removed = [name for name in RETIRED if (root / name).exists()]
    for name in removed:
        (root / name).unlink()
    return removed


def main(project: str) -> None:
    """Scaffold or refresh the project at the given path."""
    root = Path(project)
    for sub in ("audio", "fonts", "media"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    for name in PIPELINE:
        shutil.copy(SKILL / "scripts" / name, root / name)
        (root / name).chmod(0o755)
    shutil.copy(SKILL / "assets" / "explainer.py", root / "explainer.py")
    for name in STARTERS:
        if not (root / name).exists():
            shutil.copy(SKILL / "assets" / name, root / name)
    if migrate_video(root / "video.py"):
        print(
            "video.py: added `from manim import *`, which explainer.py no longer gives"
        )
    if removed := retire_old_scripts(root):
        print(f"removed {', '.join(removed)}: build.py and sheets.py replace them")
    if not (root / ".gitignore").exists():
        (root / ".gitignore").write_text("media/\n__pycache__/\n*.mp4\n")
    if not (root / "fonts" / FONTS[0]).exists():
        fetch_fonts(root / "fonts")
    # Flush before the Manim check, whose output would otherwise come first.
    print(" ".join(sorted(p.name for p in (root / "fonts").iterdir())), flush=True)
    if missing := [t for t in TOOLS if not shutil.which(t)]:
        sys.exit(f"missing tool(s): {', '.join(missing)}")
    # Manim needs Python <= 3.13 (pycairo, manimpango wheels); uv provides it without
    # touching the system Python.
    subprocess.run(
        [
            "/usr/bin/env",
            "uv",
            "tool",
            "run",
            "--python",
            "3.13",
            "--from",
            "manim",
            "manim",
            "--version",
        ],
        check=True,
    )
    print(f"project ready: {root}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold or refresh a project.")
    parser.add_argument("project", help="project directory, created if missing")
    main(parser.parse_args().project)
