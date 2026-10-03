# go-code-review

Auto-review Go code for 100+ common mistakes from [100go.co](https://100go.co/).

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Features

- **100+ mistake patterns** — error handling, concurrency, interfaces, performance, testing, stdlib
- **Severity tiers** — Critical (fix before merge), Major (should fix), Minor (consider)
- **Mistake references** — every finding links to the numbered mistake in the knowledge base
- **False-positive guard** — re-reads flagged locations to confirm accuracy before reporting
- **Real-world patterns** — OSS project examples alongside the canonical reference

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install go-code-review@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add go-code-review@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/go-code-review/` directly:

```bash
ln -s /path/to/sai/plugins/go-code-review/skills/go-code-review ~/.config/opencode/skills/go-code-review
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/go-code-review/`

## Usage

Auto-triggers when reviewing `.go` files or Go PRs. Also invocable directly: `/go-code-review` in Claude Code and Copilot CLI, `$go-code-review` in Codex, or ask in plain words ("review this Go code for common mistakes"). The skill uses no Claude-only features, so the review is the same on every agent.

## Reference Material

- `skills/go-code-review/knowledge-base.md` — full 100 Go mistakes reference
- `skills/go-code-review/real-world-patterns.md` — OSS project patterns
- `skills/go-code-review/evals/test-cases.md` — eval test cases
