#!/usr/bin/env -S uv run --quiet --script
"""Fetch a YouTube transcript and metadata, and resolve where the note goes.

Usage:
    fetch_transcript.py --url URL [--save-dir DIR]

Prints one JSON object to stdout. On success `status` is "ok" and the object
carries the transcript, timestamped chapters and the note location. On failure
`status` is "error" with an `error` message.

The note directory comes from --save-dir, else the YOUTUBE_SUMMARY_DIR
environment variable. When neither is set, `note_path` is null. The script
never writes the note itself.

Dependencies are declared inline (PEP 723) right above the first function, so
`uv run --script` installs them on first use.

Exit codes: 0 ok, 1 transcript failure, 2 invalid input.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Final
from xml.etree.ElementTree import ParseError

import requests
from youtube_transcript_api import (
    AgeRestricted,
    CouldNotRetrieveTranscript,
    InvalidVideoId,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

SAVE_DIR_ENV: Final[str] = "YOUTUBE_SUMMARY_DIR"
NOTE_PREFIX: Final[str] = "YouTube - "
NOTE_URL_LABEL: Final[str] = "**URL:**"
MAX_TITLE_BYTES: Final[int] = 200
CHAPTER_CHARS: Final[int] = 280
HTTP_TIMEOUT_SECONDS: Final[int] = 15
PREFERRED_LANGUAGES: Final[tuple[str, ...]] = ("en", "en-US", "en-GB")
OEMBED_URL: Final[str] = "https://www.youtube.com/oembed"
UNKNOWN_META: Final[dict[str, str]] = {
    "title": "Unknown title",
    "author": "Unknown channel",
}

EXIT_OK: Final[int] = 0
EXIT_FAILURE: Final[int] = 1
EXIT_USAGE: Final[int] = 2

VIDEO_ID_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_-]{11}")
PATH_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"^/(?:embed|shorts|live|v|e)/([A-Za-z0-9_-]{11})/?$",
)
SHORT_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^/([A-Za-z0-9_-]{11})/?$")
UNSAFE_TITLE_RE: Final[re.Pattern[str]] = re.compile(r'[/\\:*?"<>|#^\[\]\x00-\x1f\x7f]')
SPACES_RE: Final[re.Pattern[str]] = re.compile(r"\s+")

YOUTUBE_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    },
)
SHORT_HOSTS: Final[frozenset[str]] = frozenset({"youtu.be", "www.youtu.be"})

ERROR_MESSAGES: Final[tuple[tuple[tuple[type[Exception], ...], str], ...]] = (
    ((TranscriptsDisabled,), "Transcripts are disabled for this video"),
    ((NoTranscriptFound,), "No transcript is available for this video"),
    (
        (VideoUnavailable, InvalidVideoId),
        "The video is unavailable (removed, private or a wrong id)",
    ),
    (
        (AgeRestricted,),
        "The video is age-restricted, so its transcript needs a login",
    ),
    (
        (VideoUnplayable,),
        "The video cannot be played, so it has no fetchable transcript",
    ),
    (
        (IpBlocked, RequestBlocked),
        "YouTube blocked the request from this network; retry later or elsewhere",
    ),
)


# /// script
# requires-python = ">=3.10"
# dependencies = ["youtube-transcript-api>=1.2.0", "requests>=2.31"]
# ///
def extract_video_id(value: str) -> str | None:
    """Return the 11-character video id from a YouTube URL or bare id."""
    value = value.strip()
    if VIDEO_ID_RE.fullmatch(value):
        return value
    if "://" not in value:
        value = "https://" + value
    try:
        parsed = urllib.parse.urlsplit(value)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return None
    candidate = ""
    if parsed.scheme not in ("http", "https"):
        candidate = ""
    elif host in SHORT_HOSTS:
        match = SHORT_PATH_RE.match(parsed.path)
        candidate = match.group(1) if match else ""
    elif host in YOUTUBE_HOSTS and parsed.path in ("/watch", "/watch/"):
        candidate = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
    elif host in YOUTUBE_HOSTS:
        match = PATH_ID_RE.match(parsed.path)
        candidate = match.group(1) if match else ""
    return candidate if VIDEO_ID_RE.fullmatch(candidate) else None


def sanitize_title(title: str, fallback: str) -> str:
    """Make a title safe as a file name on macOS, Linux and Windows.

    Clipped by UTF-8 bytes so prefix, id suffix and extension stay under the
    255-byte NAME_MAX of common Linux file systems.
    """
    cleaned = UNSAFE_TITLE_RE.sub("", clean_text(title))
    cleaned = SPACES_RE.sub(" ", cleaned).strip(" .")
    clipped = cleaned.encode()[:MAX_TITLE_BYTES].decode(errors="ignore")
    cleaned = clipped.strip(" .")
    return cleaned or fallback


def resolve_save_dir(cli_dir: str | None) -> tuple[Path | None, str | None]:
    """Return (directory, error); both are None when no directory is configured."""
    raw = cli_dir if cli_dir is not None else os.environ.get(SAVE_DIR_ENV, "")
    raw = raw.strip()
    if not raw:
        return None, None
    path = Path(raw).expanduser()
    if not path.is_dir():
        source = "--save-dir" if cli_dir is not None else SAVE_DIR_ENV
        return None, f"{source} '{raw}' is not an existing directory"
    return path.resolve(), None


def mentions_video(path: Path, video_id: str) -> bool:
    """Report whether an existing note is a summary of this video."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    marker = f"watch?v={video_id}"
    return any(
        line.lstrip().startswith(NOTE_URL_LABEL) and marker in line
        for line in text.splitlines()
    )


