"""End-to-end tests for the plugin version bump pre-commit hook.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".githooks"
SCRIPT = REPO_ROOT / "scripts" / "bump_plugin_versions.py"
GIT = shutil.which("git") or "git"

_spec = importlib.util.spec_from_file_location("bump_plugin_versions", SCRIPT)
assert _spec is not None
assert _spec.loader is not None
bump = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bump
_spec.loader.exec_module(bump)

CLAUDE_MANIFEST = "claude/alpha/.claude-plugin/plugin.json"
PORTABLE_ROOT_MANIFEST = "plugins/beta/plugin.json"
PORTABLE_CLAUDE_MANIFEST = "plugins/beta/.claude-plugin/plugin.json"
CODEX_MANIFEST = "plugins/gamma/.codex-plugin/plugin.json"


def manifest(name: str, version: str, **extra: object) -> str:
    return json.dumps({"name": name, "version": version, **extra}, indent=2) + "\n"


class HookRepo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "GIT_AUTHOR_DATE": "@1790000000 +0000",
                "GIT_COMMITTER_DATE": "@1790000000 +0000",
            },
        )
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.hooksPath", str(HOOKS_DIR))

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [GIT, *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed:\n{result.stderr}")
        return result

    def write(self, path: str, content: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")

    def commit_all(self, message: str = "change") -> subprocess.CompletedProcess[str]:
        self.git("add", "-A")
        return self.git("commit", "-q", "-m", message, check=False)

    def committed_version(self, path: str) -> str:
        return str(json.loads(self.git("show", f"HEAD:{path}").stdout)["version"])

    def staged_version(self, path: str) -> str:
        return str(json.loads(self.git("show", f":{path}").stdout)["version"])

    def disk_version(self, path: str) -> str:
        return str(json.loads(self.read(path))["version"])

    def status(self) -> str:
        return self.git("status", "--porcelain").stdout


class BumpHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = HookRepo(Path(self.tmp.name))
        self.repo.write("README.md", "# repo\n")
        self.repo.write(CLAUDE_MANIFEST, manifest("alpha", "1.2.3"))
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v1\n")
        self.repo.write("claude/alpha/README.md", "alpha docs\n")
        self.repo.write(
            PORTABLE_ROOT_MANIFEST,
            '{\n  "name": "beta",\n  "version": "0.4.0",\n'
            '  "keywords": ["a", "b"],\n  "extensions": {"x": {"version": "9.9.9"}}\n}\n',
        )
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.4.0"))
        self.repo.write("plugins/beta/skills/beta/SKILL.md", "beta v1\n")
        self.repo.write(
            CODEX_MANIFEST,
            manifest("gamma", "2.0.0", skills="../../codex/gamma"),
        )
        self.repo.write("codex/gamma/SKILL.md", "gamma v1\n")
        result = self.repo.commit_all("initial")
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def assert_commit_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bumps_patch_of_changed_claude_plugin(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.disk_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.0")
        self.assertEqual(self.repo.committed_version(CODEX_MANIFEST), "2.0.0")
        self.assertEqual(self.repo.status(), "")

    def test_bumps_every_manifest_of_portable_plugin_and_keeps_formatting(
        self,
    ) -> None:
        before = self.repo.read(PORTABLE_ROOT_MANIFEST)
        self.repo.write("plugins/beta/skills/beta/SKILL.md", "beta v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.1")
        self.assertEqual(
            self.repo.committed_version(PORTABLE_CLAUDE_MANIFEST),
            "0.4.1",
        )
        self.assertEqual(
            self.repo.read(PORTABLE_ROOT_MANIFEST),
            before.replace('"version": "0.4.0"', '"version": "0.4.1"'),
        )
        self.assertEqual(self.repo.status(), "")

    def test_skills_directory_outside_plugin_dir_counts(self) -> None:
        self.repo.write("codex/gamma/SKILL.md", "gamma v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CODEX_MANIFEST), "2.0.1")
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.3")

    def test_bumps_each_changed_plugin_once(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.repo.write("codex/gamma/SKILL.md", "gamma v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.committed_version(CODEX_MANIFEST), "2.0.1")
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.0")

    def test_leaves_manual_bump_alone(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.repo.write(CLAUDE_MANIFEST, manifest("alpha", "1.3.0"))
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.3.0")

    def test_manual_bump_of_one_manifest_syncs_the_other(self) -> None:
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.5.0"))
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.5.0")
        self.assertEqual(
            self.repo.committed_version(PORTABLE_CLAUDE_MANIFEST),
            "0.5.0",
        )
        self.assertEqual(self.repo.status(), "")

    def test_mismatched_manifests_converge_on_bump(self) -> None:
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.3.9"))
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "drift")
        self.repo.write("plugins/beta/skills/beta/SKILL.md", "beta v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.1")
        self.assertEqual(
            self.repo.committed_version(PORTABLE_CLAUDE_MANIFEST),
            "0.4.1",
        )

    def test_commit_without_plugin_files_is_untouched(self) -> None:
        self.repo.write("README.md", "# repo v2\n")
        self.repo.write("scripts/tool.py", "print(1)\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(
            self.repo.git("show", "--name-only", "--format=", "HEAD").stdout.split(),
            ["README.md", "scripts/tool.py"],
        )

    def test_readme_only_change_does_not_bump(self) -> None:
        self.repo.write("claude/alpha/README.md", "alpha docs v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.3")

    def test_new_plugin_is_not_bumped(self) -> None:
        self.repo.write(
            "claude/delta/.claude-plugin/plugin.json", manifest("delta", "1.0.0")
        )
        self.repo.write("claude/delta/skills/delta/SKILL.md", "delta\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(
            self.repo.committed_version("claude/delta/.claude-plugin/plugin.json"),
            "1.0.0",
        )

    def test_deleted_plugin_passes(self) -> None:
        self.repo.git("rm", "-r", "-q", "claude/alpha")
        result = self.repo.git("commit", "-q", "-m", "drop", check=False)
        self.assert_commit_ok(result)

    def test_unstaged_manifest_edits_stay_unstaged(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.repo.git("add", "claude/alpha/skills/alpha/SKILL.md")
        self.repo.write(
            CLAUDE_MANIFEST,
            manifest("alpha", "1.2.3", description="work in progress"),
        )
        result = self.repo.git("commit", "-q", "-m", "change", check=False)
        self.assert_commit_ok(result)
        committed = json.loads(self.repo.git("show", f"HEAD:{CLAUDE_MANIFEST}").stdout)
        self.assertEqual(committed, {"name": "alpha", "version": "1.2.4"})
        on_disk = json.loads(self.repo.read(CLAUDE_MANIFEST))
        self.assertEqual(on_disk["version"], "1.2.4")
        self.assertEqual(on_disk["description"], "work in progress")
        self.assertEqual(self.repo.status().strip(), f"M {CLAUDE_MANIFEST}")

    def test_commit_all_flag_bumps(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        result = self.repo.git("commit", "-q", "-a", "-m", "change", check=False)
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.status(), "")

    def test_commit_with_pathspec_is_rejected_with_hint(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        result = self.repo.git(
            "commit",
            "-q",
            "-m",
            "change",
            "--",
            "claude/alpha/skills/alpha/SKILL.md",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git commit <paths>", result.stderr)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.3")

    def test_invalid_version_blocks_commit(self) -> None:
        for version in ("next", "1.2.03", "1.2"):
            with self.subTest(version=version):
                self.repo.write(CLAUDE_MANIFEST, manifest("alpha", version))
                result = self.repo.commit_all()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("expected MAJOR.MINOR.PATCH", result.stderr)

    def test_second_commit_bumps_again(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v3\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.5")

    def test_merge_commit_is_skipped(self) -> None:
        self.repo.git("checkout", "-q", "-b", "side")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "side\n")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "side")
        self.repo.git("checkout", "-q", "main")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "main\n")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "main")
        self.repo.git("merge", "-q", "side", check=False)
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "resolved\n")
        self.repo.git("add", "-A")
        result = self.repo.git("commit", "-q", "--no-edit", check=False)
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.3")

    def test_amend_does_not_bump_twice(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2 fixed\n")
        self.repo.git("add", "-A")
        result = self.repo.git("commit", "-q", "--amend", "--no-edit", check=False)
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.status(), "")

    def test_amend_bumps_plugin_new_to_the_commit(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.repo.write("codex/gamma/SKILL.md", "gamma v2\n")
        self.repo.git("add", "-A")
        result = self.repo.git("commit", "-q", "--amend", "--no-edit", check=False)
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.assertEqual(self.repo.committed_version(CODEX_MANIFEST), "2.0.1")

    def test_message_mentioning_amend_is_a_normal_commit(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v3\n")
        self.assert_commit_ok(self.repo.commit_all("fix --amend handling"))
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.5")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v4\n")
        self.assert_commit_ok(self.repo.commit_all("--amend"))
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.6")

    def test_amend_with_new_author_date_does_not_bump_twice(self) -> None:
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2 fixed\n")
        self.repo.git("add", "-A")
        result = self.repo.git(
            "commit",
            "-q",
            "--reset-author",
            "--date=@1800000000 +0000",
            "--amend",
            "--no-edit",
            check=False,
        )
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")

    def test_amend_through_alias_does_not_bump_twice(self) -> None:
        self.repo.git("config", "alias.fix", "commit --amend --no-edit")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2 fixed\n")
        self.repo.git("add", "-A")
        self.assert_commit_ok(self.repo.git("fix", "-q", check=False))
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")

    def test_moving_claude_plugin_into_plugins_bumps_past_both(self) -> None:
        self.repo.write(
            "plugins/alpha/.codex-plugin/plugin.json",
            manifest("alpha", "0.1.0"),
        )
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "codex alpha")
        self.repo.git(
            "mv", "claude/alpha/.claude-plugin", "plugins/alpha/.claude-plugin"
        )
        self.repo.git("mv", "claude/alpha/skills", "plugins/alpha/skills")
        self.repo.write("plugins/alpha/skills/alpha/SKILL.md", "alpha moved\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(
            self.repo.committed_version("plugins/alpha/.claude-plugin/plugin.json"),
            "1.2.4",
        )
        self.assertEqual(
            self.repo.committed_version("plugins/alpha/.codex-plugin/plugin.json"),
            "1.2.4",
        )

    def test_same_name_plugin_elsewhere_is_ignored(self) -> None:
        self.repo.write(
            "plugins/alpha/.codex-plugin/plugin.json",
            manifest("alpha", "0.1.0"),
        )
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "codex alpha")
        self.repo.write("plugins/alpha/skills/alpha/SKILL.md", "codex only\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(
            self.repo.committed_version("plugins/alpha/.codex-plugin/plugin.json"),
            "0.1.1",
        )
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.3")

    def test_unstaged_sync_leaves_nested_version_alone(self) -> None:
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.4.1"))
        self.repo.git("add", PORTABLE_CLAUDE_MANIFEST)
        unstaged = (
            '{\n  "name": "beta",\n  "version": "0.4.1",\n'
            '  "keywords": ["a", "b"],\n  "extensions": {"x": {"version": "0.4.0"}}\n}\n'
        )
        self.repo.write(PORTABLE_ROOT_MANIFEST, unstaged)
        result = self.repo.git("commit", "-q", "-m", "bump", check=False)
        self.assert_commit_ok(result)
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.1")
        self.assertEqual(self.repo.read(PORTABLE_ROOT_MANIFEST), unstaged)

    def test_deleted_manifest_with_odd_name_does_not_crash(self) -> None:
        self.repo.write(
            "claude/delta/.claude-plugin/plugin.json",
            json.dumps({"name": [], "version": "1.0.0"}),
        )
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "delta")
        self.repo.git("rm", "-r", "-q", "claude/delta")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")

    def test_crlf_manifest_keeps_line_endings(self) -> None:
        crlf = manifest("alpha", "1.2.3").replace("\n", "\r\n")
        (self.repo.root / CLAUDE_MANIFEST).write_bytes(crlf.encode())
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "crlf")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(
            (self.repo.root / CLAUDE_MANIFEST).read_bytes(),
            crlf.replace("1.2.3", "1.2.4").encode(),
        )
        self.assertEqual(self.repo.status(), "")

    def test_partial_manual_sync_of_drifted_manifests_still_bumps(self) -> None:
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.3.9"))
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "drift")
        self.repo.write("plugins/beta/skills/beta/SKILL.md", "beta v2\n")
        self.repo.write(PORTABLE_CLAUDE_MANIFEST, manifest("beta", "0.4.0"))
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(PORTABLE_ROOT_MANIFEST), "0.4.1")
        self.assertEqual(
            self.repo.committed_version(PORTABLE_CLAUDE_MANIFEST),
            "0.4.1",
        )

    def test_broken_manifest_only_blocks_its_own_plugin(self) -> None:
        self.repo.write(CODEX_MANIFEST, "{not json\n")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "break gamma")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        self.assertEqual(self.repo.committed_version(CLAUDE_MANIFEST), "1.2.4")
        self.repo.write("plugins/gamma/extra.md", "x\n")
        result = self.repo.commit_all()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not valid JSON", result.stderr)

    def test_manifest_with_bom_is_bumped(self) -> None:
        self.repo.write(CLAUDE_MANIFEST, "﻿" + manifest("alpha", "1.2.3"))
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "--no-verify", "-m", "bom")
        self.repo.write("claude/alpha/skills/alpha/SKILL.md", "alpha v2\n")
        self.assert_commit_ok(self.repo.commit_all())
        committed = self.repo.git("show", f"HEAD:{CLAUDE_MANIFEST}").stdout
        self.assertTrue(committed.startswith("﻿"))
        self.assertEqual(json.loads(committed.lstrip("﻿"))["version"], "1.2.4")


class AmendRequestedTest(unittest.TestCase):
    def test_parses_commit_options(self) -> None:
        cases = [
            (["--amend"], True),
            (["--am"], True),
            (["-a", "--amend"], True),
            (["-SDEADBEEF", "--amend"], True),
            (["-uno", "--amend"], True),
            (["--reset-author", "--amend", "--no-edit"], True),
            (["--amend", "--no-amend"], False),
            (["-m", "--amend"], False),
            (["-am", "--amend"], False),
            (["-mfix", "--amend"], True),
            (["--author", "--amend"], False),
            (["--message=--amend"], False),
            (["-m", "fix --amend"], False),
            (["--", "--amend"], False),
            ([], False),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertIs(bump.amend_requested(["git", "commit", *args]), expected)

    def test_skips_git_global_options(self) -> None:
        argv = ["git", "-c", "x=commit", "-C", "commit", "commit", "--amend"]
        self.assertTrue(bump.amend_requested(argv))
        self.assertFalse(bump.amend_requested(["git", "status", "--amend"]))


if __name__ == "__main__":
    unittest.main()
