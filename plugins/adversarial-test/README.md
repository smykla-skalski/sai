# adversarial-test

Adversarial manual testing. It answers one question - does this change work for a user? - by running it:

1. **Test Adversary** subagent, in a clean context, derives acceptance criteria from the task, runs the real product surface (service + probe, CLI, sandbox, public API) against isolated temp state, and attacks boundaries, malformed input, repetition/concurrency, adjacent flows, and error paths. Every failure comes with a self-contained reproduction.
2. **Reproduction check**: the caller reruns each reproduction in a fresh shell. Confirmed and flaky failures survive; ones that never reproduce are dropped.

Unit tests, lint, and build output are supporting evidence only; a PASS backed by them alone is rejected.

Output leads with `Test Verdict: PASS`, `Test Verdict: FAIL`, or `Test Verdict: BLOCKED`, so callers such as `ship-issue` can gate on the first line.

For code correctness review, use `adversarial-review`.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install adversarial-test@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add adversarial-test@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/adversarial-test/` directly:

```bash
ln -s /path/to/sai/plugins/adversarial-test/skills/adversarial-test ~/.config/opencode/skills/adversarial-test
```

Optional named opencode subagent: create `~/.config/opencode/agents/test-adversary.md` with frontmatter `description` and `mode: subagent`, followed by the body of `skills/adversarial-test/references/test-adversary.md`. Leave bash allowed - the tester must run the product.

Local checkout: `claude --plugin-dir /path/to/sai/plugins/adversarial-test/`

## Usage

In Claude Code and Copilot CLI use `/adversarial-test`, in Codex `$adversarial-test`, or ask in plain words ("adversarially test this branch").

```text
/adversarial-test                                   # working tree vs merge-base with origin/<default>
/adversarial-test --base origin/release-1.4
/adversarial-test https://github.com/owner/repo/pull/123   # runs from a temp worktree if HEAD differs
/adversarial-test --context <issue-file|text>       # acceptance criteria for the tester
```

## Subagent per agent

| Agent | Subagent |
| :-- | :-- |
| Claude Code | Named agent `adversarial-test:test-adversary` from `agents/`; `general-purpose` with the mandate prepended as fallback |
| Copilot CLI | Same named agent `adversarial-test:test-adversary`; `general-purpose` fallback |
| Codex | One `spawn_agent` call with the mandate prepended, closed after the pass |
| opencode | `task` tool with an installed `test-adversary` agent or the built-in `general` subagent |

Every agent falls back to an inline pass when subagents are unavailable. Only one subagent runs at a time.

## Files

- `agents/test-adversary.md` - Claude Code and Copilot CLI agent definition
- `plugin.json` - root manifest for Codex and Copilot CLI. It has no `$schema` key on purpose: with `$schema` set, Copilot CLI stops registering the plugin's `agents/`
- `skills/adversarial-test/references/test-adversary.md` - the same mandate for the generic-subagent and inline paths. The agent body and the reference file must stay identical; `tests/test_adversarial_test_mandate.py` enforces it

## License

MIT
