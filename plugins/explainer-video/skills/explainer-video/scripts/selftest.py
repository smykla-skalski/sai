#!/usr/bin/env python3
"""Regression test for the shared pipeline, at no ElevenLabs cost.

  selftest.py [dir]

Scaffolds a project from the templates, voices its beats with synthetic tones
through tts.trim(), checks the transcript normalizer, builds a 480p preview and
makes contact sheets. Then it turns the project into one that an older version of
the skill left behind, refreshes it and renders it, so old projects keep working.
Run it after every change to scripts/ or assets/; it must end with "selftest OK".
Without a dir it uses a temp dir and deletes it on success.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

HERE: Final = Path(__file__).resolve()
UV: Final = ("/usr/bin/env", "uv", "run", "--quiet")
CHARS_PER_SECOND: Final = 16  # the pace of the real voice after trim()
DURATION_TOLERANCE: Final = 0.3
MANIM: Final = ("/usr/bin/env", "uv", "tool", "run", "--python", "3.13")
# video.py as older versions wrote it: Manim's names came only through explainer.py,
# T took Text options and fade_to took animation options. unit() must stay
# explainer's, not Manim's module of the same name.
OLD_VIDEO: Final = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from explainer import *  # the shared look

SCENES = ["Title"]


class Title(Narrated):
    def construct(self):
        self.voice("title_1")
        self.play(Write(T("Old project", 48, YELLOW, weight=BOLD)))
        self.play(fade_to(Circle().shift(unit(0)), run_time=0.5))
        self._until(self.time)
        self.finish()
        self.fade_all()
"""


def check(ok: object, what: object) -> None:
    """Stop the self-test with what when ok is false."""
    if not ok:
        sys.exit(f"selftest FAILED: {what}")


def tones() -> None:
    """Voice every beat with a tone as long as the real voice would speak it.

    Runs inside the project, whose script.py and tts.py exist only there; each tone
    has the edge silence ElevenLabs adds.
    """
    beats = importlib.import_module("script").BEATS
    tts = importlib.import_module("tts")
    tts.OUT.mkdir(exist_ok=True)
    manifest = {}
    for key, text in (b for scene in beats.values() for b in scene):
        mp3, seconds = tts.OUT / f"{key}.mp3", len(text) / CHARS_PER_SECOND
        wave = "0.3*sin(2*PI*180*t)*(0.6+0.4*sin(2*PI*4*t))"
        # S603: list argv, no shell; the only variables are project paths.
        subprocess.run(  # noqa: S603
            [
                "/usr/bin/env",
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"aevalsrc={wave}:s=44100:d={seconds:.2f}",
                "-af",
                "adelay=600,apad=pad_dur=0.6",
                "-ac",
                "1",
                "-b:a",
                "128k",
                str(mp3),
            ],
            check=True,
        )
        dur = tts.trim(mp3, tts.OUT / f"{key}.wav")
        check(abs(dur - seconds) < DURATION_TOLERANCE, f"{key} trimmed to {dur:.2f}s")
        manifest[key] = {"text": text, "dur": dur}
    tts.MANIFEST.write_text(json.dumps(manifest, indent=1))


def normalizer() -> None:
    """Check that transcribe.words() treats formatting differences as equal."""
    words = importlib.import_module("transcribe").words
    cases = [
        (words("Ten thousand, or one percent."), ["#", "or", "#"]),
        (words("O-I-D-C and O-Auth"), ["oidc", "and", "oauth"]),
        (words("thirty-three e-mail"), ["#", "email"]),
        (words("HTTP3 or MP3"), ["http", "#", "or", "mp", "#"]),
        (words("H-T-T-P three or M-P three"), ["http", "#", "or", "mp", "#"]),
        (words("QUIC runs", {"quic": "quick"}), ["quick", "runs"]),
        (words("cosine", {"cosine": "co sign"}), ["co", "sign"]),
        (words("co-sign"), ["co", "sign"]),
        (
            words("minus point six, point eight is the point"),
            ["minus", "#", "is", "the", "point"],
        ),
        (words("minus 0.6, .8 is the point"), ["minus", "#", "is", "the", "point"]),
    ]
    for got, want in cases:
        check(got == want, f"words() gave {got}, expected {want}")


def run(project: Path, *argv: str, env: dict[str, str] | None = None) -> None:
    """Run argv in the project and stop the self-test if it fails."""
    # S603: list argv, no shell; the only variables are project paths.
    done = subprocess.run(argv, cwd=project, env=env, check=False)  # noqa: S603
    check(done.returncode == 0, f"{' '.join(argv)} exited with {done.returncode}")


def scaffold(project: Path) -> str:
    """Run new_project.py on the project and return what it printed."""
    # S603: list argv, no shell; the only variables are project paths.
    done = subprocess.run(  # noqa: S603
        [str(HERE.parent / "new_project.py"), str(project)],
        capture_output=True,
        text=True,
        check=False,
    )
    check(done.returncode == 0, done.stdout + done.stderr)
    return done.stdout


def old_project(project: Path) -> None:
    """Refresh a project as older versions left it, and render its scene."""
    (project / "video.py").write_text(OLD_VIDEO)
    for name in ("build.sh", "sheets.sh"):
        (project / name).write_text("#!/usr/bin/env bash\n")
    scaffold(project)
    video = (project / "video.py").read_text()
    manim_at, explainer_at = (
        video.find("from manim import *"),
        video.find("from explainer"),
    )
    check(0 <= manim_at < explainer_at, f"refresh did not migrate video.py:\n{video}")
    gone = not (project / "build.sh").exists() and not (project / "sheets.sh").exists()
    check(gone, "refresh kept build.sh or sheets.sh")
    # S603: list argv, no shell; the only variables are project paths.
    render = subprocess.run(  # noqa: S603
        [
            *MANIM,
            "--from",
            "manim",
            "manim",
            "-ql",
            "--disable_caching",
            "video.py",
            "Title",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    log = render.stdout + render.stderr
    check(render.returncode == 0 and "Traceback" not in log, log[-2000:])
    scaffold(project)
    check(
        video == (project / "video.py").read_text(), "a second refresh changed video.py"
    )


def main(target: str | None) -> None:
    """Scaffold, voice, check, build and sheet a template project, then migrate it."""
    project = Path(target or tempfile.mkdtemp(prefix="explainer-selftest-")).resolve()
    scaffold(project)
    with_numpy = (*UV, "--python", "3.13", "--with", "numpy", "python")
    run(project, *with_numpy, str(HERE), "--tones")
    run(
        project,
        *UV,
        "--python",
        "3.12",
        "--with",
        "faster-whisper",
        "python",
        str(HERE),
        "--words",
    )
    run(project, *with_numpy, "narration.py", "clips")
    run(project, "./build.py", env={**os.environ, "QUALITY": "l"})
    sheets = subprocess.run(
        ["./sheets.py", "480p15"], cwd=project, capture_output=True, check=False
    )
    check(sheets.returncode == 0, sheets.stderr)
    old_project(project)
    print(f"selftest OK{f': {project}' if target else ''}")
    if not target:
        shutil.rmtree(project)


if __name__ == "__main__":
    if sys.argv[1:] == ["--tones"]:
        sys.path.insert(0, str(Path.cwd()))
        tones()
    elif sys.argv[1:] == ["--words"]:
        sys.path.insert(0, str(Path.cwd()))
        normalizer()
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else None)
