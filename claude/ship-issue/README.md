# ship-issue

Take one GitHub issue from URL to merged pull request autonomously: explore the repository, implement and test the change, red-team it with code review and manual testing, open a PR, address Copilot feedback, wait for green CI, merge, and close the issue.

## Installation

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ship-issue@sai
```

For local development:

```bash
claude --plugin-dir /path/to/sai/claude/ship-issue
```

## Usage

```text
/ship-issue https://github.com/owner/repo/issues/123
```

The skill owns the full ticket lifecycle and stops only for genuine ambiguity, branch-protection requirements, persistent review/test failures, or product decisions that cannot be recovered from the issue and repository.

## License

MIT
