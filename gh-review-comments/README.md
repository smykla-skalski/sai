# GitHub Review Comments

List, reply to, resolve, and create GitHub PR review comment threads.

## Installation

```bash
claude --plugin-dir /path/to/sai/gh-review-comments
```

## Usage

```bash
# List all threads
/gh-review-comments list <pr-url>

# Reply to a thread
/gh-review-comments reply <pr-url> <thread-id> <message>

# Resolve a thread
/gh-review-comments resolve <pr-url> <thread-id>

# Create new review comment
/gh-review-comments create <pr-url> <file> <line> <message>
```

## Documentation

See [SKILL.md](./SKILL.md) for detailed configuration and workflow.

## License

MIT - See [../LICENSE](../LICENSE)
