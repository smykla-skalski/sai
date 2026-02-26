# UI Inspector

Inspect live macOS UI elements via Accessibility API and get click coordinates for automation.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ui-inspector@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/ui-inspector/
```

## Usage

```bash
/ui-inspector <command> --app <app> [--role <role>] [--title <title>] [--json]
```

## Skills

- **ui-inspector**: Find buttons, text fields, and other UI elements in running macOS applications

## License

MIT