def note_path_for(save_dir: Path, title: str, video_id: str) -> tuple[Path, bool]:
    """Pick the note file and report whether it holds an earlier summary.

    The plain name is reused when it is free or already summarizes this video;
    otherwise the video id is appended so another video's note is never replaced.
    """
    stem = NOTE_PREFIX + sanitize_title(title, video_id)
    plain = save_dir / f"{stem}.md"
    suffixed = save_dir / f"{stem} ({video_id}).md"
    if suffixed.exists():
        return suffixed, True
    if not plain.exists():
        return plain, False
    if mentions_video(plain, video_id):
        return plain, True
    return suffixed, False


def fetch_metadata(video_id: str) -> dict[str, str]:
    """Best-effort title and channel via the public oEmbed endpoint."""
    params = {"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}
    try:
        resp = requests.get(
            OEMBED_URL,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return dict(UNKNOWN_META)
    if not isinstance(data, dict):
        return dict(UNKNOWN_META)
    return {
        "title": str(data.get("title") or UNKNOWN_META["title"]),
        "author": str(data.get("author_name") or UNKNOWN_META["author"]),
    }


def fmt_time(seconds: float) -> str:
    """Format seconds as m:ss or h:mm:ss."""
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def clean_text(text: str) -> str:
    """Collapse all whitespace, including caption line breaks, to single spaces."""
    return SPACES_RE.sub(" ", text).strip()


def build_chapters(snippets: list[Any], chunk_chars: int = CHAPTER_CHARS) -> list[str]:
    """Group snippets into timestamped segments for citing moments."""
    chapters: list[str] = []
    buf: list[str] = []
    buf_start = 0.0
    for snip in snippets:
        text = clean_text(snip.text)
        if not text:
            continue
        if not buf:
            buf_start = snip.start
        buf.append(text)
        if sum(len(t) for t in buf) >= chunk_chars:
            chapters.append(f"[{fmt_time(buf_start)}] {' '.join(buf)}")
            buf = []
    if buf:
        chapters.append(f"[{fmt_time(buf_start)}] {' '.join(buf)}")
    return chapters


def describe_error(exc: Exception) -> str:
    """Turn a transcript library or network error into one clear sentence."""
    for types, message in ERROR_MESSAGES:
        if isinstance(exc, types):
            return message
    text = exc.cause if isinstance(exc, CouldNotRetrieveTranscript) else str(exc)
    lines = text.strip().splitlines()
    detail = f": {lines[0]}" if lines else ""
    return f"Could not fetch the transcript ({type(exc).__name__}{detail})"


def emit(payload: dict[str, Any], code: int) -> int:
    """Print the JSON result and return the exit code."""
    print(json.dumps(payload))
    return code


def fail(message: str, code: int, video_id: str | None = None) -> int:
    """Print an error result and return the exit code."""
    payload: dict[str, Any] = {"status": "error"}
    if video_id:
        payload["video_id"] = video_id
    payload["error"] = message
    return emit(payload, code)


def fetch_snippets(video_id: str) -> tuple[Any, list[Any]]:
    """Return the fetched transcript and its non-empty snippets."""
    transcript_list = YouTubeTranscriptApi().list(video_id)
    try:
        transcript = transcript_list.find_transcript(PREFERRED_LANGUAGES)
    except NoTranscriptFound:
        transcript = next(iter(transcript_list), None)
    if transcript is None:
        raise NoTranscriptFound(video_id, list(PREFERRED_LANGUAGES), transcript_list)
    fetched = transcript.fetch()
    return fetched, [s for s in fetched if clean_text(s.text)]


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(description="Fetch a YouTube transcript as JSON.")
    parser.add_argument("--url", required=True, help="YouTube URL or 11-char video id")
    parser.add_argument("--save-dir", help=f"Note directory; overrides {SAVE_DIR_ENV}")
    args = parser.parse_args(argv)

    video_id = extract_video_id(args.url)
    if not video_id:
        message = f"Not a YouTube video URL or id: '{args.url.strip()}'"
        return fail(message, EXIT_USAGE)

    save_dir, save_dir_error = resolve_save_dir(args.save_dir)

    try:
        fetched, snippets = fetch_snippets(video_id)
    except (
        CouldNotRetrieveTranscript,
        requests.RequestException,
        OSError,
        ParseError,
    ) as exc:
        return fail(describe_error(exc), EXIT_FAILURE, video_id)
    if not snippets:
        return fail("The transcript is empty", EXIT_FAILURE, video_id)

    meta = fetch_metadata(video_id)
    last = snippets[-1]
    duration = last.start + last.duration
    note_path, note_exists = (
        note_path_for(save_dir, meta["title"], video_id) if save_dir else (None, False)
    )

    return emit(
        {
            "status": "ok",
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "title": meta["title"],
            "author": meta["author"],
            "language": fetched.language,
            "is_generated": bool(fetched.is_generated),
            "duration_seconds": round(duration, 1),
            "duration_human": fmt_time(duration),
            "segment_count": len(snippets),
            "save_dir": str(save_dir) if save_dir else None,
            "save_dir_error": save_dir_error,
            "note_path": str(note_path) if note_path else None,
            "note_exists": note_exists,
            "transcript": " ".join(clean_text(s.text) for s in snippets),
            "chapters": build_chapters(snippets),
        },
        EXIT_OK,
    )


if __name__ == "__main__":
    sys.exit(main())
