# Manage Plan

Create, modify, or transform implementation plans with codebase investigation and built-in quality validation.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install manage-plan@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/manage-plan/
```

## Usage

```bash
/manage-plan [task-description|plan-path|doc-path] [--create|--modify|--transform]
```

## Skills

- **manage-plan**: Investigate codebases and produce self-contained implementation plans for executor sessions. Supports creating plans from task descriptions, modifying existing plans, and transforming specs/RFCs into actionable execution plans. Includes automatic quality validation.

## License

MIT
