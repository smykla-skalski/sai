# test-writer

Write tests that verify behavior (not implementation), use table-driven/parameterized patterns, and minimize mocking.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install test-writer@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add test-writer@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/test-writer/` directly:

```bash
ln -s /path/to/sai/plugins/test-writer/skills/test-writer ~/.config/opencode/skills/test-writer
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/test-writer/`

## Usage

```bash
# Write tests for a file
/test-writer src/parser.go

# Review existing tests
/test-writer tests/parser_test.go --review

# Override language detection
/test-writer lib/utils.py --lang python
```

In Codex use `$test-writer` with the same target and flags, or ask in plain words ("write behavior tests for src/parser.go"). In Claude Code the skill runs in a forked `general-purpose` subagent; on other agents it runs in the main loop with the same workflow (see "Agent compatibility" in [skills/test-writer/SKILL.md](skills/test-writer/SKILL.md)).

## Features

- **Behavior-first testing** — tests survive refactoring, catch real bugs
- **Table-driven by default** — when 3+ cases share the same assertion shape
- **Mock discipline** — only external boundaries, max 2 mocks per test
- **Review mode** — detect 10 anti-patterns in existing tests
- **Multi-language** — Go, Python, TypeScript, Java, Rust

## Philosophy

Test what the code does, not how it does it. If you refactor internals and tests break — the tests are wrong, not the code.

## References

- `skills/test-writer/references/testing-principles.md` — core testing principles knowledge base
- `skills/test-writer/references/language-patterns.md` — idiomatic table-driven patterns per language
