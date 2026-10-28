"""Check where the smallsteps notes script puts idea notes.

The script decides the notes folder for every agent harness, so a wrong path
loses notes or scatters them. Each test runs the script as the skill does, with
its own HOME and XDG_DATA_HOME.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "smallsteps"
    / "skills"
    / "smallsteps"
    / "scripts"
    / "notes.py"
)
EXIT_INVALID = 2


class NotesScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.home = self.tmp / "home"
        self.xdg = self.tmp / "xdg"
        self.home.mkdir()
        self.project = self.tmp / "work" / "app"
        self.project.mkdir(parents=True)

    def run_script(
        self, *args: str, xdg: str | None = None
    ) -> tuple[int, dict[str, Any]]:
        env = {k: v for k, v in os.environ.items() if k != "XDG_DATA_HOME"}
        env["HOME"] = str(self.home)
        env["XDG_DATA_HOME"] = str(self.xdg) if xdg is None else xdg
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.tmp,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return proc.returncode, json.loads(proc.stdout)

    def setting(self) -> Path:
        return self.xdg / "sai" / "smallsteps" / "notes-dir"

    def test_default_is_the_shared_folder_without_a_setting(self) -> None:
        code, out = self.run_script("where")
        self.assertEqual(code, 0)
        self.assertEqual(out["dir"], str(self.xdg / "sai" / "smallsteps" / "ideas"))
        self.assertEqual(out["source"], "default")
        self.assertFalse(out["exists"])

    def test_unset_or_relative_xdg_data_home_falls_back_to_home(self) -> None:
        expected = str(self.home / ".local" / "share" / "sai" / "smallsteps" / "ideas")
        for value in ("", "relative/data"):
            with self.subTest(xdg=value):
                _, out = self.run_script("where", xdg=value)
                self.assertEqual(out["dir"], expected)

    def test_ideas_place_uses_the_repository_top(self) -> None:
        repo = self.tmp / "work"
        (repo / ".git").mkdir()
        code, out = self.run_script("set", "ideas", "--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertEqual(out["dir"], str(repo / "ideas"))
        self.assertTrue((repo / "ideas").is_dir())
        self.assertEqual(self.setting().read_text(), "ideas\n")
        _, again = self.run_script("where", "--project", str(self.project))
        self.assertEqual(again["dir"], str(repo / "ideas"))
        self.assertEqual(again["source"], "setting")

    def test_ideas_place_finds_a_linked_worktree_by_its_git_file(self) -> None:
        (self.project / ".git").write_text("gitdir: /elsewhere/.git/worktrees/app\n")
        _, out = self.run_script("set", "ideas", "--project", str(self.project))
        self.assertEqual(out["dir"], str(self.project / "ideas"))

    def test_ideas_place_outside_git_uses_the_project_folder(self) -> None:
        _, out = self.run_script("set", "ideas", "--project", str(self.project))
        self.assertEqual(out["dir"], str(self.project / "ideas"))

    def test_ideas_place_without_project_is_an_error(self) -> None:
        self.run_script("set", "ideas", "--project", str(self.project))
        code, out = self.run_script("where")
        self.assertEqual(code, EXIT_INVALID)
        self.assertEqual(out["status"], "error")
        self.assertIn("--project", str(out["error"]))

    def test_absolute_folder_such_as_a_vault_is_saved_and_created(self) -> None:
        vault = self.tmp / "vault" / "Ideas"
        code, out = self.run_script("set", str(vault))
        self.assertEqual(code, 0)
        self.assertEqual(out["dir"], str(vault))
        self.assertTrue(vault.is_dir())
        self.assertEqual(self.setting().read_text(), f"{vault}\n")

    def test_tilde_folder_expands_to_home(self) -> None:
        _, out = self.run_script("set", "~/vault/Ideas")
        self.assertEqual(out["dir"], str(self.home / "vault" / "Ideas"))

    def test_relative_folder_is_refused_and_not_saved(self) -> None:
        code, out = self.run_script("set", "notes")
        self.assertEqual(code, EXIT_INVALID)
        self.assertEqual(out["status"], "error")
        self.assertFalse(self.setting().exists())

    def test_broken_setting_is_reported_not_guessed(self) -> None:
        self.setting().parent.mkdir(parents=True)
        self.setting().write_text("notes\n")
        code, out = self.run_script("where")
        self.assertEqual(code, EXIT_INVALID)
        self.assertEqual(out["status"], "error")

    def test_shared_after_ideas_goes_back_to_the_shared_folder(self) -> None:
        self.run_script("set", "ideas", "--project", str(self.project))
        _, out = self.run_script("set", "shared")
        self.assertEqual(out["dir"], str(self.xdg / "sai" / "smallsteps" / "ideas"))

    def test_list_reads_each_note_status_line(self) -> None:
        folder = self.xdg / "sai" / "smallsteps" / "ideas"
        folder.mkdir(parents=True)
        (folder / "link-finder.md").write_text(
            "# Link finder\n\n"
            "Step 3 of 4 | Next action: Open the notes app | Updated: 2026-10-20\n"
        )
        (folder / "draft.md").write_text("# Draft without a status line\n")
        (folder / "board.png").write_bytes(b"\x89PNG")
        code, out = self.run_script("list")
        self.assertEqual(code, 0)
        notes = {note["name"]: note for note in out["notes"]}
        self.assertEqual(sorted(notes), ["draft", "link-finder"])
        self.assertEqual(notes["link-finder"]["step"], 3)
        self.assertEqual(notes["link-finder"]["next_action"], "Open the notes app")
        self.assertEqual(notes["link-finder"]["updated"], "2026-10-20")
        self.assertIsNone(notes["draft"]["next_action"])

    def test_list_reads_the_next_question_or_the_first_action(self) -> None:
        folder = self.xdg / "sai" / "smallsteps" / "ideas"
        folder.mkdir(parents=True)
        (folder / "asking.md").write_text(
            "# Asking\n\n"
            "Step 2 of 4 | Next question: What are you least sure about?"
            " | Updated: 2026-10-28\n\n"
            "## Now\n\n**First action:** Open the notes app\n"
        )
        (folder / "planned.md").write_text(
            "# Planned\n\n"
            "Step 3 of 4 | Updated: 2026-10-28\n\n"
            "## Now\n\n**Result:** Know if my notes app finds one link\n\n"
            "**First action:** Open the notes app\n"
        )
        _, out = self.run_script("list")
        notes = {note["name"]: note for note in out["notes"]}
        self.assertEqual(
            notes["asking"]["next_action"], "What are you least sure about?"
        )
        self.assertEqual(notes["planned"]["next_action"], "Open the notes app")
        self.assertEqual(notes["planned"]["step"], 3)
        self.assertEqual(notes["planned"]["updated"], "2026-10-28")


if __name__ == "__main__":
    unittest.main()
