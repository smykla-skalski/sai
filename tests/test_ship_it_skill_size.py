"""Keep the ship-it SKILL.md under the Codex skill prompt limit.

Codex truncates a plugin skill's SKILL.md past MAX_SKILL_PROMPT_BYTES
(openai/codex codex-rs/ext/skills/src/render.rs), hiding later phases.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Final

SKILL_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "plugins" / "ship-it" / "skills" / "ship-it"
)
SKILL_FILE: Final[Path] = SKILL_DIR / "SKILL.md"
CODEX_MAX_SKILL_PROMPT_BYTES: Final[int] = 8000
SKILL_BUDGET_BYTES: Final[int] = 6000
REFERENCE_LINK: Final[re.Pattern[str]] = re.compile(r"\]\((references/[^)]+\.md)\)")
CROSS_REF: Final[re.Pattern[str]] = re.compile(r"SKILL\.md|Phase \d")
PHASE_REFERENCE_ROWS: Final[tuple[tuple[str, str], ...]] = (
    ("1 — Resolve", "inputs.md"),
    ("2 — Explore", "explore.md"),
    ("3 — Branch", "branch.md"),
    ("4 — Implement", "implementation.md"),
    ("5 — Review", "review.md"),
    ("6 — Test", "test.md"),
    ("7–10 — PR loop", "pr-loop.md"),
    ("11 — Complete", "completion.md"),
)
PHASE_REFERENCE_ROW: Final[re.Pattern[str]] = re.compile(
    r"^\| (?P<phase>[^|]+?) \| "
    r"\[references/(?P<reference>[^]]+\.md)\]"
    r"\(references/(?P=reference)\) \|$",
    re.MULTILINE,
)


class ShipItSkillSizeTest(unittest.TestCase):
    def test_skill_fits_codex_prompt_limit(self) -> None:
        size = len(SKILL_FILE.read_bytes())
        self.assertLessEqual(
            size,
            CODEX_MAX_SKILL_PROMPT_BYTES,
            f"{SKILL_FILE} is {size} bytes; Codex truncates it",
        )
        self.assertLessEqual(
            size,
            SKILL_BUDGET_BYTES,
            f"{SKILL_FILE} is {size} bytes; move detail into references/",
        )

    def test_linked_references_exist_and_stand_alone(self) -> None:
        links = REFERENCE_LINK.findall(SKILL_FILE.read_text(encoding="utf-8"))
        self.assertTrue(links, "SKILL.md links no references")
        for link in sorted(set(links)):
            with self.subTest(reference=link):
                path = SKILL_DIR / link
                self.assertTrue(path.is_file(), f"missing {path}")
                self.assertIsNone(
                    CROSS_REF.search(path.read_text(encoding="utf-8")),
                    f"{link} must not cross-reference SKILL.md or its phases",
                )

    def test_every_phase_loads_its_guidance_on_demand(self) -> None:
        skill = SKILL_FILE.read_text(encoding="utf-8")
        phase_index = skill.split("## Phase reference index", 1)[1].split("\n## ", 1)[0]
        actual_rows = tuple(
            (match["phase"], match["reference"])
            for match in PHASE_REFERENCE_ROW.finditer(phase_index)
        )
        self.assertEqual(actual_rows, PHASE_REFERENCE_ROWS)

        for _, reference in PHASE_REFERENCE_ROWS:
            with self.subTest(reference=reference):
                link = f"[references/{reference}](references/{reference})"
                self.assertEqual(
                    skill.count(link),
                    1,
                    f"{reference} must appear once in the phase reference index",
                )


if __name__ == "__main__":
    unittest.main()
