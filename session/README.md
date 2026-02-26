# Session

Capture session context for continuity between Claude Code sessions. Generates handover documents with failed approaches, architectural decisions, and next steps.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install session@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/session/
```

## Usage

```bash
/session [session-focus]
```

## Skills

- **session**: Capture critical session context so the next session can continue without re-investigation or retrying failed approaches

## License

MIT
