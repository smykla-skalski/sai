"""Keep portable skill prompts within Codex's 8,000-byte limit."""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_SKILL_BYTES = 8_000
OVERSIZED_SKILL_ALLOWLIST = {
    "plugins/review-claude-md/skills/review-claude-md/SKILL.md",
}


class SkillSizeTest(unittest.TestCase):
    def test_skill_prompts_fit_codex_limit(self) -> None:
        oversized = {}
        for skill in sorted(REPO_ROOT.glob("plugins/*/skills/*/SKILL.md")):
            relative = skill.relative_to(REPO_ROOT).as_posix()
            size = skill.stat().st_size
            if size > MAX_SKILL_BYTES:
                oversized[relative] = size

        unexpected = {
            path: size
            for path, size in oversized.items()
            if path not in OVERSIZED_SKILL_ALLOWLIST
        }
        stale = OVERSIZED_SKILL_ALLOWLIST - oversized.keys()
        details = [
            *(f"{path}: {size} bytes" for path, size in unexpected.items()),
            *(f"{path}: stale allowlist entry" for path in sorted(stale)),
        ]
        self.assertFalse(
            unexpected or stale,
            "SKILL.md size limit violations:\n" + "\n".join(details),
        )


if __name__ == "__main__":
    unittest.main()
