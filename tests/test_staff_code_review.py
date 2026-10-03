"""staff-code-review: agent/mandate sync and humanize reference lookup.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "staff-code-review"
AGENTS_DIR = PLUGIN_DIR / "agents"
SKILL_DIR = PLUGIN_DIR / "skills" / "staff-code-review"
MANDATES_DIR = SKILL_DIR / "references" / "agents"
LOOKUP_SCRIPT = SKILL_DIR / "scripts" / "find_humanize_refs.py"
FRONTMATTER_FENCE = "---\n"
EXPECTED_AGENTS = frozenset(
    {
        "architecture-design-reviewer",
        "backward-compatibility-reviewer",
        "code-adversary",
        "convention-conformance-reviewer",
        "dead-code-reviewer",
        "performance-scalability-reviewer",
        "reliability-operations-reviewer",
        "review-adversary",
        "security-dependencies-reviewer",
    }
)
HUMANIZE_FILES = ("patterns.md", "elements-of-style.md")
DISPATCH_ROW = re.compile(
    r"^\| (?P<dimension>[^|]+?) \| `council:[^`]+` \| `(?P<reviewer>[a-z-]+)` \|",
    re.MULTILINE,
)


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    front = text[len(FRONTMATTER_FENCE) : end]
    body = text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")
    return front, body


def load_lookup() -> ModuleType:
    spec = importlib.util.spec_from_file_location("find_humanize_refs", LOOKUP_SCRIPT)
    if spec is None or spec.loader is None:
        message = f"cannot load {LOOKUP_SCRIPT}"
        raise ImportError(message)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentMandateSyncTest(unittest.TestCase):
    def test_agent_set_matches_mandate_set(self) -> None:
        agents = {path.stem for path in AGENTS_DIR.glob("*.md")}
        mandates = {path.stem for path in MANDATES_DIR.glob("*.md")}
        self.assertEqual(agents, EXPECTED_AGENTS)
        self.assertEqual(mandates, EXPECTED_AGENTS)

    def test_agent_body_matches_reference_mandate(self) -> None:
        for name in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=name):
                agent = AGENTS_DIR / f"{name}.md"
                _, body = split_frontmatter(agent.read_text(encoding="utf-8"))
                mandate = (MANDATES_DIR / f"{name}.md").read_text(encoding="utf-8")
                self.assertEqual(
                    body,
                    mandate,
                    f"edit agents/{name}.md body and its mandate together",
                )

    def test_frontmatter_is_portable(self) -> None:
        for name in sorted(EXPECTED_AGENTS):
            with self.subTest(agent=name):
                front, _ = split_frontmatter(
                    (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
                )
                keys = {line.split(":", 1)[0] for line in front.splitlines()}
                self.assertEqual(keys, {"name", "description", "tools"})
                self.assertIn(f"name: {name}", front.splitlines())

    def test_dispatch_dimensions_match_reviewer_headers(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        rows = {rev: dim for dim, rev in DISPATCH_ROW.findall(skill)}
        reviewers = {name for name in EXPECTED_AGENTS if name.endswith("-reviewer")}
        self.assertEqual(set(rows), reviewers)
        for name, dimension in sorted(rows.items()):
            with self.subTest(reviewer=name):
                agent = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
                self.assertIn(f"`## {dimension} review`", agent)


class HumanizeLookupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.lookup = load_lookup()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_refs(self, directory: Path) -> Path:
        directory.mkdir(parents=True)
        for name in HUMANIZE_FILES:
            (directory / name).write_text("x", encoding="utf-8")
        return directory

    def make_skill(self, skill_dir: Path) -> Path:
        skill_dir.mkdir(parents=True)
        return skill_dir

    def run_lookup(self, skill_dir: Path) -> dict[str, Any]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = self.lookup.main(["--skill-dir", str(skill_dir)])
        self.assertEqual(code, 0)
        return json.loads(out.getvalue())

    def test_layouts(self) -> None:
        layouts = {
            "portable checkout": (
                "plugins/staff-code-review/skills/staff-code-review",
                "plugins/humanize/skills/humanize/references",
            ),
            "copilot install": (
                "sai/staff-code-review/skills/staff-code-review",
                "sai/humanize/skills/humanize/references",
            ),
            "versioned cache": (
                "sai/staff-code-review/1.10.0/skills/staff-code-review",
                "sai/humanize/2.5.10/skills/humanize/references",
            ),
            "flat skills dir": (
                "skills/staff-code-review",
                "skills/humanize/references",
            ),
        }
        for label, (skill, refs) in layouts.items():
            with self.subTest(layout=label):
                base = self.root / label.replace(" ", "-")
                skill_dir = self.make_skill(base / skill)
                refs_dir = self.make_refs(base / refs)
                record = self.run_lookup(skill_dir)
                self.assertTrue(record["found"])
                self.assertEqual(
                    record["patterns"], str((refs_dir / "patterns.md").resolve())
                )

    def test_highest_cached_version_wins(self) -> None:
        skill_dir = self.make_skill(
            self.root / "sai/staff-code-review/1.0.0/skills/staff-code-review"
        )
        self.make_refs(self.root / "sai/humanize/2.5.9/skills/humanize/references")
        newest = self.make_refs(
            self.root / "sai/humanize/2.5.10/skills/humanize/references"
        )
        record = self.run_lookup(skill_dir)
        self.assertEqual(
            record["elements_of_style"],
            str((newest / "elements-of-style.md").resolve()),
        )

    def test_symlinked_skill_falls_back_to_real_tree(self) -> None:
        real = self.make_skill(
            self.root / "repo/plugins/staff-code-review/skills/staff-code-review"
        )
        refs = self.make_refs(
            self.root / "repo/plugins/humanize/skills/humanize/references"
        )
        link_parent = self.root / "home/.config/opencode/skills"
        link_parent.mkdir(parents=True)
        link = link_parent / "staff-code-review"
        link.symlink_to(real, target_is_directory=True)
        record = self.run_lookup(link)
        self.assertEqual(record["patterns"], str((refs / "patterns.md").resolve()))

    def test_orphaned_cache_version_is_skipped(self) -> None:
        skill_dir = self.make_skill(
            self.root / "sai/staff-code-review/1.0.0/skills/staff-code-review"
        )
        live = self.make_refs(
            self.root / "sai/humanize/2.5.2/skills/humanize/references"
        )
        self.make_refs(self.root / "sai/humanize/2.6.0/skills/humanize/references")
        (self.root / "sai/humanize/2.6.0/.orphaned_at").write_text(
            "1", encoding="utf-8"
        )
        record = self.run_lookup(skill_dir)
        self.assertEqual(record["patterns"], str((live / "patterns.md").resolve()))

    def test_unreadable_plugin_dir_reports_not_found(self) -> None:
        skill_dir = self.make_skill(
            self.root / "sai/staff-code-review/1.0.0/skills/staff-code-review"
        )
        locked = self.root / "sai/humanize"
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        record = self.run_lookup(skill_dir)
        self.assertFalse(record["found"])

    def test_unreadable_version_dir_is_skipped(self) -> None:
        skill_dir = self.make_skill(
            self.root / "sai/staff-code-review/1.0.0/skills/staff-code-review"
        )
        live = self.make_refs(
            self.root / "sai/humanize/2.5.2/skills/humanize/references"
        )
        locked = self.root / "sai/humanize/9.9.9"
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        record = self.run_lookup(skill_dir)
        self.assertEqual(record["patterns"], str((live / "patterns.md").resolve()))

    def test_unreadable_reference_file_is_skipped(self) -> None:
        skill_dir = self.make_skill(
            self.root / "plugins/staff-code-review/skills/staff-code-review"
        )
        refs = self.make_refs(self.root / "plugins/humanize/skills/humanize/references")
        (refs / "patterns.md").chmod(0)
        self.addCleanup((refs / "patterns.md").chmod, 0o644)
        record = self.run_lookup(skill_dir)
        self.assertFalse(record["found"])

    def test_skill_dir_under_unreadable_parent_is_usage_error(self) -> None:
        locked = self.root / "locked"
        (locked / "skill").mkdir(parents=True)
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        self.assertEqual(self.lookup.main(["--skill-dir", str(locked / "skill")]), 2)

    def test_partial_references_are_skipped(self) -> None:
        skill_dir = self.make_skill(
            self.root / "plugins/staff-code-review/skills/staff-code-review"
        )
        partial = self.root / "plugins/humanize/skills/humanize/references"
        partial.mkdir(parents=True)
        (partial / "patterns.md").write_text("x", encoding="utf-8")
        record = self.run_lookup(skill_dir)
        self.assertFalse(record["found"])
        self.assertIn(str(partial), record["searched"])

    def test_missing_humanize_reports_not_found(self) -> None:
        skill_dir = self.make_skill(self.root / "a/b/c/staff-code-review")
        record = self.run_lookup(skill_dir)
        self.assertEqual(record["kind"], "humanize-refs")
        self.assertFalse(record["found"])

    def test_missing_skill_dir_is_usage_error(self) -> None:
        code = self.lookup.main(["--skill-dir", str(self.root / "nope")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
