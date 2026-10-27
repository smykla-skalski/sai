#!/usr/bin/env python3
"""Find, set and list the folder that holds smallsteps idea notes.

Usage:
    python3 scripts/notes.py where --project DIR      print the folder for new notes
    python3 scripts/notes.py set PLACE --project DIR  save the place
    python3 scripts/notes.py list --project DIR       list notes and next actions

DIR is the user's project folder (the agent's working folder), not this skill's
folder. It is needed only for the ideas place.

Places:
    shared   <data folder>/ideas/, the default; works from any repository
    ideas    ideas/ at the top of the git repository that holds DIR, or in DIR
             outside git
    /path    any absolute folder, such as a folder in an Obsidian vault;
             a leading ~ is expanded

The data folder is ${XDG_DATA_HOME:-$HOME/.local/share}/sai/smallsteps. The
chosen place is one line in its notes-dir file; a missing file means shared.

Output: one JSON object on stdout. On success "status" is "ok"; on bad input
"status" is "error" with an "error" message.

Exit codes: 0 ok, 2 invalid input or setting.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Final

PLUGIN_NAME: Final[str] = "smallsteps"
SETTING_FILE: Final[str] = "notes-dir"
SHARED: Final[str] = "shared"
REPO: Final[str] = "ideas"
EXIT_OK: Final[int] = 0
EXIT_INVALID: Final[int] = 2
STATUS_LINE: Final[re.Pattern[str]] = re.compile(
    r"^Step (?P<step>\d) of 4 \| Next action: (?P<next>.*?)"
    r" \| Updated: (?P<updated>\S+)\s*$",
    re.MULTILINE,
)


class InvalidPlaceError(ValueError):
    """The place is not shared, ideas or an absolute folder, or cannot resolve."""


def data_dir() -> Path:
    """Return the plugin's data folder, following the XDG base directory spec."""
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg and Path(xdg).is_absolute():
        return Path(xdg) / "sai" / PLUGIN_NAME
    return Path.home() / ".local" / "share" / "sai" / PLUGIN_NAME


def repo_root(project: Path) -> Path:
    """Return the top of the git work tree that holds project, else project.

    A work tree's top holds a .git directory, or a .git file in a linked
    worktree or a submodule.
    """
    for folder in (project, *project.parents):
        if (folder / ".git").exists():
            return folder
    return project


def normalize_place(place: str) -> str:
    """Return the place as stored in the setting file, or raise InvalidPlaceError."""
    place = place.strip()
    if place in (SHARED, REPO):
        return place
    path = Path(place).expanduser()
    if not path.is_absolute():
        msg = f"place must be {SHARED}, {REPO} or an absolute folder, not {place!r}"
        raise InvalidPlaceError(msg)
    return str(path)


def resolve(place: str, project: Path | None) -> Path:
    """Return the notes folder for a stored place."""
    if place == SHARED:
        return data_dir() / "ideas"
    if place == REPO:
        if project is None:
            msg = f"the {REPO} place needs --project with the user's project folder"
            raise InvalidPlaceError(msg)
        return repo_root(project) / "ideas"
    return Path(place)


def read_place() -> tuple[str, str]:
    """Return the stored place and its source: "setting" or "default"."""
    setting = data_dir() / SETTING_FILE
    if not setting.is_file():
        return SHARED, "default"
    text = setting.read_text(encoding="utf-8", errors="replace")
    return normalize_place(text), "setting"


def describe(place: str, source: str, project: Path | None) -> dict[str, object]:
    """Return the JSON result for a place."""
    folder = resolve(place, project)
    return {
        "status": "ok",
        "dir": str(folder),
        "place": place,
        "source": source,
        "exists": folder.is_dir(),
        "setting_file": str(data_dir() / SETTING_FILE),
    }


def command_where(project: Path | None) -> dict[str, object]:
    """Return where new notes go."""
    place, source = read_place()
    return describe(place, source, project)


def command_set(raw_place: str, project: Path | None) -> dict[str, object]:
    """Save the place, create its folder and return where new notes go."""
    place = normalize_place(raw_place)
    folder = resolve(place, project)
    folder.mkdir(parents=True, exist_ok=True)
    setting = data_dir() / SETTING_FILE
    setting.parent.mkdir(parents=True, exist_ok=True)
    setting.write_text(place + "\n", encoding="utf-8")
    return describe(place, "setting", project)


def note_summary(note: Path) -> dict[str, object]:
    """Return a note's name, path and the parts of its status line."""
    text = note.read_text(encoding="utf-8", errors="replace")
    match = STATUS_LINE.search(text)
    return {
        "name": note.stem,
        "path": str(note),
        "step": int(match["step"]) if match else None,
        "next_action": match["next"].strip() if match else None,
        "updated": match["updated"] if match else None,
    }


def command_list(project: Path | None) -> dict[str, object]:
    """Return where notes go and a summary of each note there."""
    result = command_where(project)
    folder = Path(str(result["dir"]))
    notes = sorted(folder.glob("*.md")) if folder.is_dir() else []
    result["notes"] = [note_summary(note) for note in notes]
    return result


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Find, set and list the smallsteps notes folder"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    project = argparse.ArgumentParser(add_help=False)
    project.add_argument("--project", type=Path, help="the user's project folder")
    commands.add_parser(
        "where", parents=[project], help="print the folder where new notes go"
    )
    set_parser = commands.add_parser(
        "set",
        parents=[project],
        help="save the place: shared, ideas or an absolute folder",
    )
    set_parser.add_argument("place")
    commands.add_parser(
        "list", parents=[project], help="print each note's name, step and next action"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one command and print its JSON result."""
    args = parse_args(argv)
    project = args.project.expanduser().resolve() if args.project else None
    try:
        if args.command == "where":
            result = command_where(project)
        elif args.command == "set":
            result = command_set(args.place, project)
        else:
            result = command_list(project)
    except InvalidPlaceError as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return EXIT_INVALID
    print(json.dumps(result))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
