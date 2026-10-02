# adversarial-review

Fast two-pass adversarial code review. It answers one question - is this change correct? - with two opposed subagents, each in a clean context:

1. **Code Adversary** assumes the change is broken and hunts the concrete bug. Every finding needs a failing input or sequence.
2. **Findings Adversary** is spawned fresh, gets only the numbered findings (never the first agent's reasoning), and tries to refute each one against the source: removes false positives, right-sizes severity, fixes bad locations, merges duplicates.

Output leads with `Review Verdict: CLEAN` or `Review Verdict: NEEDS_FIXES`, so callers such as `ship-issue` can gate on the first line.

For architecture, conventions, and cross-team impact, use `staff-code-review` instead.

## Usage

```text
/adversarial-review                                   # working tree vs merge-base with origin/<default>
/adversarial-review --base origin/release-1.4
/adversarial-review https://github.com/owner/repo/pull/123
/adversarial-review <patch-file>
/adversarial-review --context <issue-file|text>       # acceptance criteria for the Code Adversary
```

## Runtimes

| Runtime | Package | Subagents |
| :-- | :-- | :-- |
| Claude Code | `claude/adversarial-review/` | Named agents `adversarial-review:code-adversary` and `adversarial-review:findings-adversary`; `general-purpose` fallback |
| Codex | `plugins/adversarial-review/` → `codex/adversarial-review/` | `spawn_agent`, sequential, closed after each pass |
| OpenCode | `codex/adversarial-review/` (symlinked skill) | `task` tool with installed agents or the built-in `general` subagent |

All runtimes fall back to inline passes when subagents are unavailable.

## Installation

```bash
# Claude Code
claude plugin marketplace add smykla-skalski/sai
claude plugin install adversarial-review@sai

# Codex: /plugin install adversarial-review@sai, or
ln -s /path/to/sai/codex/adversarial-review ~/.agents/skills/adversarial-review

# OpenCode
ln -s /path/to/sai/codex/adversarial-review ~/.config/opencode/skills/adversarial-review
```

## Files

- `agents/code-adversary.md`, `agents/findings-adversary.md` - Claude agent definitions
- `../../codex/adversarial-review/references/*.md` - the same mandates for Codex and OpenCode. Agent bodies and reference files must stay identical; edit both together

## License

MIT
