# adversarial-test

Adversarial manual testing. It answers one question - does this change work for a user? - by running it:

1. **Test Adversary** subagent, in a clean context, derives acceptance criteria from the task, runs the real product surface (service + probe, CLI, sandbox, public API) against isolated temp state, and attacks boundaries, malformed input, repetition/concurrency, adjacent flows, and error paths. Every failure comes with a self-contained reproduction.
2. **Reproduction check**: the caller reruns each reproduction in a fresh shell. Confirmed and flaky failures survive; ones that never reproduce are dropped.

Unit tests, lint, and build output are supporting evidence only; a PASS backed by them alone is rejected.

Output leads with `Test Verdict: PASS`, `Test Verdict: FAIL`, or `Test Verdict: BLOCKED`, so callers such as `ship-issue` can gate on the first line.

For code correctness review, use `adversarial-review`.

## Usage

```text
/adversarial-test                                   # working tree vs merge-base with origin/<default>
/adversarial-test --base origin/release-1.4
/adversarial-test https://github.com/owner/repo/pull/123   # runs from a temp worktree if HEAD differs
/adversarial-test --context <issue-file|text>       # acceptance criteria for the tester
```

## Runtimes

| Runtime | Package | Subagent |
| :-- | :-- | :-- |
| Claude Code | `claude/adversarial-test/` | Named agent `adversarial-test:test-adversary`; `general-purpose` fallback |
| Codex | `plugins/adversarial-test/` → `codex/adversarial-test/` | `spawn_agent`, closed after the pass |
| OpenCode | `codex/adversarial-test/` (symlinked skill) | `task` tool with an installed agent or the built-in `general` subagent |

All runtimes fall back to an inline pass when subagents are unavailable.

## Installation

```bash
# Claude Code
claude plugin marketplace add smykla-skalski/sai
claude plugin install adversarial-test@sai

# Codex: /plugin install adversarial-test@sai, or
ln -s /path/to/sai/codex/adversarial-test ~/.agents/skills/adversarial-test

# OpenCode
ln -s /path/to/sai/codex/adversarial-test ~/.config/opencode/skills/adversarial-test
```

## Files

- `agents/test-adversary.md` - Claude agent definition
- `../../codex/adversarial-test/references/test-adversary.md` - the same mandate for Codex and OpenCode. Agent body and reference file must stay identical; edit both together

## License

MIT
