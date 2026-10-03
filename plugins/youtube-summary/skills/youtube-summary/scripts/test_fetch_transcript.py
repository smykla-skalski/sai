#!/usr/bin/env -S uv run --quiet --script
"""Offline checks for fetch_transcript.py. Run: uv run --script test_fetch_transcript.py"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from xml.etree.ElementTree import ParseError

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import fetch_transcript as ft
import requests
from youtube_transcript_api import TranscriptsDisabled, YouTubeRequestFailed

VIDEO_ID = "jNQXAC9IVRw"


# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api>=1.2.0", "requests>=2.31"]
# ///
def test_extract_video_id_accepts_youtube_forms():
    accepted = [
        VIDEO_ID,
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s&list=PL123",
        f"https://youtube.com/watch?feature=share&v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://music.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?si=abc",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}?feature=share",
        f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}",
        f"www.youtube.com/watch?v={VIDEO_ID}",
        f"youtu.be/{VIDEO_ID}",
        f"  https://youtu.be/{VIDEO_ID}  ",
    ]
    for url in accepted:
        assert ft.extract_video_id(url) == VIDEO_ID, url


def test_extract_video_id_rejects_non_videos():
    rejected = [
        "",
        "not a url",
        "https://example.com/watch?v=jNQXAC9IVRw",
        "https://youtube.com.evil.example/watch?v=jNQXAC9IVRw",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch?v=jNQXAC9IVRwEXTRA",
        "https://www.youtube.com/@somechannel",
        "https://www.youtube.com/playlist?list=PL123",
        "https://youtu.be/",
        "ftp://youtu.be/jNQXAC9IVRw",
        "https://[broken/watch?v=jNQXAC9IVRw",
    ]
    for url in rejected:
        assert ft.extract_video_id(url) is None, url


def test_sanitize_title():
    assert ft.sanitize_title('A/B: "C"? <D> | E*\\F', "id") == "AB C D EF"
    assert ft.sanitize_title("  spaced\n\tout  ", "id") == "spaced out"
    assert ft.sanitize_title("...", "fallback") == "fallback"
    assert ft.sanitize_title("C# in 100 Seconds [2024] ^x", "id") == "C in 100 Seconds 2024 x"
    assert ft.sanitize_title("x" * 400, "id") == "x" * ft.MAX_TITLE_BYTES
    cjk = ft.sanitize_title("日本語のタイトル" * 30, "id")
    assert len(cjk.encode()) <= ft.MAX_TITLE_BYTES and cjk.startswith("日本語")
    emoji = ft.sanitize_title("🎬" * 100, "id")
    assert emoji == "🎬" * (ft.MAX_TITLE_BYTES // 4)
    longest = f"{ft.NOTE_PREFIX}{cjk} ({VIDEO_ID}).md"
    assert len(longest.encode()) <= 255


def test_resolve_save_dir():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ.pop(ft.SAVE_DIR_ENV, None)
        assert ft.resolve_save_dir(None) == (None, None)
        os.environ[ft.SAVE_DIR_ENV] = tmp
        assert ft.resolve_save_dir(None) == (Path(tmp).resolve(), None)
        missing = str(Path(tmp) / "missing")
        assert ft.resolve_save_dir(missing)[0] is None
        assert "--save-dir" in (ft.resolve_save_dir(missing)[1] or "")
        os.environ[ft.SAVE_DIR_ENV] = missing
        assert ft.SAVE_DIR_ENV in (ft.resolve_save_dir(None)[1] or "")
        os.environ[ft.SAVE_DIR_ENV] = "   "
        assert ft.resolve_save_dir(None) == (None, None)
        os.environ.pop(ft.SAVE_DIR_ENV, None)


def test_note_path_reuses_same_video_note():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        plain = folder / "YouTube - Me at the zoo.md"
        assert ft.note_path_for(folder, "Me at: the zoo", VIDEO_ID) == (plain, False)
        plain.write_text(f"**URL:** https://www.youtube.com/watch?v={VIDEO_ID}\n")
        for _ in range(3):
            assert ft.note_path_for(folder, "Me at: the zoo", VIDEO_ID) == (plain, True)
        assert sorted(p.name for p in folder.iterdir()) == [plain.name]


def test_note_path_adds_id_when_another_video_owns_the_name():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        plain = folder / "YouTube - Me at the zoo.md"
        plain.write_text("**URL:** https://www.youtube.com/watch?v=otherVideo1\n")
        suffixed = folder / f"YouTube - Me at the zoo ({VIDEO_ID}).md"
        assert ft.note_path_for(folder, "Me at the zoo", VIDEO_ID) == (suffixed, False)
        suffixed.write_text("summary")
        assert ft.note_path_for(folder, "Me at the zoo", VIDEO_ID) == (suffixed, True)
        plain.unlink()
        assert ft.note_path_for(folder, "Me at the zoo", VIDEO_ID) == (suffixed, True)


def test_dash_leading_id_parses_with_equals_form():
    out = io.StringIO()
    with redirect_stdout(out):
        code = ft.main(["--url=-not-a-url!"])
    assert code == ft.EXIT_USAGE
    assert json.loads(out.getvalue())["status"] == "error"


def test_note_path_ignores_id_outside_url_line():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        plain = folder / "YouTube - Talk.md"
        plain.write_text(
            "**URL:** https://www.youtube.com/watch?v=otherVideo1\n"
            f"## Related\n- https://www.youtube.com/watch?v={VIDEO_ID}\n",
        )
        suffixed = folder / f"YouTube - Talk ({VIDEO_ID}).md"
        assert ft.note_path_for(folder, "Talk", VIDEO_ID) == (suffixed, False)


def test_broken_caption_file_reports_json_error():
    class BrokenTranscript:
        def fetch(self):
            raise ParseError("no element found: line 1, column 0")

    class FakeList:
        def find_transcript(self, _languages):
            return BrokenTranscript()

    original = ft.YouTubeTranscriptApi.list
    ft.YouTubeTranscriptApi.list = lambda _self, _video_id: FakeList()
    try:
        out = io.StringIO()
        with redirect_stdout(out):
            code = ft.main(["--url", VIDEO_ID])
    finally:
        ft.YouTubeTranscriptApi.list = original
    payload = json.loads(out.getvalue())
    assert code == ft.EXIT_FAILURE
    assert payload["status"] == "error" and "ParseError" in payload["error"]


def test_build_chapters():
    snippets = [SimpleNamespace(text=t, start=s) for t, s in [("a" * 200, 0.0), (" \n", 5.0), ("b" * 100, 65.0), ("c", 3700.0)]]
    assert ft.build_chapters(snippets) == [f"[0:00] {'a' * 200} {'b' * 100}", "[1:01:40] c"]


def test_invalid_url_exits_2_without_network():
    out = io.StringIO()
    with redirect_stdout(out):
        code = ft.main(["--url", "https://example.com/nope"])
    payload = json.loads(out.getvalue())
    assert code == ft.EXIT_USAGE
    assert payload["status"] == "error" and "Not a YouTube video" in payload["error"]


def test_describe_error_falls_back_to_type_name():
    assert ft.describe_error(RuntimeError("boom\nmore")) == "Could not fetch the transcript (RuntimeError: boom)"
    assert ft.describe_error(RuntimeError()) == "Could not fetch the transcript (RuntimeError)"
    failed = YouTubeRequestFailed(VIDEO_ID, requests.HTTPError("429 Too Many Requests"))
    assert ft.describe_error(failed) == (
        "Could not fetch the transcript (YouTubeRequestFailed: Request to YouTube failed: 429 Too Many Requests)"
    )
    assert ft.describe_error(TranscriptsDisabled(VIDEO_ID)) == "Transcripts are disabled for this video"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
