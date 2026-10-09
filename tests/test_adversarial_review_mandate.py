"""Keep the adversarial-review agents, mandates and verdict contract in sync.

Run with: python3 -m unittest discover -s tests

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "adversarial-review"
AGENTS_DIR = PLUGIN_DIR / "agents"
REFERENCES_DIR = PLUGIN_DIR / "skills" / "adversarial-review" / "references"
WORKFLOW_FILE = REFERENCES_DIR / "workflow.md"
ADVERSARIES = ("code-adversary", "findings-adversary")
FRONTMATTER_FENCE = "---\n"
CODE_VERDICT = re.compile(
    r"^CODE_ADVERSARY_VERDICT: "
    r"(FOUND BLOCKING \(\d+\)|FOUND ISSUES \(\d+\)|MINOR ONLY \(\d+\)|CLEAN)$"
)
FINDINGS_VERDICT = re.compile(r"^FINDINGS_ADVERSARY_VERDICT: (SOUND|CORRECTED|ESCAPED_BUG)$")
VALID_CODE_VERDICTS = (
    "CODE_ADVERSARY_VERDICT: FOUND BLOCKING (2)",
    "CODE_ADVERSARY_VERDICT: FOUND ISSUES (1)",
    "CODE_ADVERSARY_VERDICT: MINOR ONLY (3)",
    "CODE_ADVERSARY_VERDICT: CLEAN",
)
MALFORMED_CODE_VERDICTS = (
    "CODE_ADVERSARY_VERDICT: FOUND BLOCKING",
    "CODE_ADVERSARY_VERDICT: CLEAN.",
    "Code adversary verdict: clean",
    "CODE_ADVERSARY_VERDICT: NEEDS_FIXES",
)
VALID_FINDINGS_VERDICTS = (
    "FINDINGS_ADVERSARY_VERDICT: SOUND",
    "FINDINGS_ADVERSARY_VERDICT: CORRECTED",
    "FINDINGS_ADVERSARY_VERDICT: ESCAPED_BUG",
)
MALFORMED_FINDINGS_VERDICTS = (
    "FINDINGS_ADVERSARY_VERDICT: SOUND (3)",
    "FINDINGS_ADVERSARY_VERDICT: CLEAN",
    "findings adversary verdict: sound",
)


def strip_frontmatter(text: str) -> str:
    if not text.startswith(FRONTMATTER_FENCE):
        message = "agent file has no YAML frontmatter"
        raise ValueError(message)
    end = text.index("\n" + FRONTMATTER_FENCE, len(FRONTMATTER_FENCE))
    return text[end + 1 + len(FRONTMATTER_FENCE) :].lstrip("\n")


def read_mandate(name: str) -> str:
    return (REFERENCES_DIR / f"{name}.md").read_text(encoding="utf-8")


class MandateSyncTest(unittest.TestCase):
    def test_agent_bodies_match_reference_mandates(self) -> None:
        for name in ADVERSARIES:
            with self.subTest(agent=name):
                agent_file = AGENTS_DIR / f"{name}.md"
                agent_body = strip_frontmatter(agent_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    agent_body,
                    read_mandate(name),
                    f"edit {agent_file.name} body and references/{name}.md together",
                )

    def test_agent_frontmatter_names_match_file_names(self) -> None:
        for name in ADVERSARIES:
            with self.subTest(agent=name):
                head = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8").split("\n", 2)[1]
                self.assertEqual(head, f"name: {name}")


class ProofContractTest(unittest.TestCase):
    def test_code_adversary_requires_proof_for_blocking(self) -> None:
        mandate = read_mandate("code-adversary")
        for marker in ("## Proof ladder", "*Proof:*", "*Trace:*", "`question:`"):
            with self.subTest(marker=marker):
                self.assertIn(marker, mandate)
        self.assertIn("A `blocking:` without a `*Proof:*` or `*Trace:*` line is not a blocking finding", mandate)

    def test_findings_adversary_strips_unproven_blocking(self) -> None:
        mandate = read_mandate("findings-adversary")
        self.assertIn("**Proof is executed.**", mandate)
        self.assertIn("DOWNGRADE→`issue:`", mandate)
        self.assertIn("DOWNGRADE→`question:`", mandate)
        self.assertIn("A race with no step-by-step trace is a `question:`, never a blocker", mandate)

    def test_findings_adversary_refuses_clean_input(self) -> None:
        mandate = read_mandate("findings-adversary")
        self.assertIn("If the list holds no `blocking:` or `issue:` finding", mandate)
        self.assertIn("end with `FINDINGS_ADVERSARY_VERDICT: SOUND`", mandate)


class VerdictFormatTest(unittest.TestCase):
    def test_workflow_documents_both_verdict_patterns(self) -> None:
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        self.assertIn(CODE_VERDICT.pattern, workflow)
        self.assertIn(FINDINGS_VERDICT.pattern, workflow)

    def test_documented_code_verdicts_match_pattern(self) -> None:
        for line in VALID_CODE_VERDICTS:
            with self.subTest(line=line):
                self.assertRegex(line, CODE_VERDICT)
        for line in MALFORMED_CODE_VERDICTS:
            with self.subTest(line=line):
                self.assertNotRegex(line, CODE_VERDICT)

    def test_documented_findings_verdicts_match_pattern(self) -> None:
        for line in VALID_FINDINGS_VERDICTS:
            with self.subTest(line=line):
                self.assertRegex(line, FINDINGS_VERDICT)
        for line in MALFORMED_FINDINGS_VERDICTS:
            with self.subTest(line=line):
                self.assertNotRegex(line, FINDINGS_VERDICT)

    def test_workflow_fails_gate_after_one_retry(self) -> None:
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        self.assertIn("Review Verdict: FAILED", workflow)
        self.assertIn("A second malformed reply is a gate failure", workflow)

    def test_workflow_checks_verdict_keyword_against_labels(self) -> None:
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        self.assertIn("The keyword must agree with the labels", workflow)
        self.assertIn("a keyword that disagrees with the labels", workflow)

    def test_workflow_skips_findings_pass_without_fixable_findings(self) -> None:
        workflow = WORKFLOW_FILE.read_text(encoding="utf-8")
        self.assertIn("when no finding is labelled `blocking:` or `issue:`", workflow)
        self.assertIn("Never dispatch the Findings Adversary to refute a clean result", workflow)

    def test_findings_guard_reply_satisfies_validator(self) -> None:
        mandate = read_mandate("findings-adversary")
        self.assertIn("write `F<n> — UPHOLD — not applicable —", mandate)


if __name__ == "__main__":
    unittest.main()
