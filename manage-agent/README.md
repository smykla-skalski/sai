# Manage Agent

Create, modify, or transform Claude Code agent definitions with built-in quality validation.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install manage-agent@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/manage-agent/
```

## Usage

```bash
/manage-agent [file-path|description] [--create|--modify|--transform]
```

## Skills

- **manage-agent**: Create new agents from descriptions, improve existing agents, or convert prompt templates into production-quality agent definitions. Includes automatic quality validation against a comprehensive checklist.

## License

MIT
