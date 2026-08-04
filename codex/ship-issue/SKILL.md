---
name: ship-issue
description: Ship a GitHub issue end-to-end by reusing the source workflow under `claude/ship-issue`: implement, adversarially review and test, open a PR, address Copilot feedback, merge, and close the issue. Use when given a GitHub issue URL and asked to implement and ship it.
metadata:
  short-description: Ship a GitHub issue through merge
---

# Ship Issue

Use this skill when the user gives a GitHub issue URL and asks to implement and ship it through a merged PR.

This is a thin Codex wrapper around `claude/ship-issue/skills/ship-issue/SKILL.md`. Reuse the source workflow rather than maintaining a divergent copy.

## Source Material

- Source skill: `claude/ship-issue/skills/ship-issue/SKILL.md`
- Source directory: `claude/ship-issue/skills/ship-issue/`

Read the source workflow before acting and load only needed supporting files.

## Codex Adaptation

1. Resolve the issue URL, read the issue, explore the target repository, create a conventional feature branch, implement, and run the project’s narrowest relevant quality gates.
2. Run Phase 5 adversarial review and Phase 6 adversarial manual testing. Use native Codex subagents if capacity permits; otherwise perform each adversarial pass inline with the source prompts and acceptance criteria. Do not omit either pass.
3. Open the PR, request Copilot review where available, and poll at a 5–10 minute interval for both successful CI and a posted Copilot review. Address every valid thread and rerun the wait loop after fixes.
4. Merge only when all source conditions hold. Verify the issue closes, return to the default branch, and provide the source skill’s terse final report.

## Codex Notes

- Ignore Claude-only frontmatter and runtime wiring such as `allowed-tools`, `user-invocable`, and `$ARGUMENTS`.
- The user’s request to ship the issue authorizes normal branch, commit, push, PR, review-response, merge, and issue-close actions in the target repository. Ask only for ambiguity or an authority the source workflow identifies as a hard stop.
- Do not suppress quality checks or force a merge.
- If a networked command fails because of sandbox restrictions, rerun it with escalation and a concise justification.
- After each state-changing step, inspect the relevant GitHub or git state before continuing.
