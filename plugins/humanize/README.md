# humanize

Identifies and removes signs of AI-generated writing from text, then rewrites it using proven composition principles.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Two complementary sources:

- **Detection**: Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide (WikiProject AI Cleanup) - 24 patterns across content, language, style, communication, and filler categories
- **Composition**: William Strunk Jr.'s [The Elements of Style](https://github.com/obra/the-elements-of-style) (1918) - active voice, concrete language, omitting needless words, sentence variety, emphasis placement

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install humanize@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add humanize@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/humanize/` directly:

```bash
ln -s /path/to/sai/plugins/humanize/skills/humanize ~/.config/opencode/skills/humanize
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/humanize/`

## Usage

In Claude Code and Copilot CLI use `/humanize`, in Codex `$humanize`, or ask in plain words ("humanize this PR description"). Where the agent has no subagent tool, the pattern scan runs inline instead of in a subagent; the output is the same.

```
/humanize path/to/file.md
/humanize path/to/file.md --score-only
/humanize path/to/file.md --dry-run
```

| Flag           | Purpose                                         |
|:---------------|:------------------------------------------------|
| (positional)   | File path to humanize                           |
| `--score-only` | Report detected patterns without rewriting      |
| `--dry-run`    | Output rewritten text to chat instead of saving |

## What it detects

24 AI writing patterns in five categories:

1. **Content** (1-6): significance inflation, notability claims, superficial -ing analyses, promotional language, vague attributions, formulaic challenges
2. **Language** (7-12): AI vocabulary, copula avoidance, negative parallelisms, rule-of-three, synonym cycling, false ranges
3. **Style** (13-18): em dash overuse, boldface overuse, inline-header lists, title case, emoji decoration, curly quotes
4. **Communication** (19-21): chatbot artifacts, knowledge-cutoff disclaimers, sycophantic tone
5. **Filler** (22-24): filler phrases, excessive hedging, generic positive conclusions

## License

MIT
