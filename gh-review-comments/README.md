# GitHub Review Comments

List, reply to, resolve, and create GitHub PR review comment threads.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai && claude plugin install gh-review-comments@smykla-skalski-sai
```

### Manual

```bash
claude --plugin-dir /path/to/sai/gh-review-comments
```

## Usage

```bash
# List all review threads on a PR
/gh-review-comments owner/repo 42

# List unresolved threads from a specific reviewer
/gh-review-comments owner/repo 42 --author reviewer --unresolved-only

# Reply to all unresolved threads from a reviewer
/gh-review-comments owner/repo 42 --author reviewer --reply "Fixed"

# Reply and resolve a specific thread
/gh-review-comments owner/repo 42 --thread-id PRRT_abc123 --reply "Done" --resolve

# Create a review with line-level comments
/gh-review-comments owner/repo 42 --create-review
```

## Documentation

See [SKILL.md](./skills/gh-review-comments/SKILL.md) for detailed configuration and workflow.

## License

MIT - See [../LICENSE](../LICENSE)
