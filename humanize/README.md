# humanize

A Claude Code plugin that identifies and removes signs of AI-generated writing from text.

Based on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide, maintained by WikiProject AI Cleanup. Detects and fixes 24 AI writing patterns across content, language, style, communication, and filler categories.

## Installation

### From GitHub Marketplace

Install from the [SAI plugin collection](https://github.com/smykla-skalski/sai).

### Manual

```bash
claude --plugin-dir /path/to/sai/humanize/
```

## Usage

```
/humanize path/to/file.md
/humanize path/to/file.md --score-only
/humanize path/to/file.md --inline
```

| Flag           | Purpose                                              |
|:---------------|:-----------------------------------------------------|
| (positional)   | File path to humanize                                |
| `--score-only` | Report detected patterns without rewriting           |
| `--inline`     | Edit the file in-place instead of outputting to chat |

## What it detects

24 AI writing patterns in five categories:

1. **Content** (1-6): significance inflation, notability claims, superficial -ing analyses, promotional language, vague attributions, formulaic challenges
2. **Language** (7-12): AI vocabulary, copula avoidance, negative parallelisms, rule-of-three, synonym cycling, false ranges
3. **Style** (13-18): em dash overuse, boldface overuse, inline-header lists, title case, emoji decoration, curly quotes
4. **Communication** (19-21): chatbot artifacts, knowledge-cutoff disclaimers, sycophantic tone
5. **Filler** (22-24): filler phrases, excessive hedging, generic positive conclusions

## License

MIT
