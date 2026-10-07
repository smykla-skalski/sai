"""Keep portable skill prompts within Codex's 8,000-byte limit."""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_SKILL_BYTES = 8_000
OVERSIZED_SKILL_ALLOWLIST = {
    "plugins/adversarial-review/skills/adversarial-review/SKILL.md",
    "plugins/adversarial-test/skills/adversarial-test/SKILL.md",
    "plugins/ai-daily-digest/skills/ai-daily-digest/SKILL.md",
    "plugins/council/skills/council/SKILL.md",
    "plugins/generate-claude-md/skills/generate-claude-md/SKILL.md",
    "plugins/git-stage-hunk/skills/git-stage-hunk/SKILL.md",
    "plugins/humanize/skills/humanize/SKILL.md",
    "plugins/kubecon-cfp/skills/kubecon-cfp/SKILL.md",
    "plugins/kup/skills/kup/SKILL.md",
    "plugins/plan-critic/skills/plan-critic/SKILL.md",
    "plugins/promptgen/skills/promptgen/SKILL.md",
    "plugins/refactor-council/skills/refactor-council/SKILL.md",
    "plugins/review-claude-md/skills/review-claude-md/SKILL.md",
    "plugins/service-mesh-debug/skills/service-mesh-debug/SKILL.md",
    "plugins/staff-resume/skills/staff-resume/SKILL.md",
    "plugins/technical-debt-manager/skills/technical-debt-manager/SKILL.md",
    "plugins/test-writer/skills/test-writer/SKILL.md",
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
