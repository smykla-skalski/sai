# OCR Finder

Find text in images using EasyOCR, returning click coordinates. Works on screenshots and UI captures without accessibility permissions.

## Installation

### Quick install

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install ocr-finder@smykla-skalski-sai
```

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/ocr-finder/
```

## Usage

```bash
/ocr-finder [command] [args]
```

## Skills

- **ocr-finder**: Detect text in images and return bounding boxes with click coordinates for UI automation

## License

MIT
