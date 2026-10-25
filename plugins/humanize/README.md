# humanize

Writes and rewrites text for people as short and plain as it can be without losing anything the reader needs: every fact, instruction, condition, number and the intended tone. It removes signs of AI-generated writing, fixes grammar and usage, applies plain composition rules, and checks the result against its source before it cuts further. The patterns are editing smells, not proof of who wrote a text, so the skill gives no authorship verdict and never adds fake mistakes to look human.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

Sources:

- Detection: Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide (WikiProject AI Cleanup), plus habits of AI agents such as burying the point: 30 patterns in six categories
- Meaning: a lossless plain-language method built on ISO 24495, Digital.gov and W3C guidance. It records what the reader must know and do, locks numbers, conditions, modal verbs, quotations and code, and checks recall and support before every further cut
- Usage and composition: all of William Strunk Jr.'s [The Elements of Style](https://github.com/obra/the-elements-of-style) (1918), rules 1-18 and the list of misused words, with the Google and Microsoft style guides where they have moved on from 1918, such as singular "they"

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

In Claude Code and Copilot CLI use `/humanize`, in Codex `$humanize`, or ask in plain words ("humanize this PR description", "tighten this paragraph", "write the commit message for this change"). The skill runs in the current conversation and starts no subagents.

It has three modes. Rewrite edits an existing draft and reports what it changed. Draft writes new text, such as a commit message, release notes or a docs section, from the facts you give, with no report. Score reports the patterns without a rewrite.

```
/humanize path/to/file.md
/humanize path/to/file.md --score-only
/humanize path/to/file.md --dry-run
```

| Flag           | Purpose                                         |
|:---------------|:------------------------------------------------|
| (positional)   | File path or text to rewrite or score           |
| `--score-only` | Report detected patterns without rewriting      |
| `--dry-run`    | Output rewritten text to chat instead of saving |

## What it detects

30 AI writing patterns in six categories:

1. **Content** (1-6): significance inflation, notability claims, superficial -ing analyses, promotional language, vague attributions, formulaic challenges
2. **Language** (7-12): AI vocabulary, copula avoidance, negative parallelisms, rule-of-three, synonym cycling, false ranges
3. **Style** (13-18): em dash overuse, boldface overuse, inline-header lists, title case, emoji decoration, curly quotes
4. **Communication** (19-21): chatbot artifacts, knowledge-cutoff disclaimers, sycophantic tone
5. **Filler** (22-24): filler phrases, excessive hedging, generic positive conclusions
6. **Structure** (25-30): buried point, over-completing, excessive balance, generic headings, unsupported confidence, needless connectors

It also fixes Strunk's usage errors (possessives, serial commas, comma splices, fragments, dangling modifiers and 65 misused words and expressions) and applies his composition rules.

## Evals

`evals/` holds behavior tests for [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals): in-place rewrite, `--score-only` without an authorship verdict, a chat-only preview, pasted text, a buried point, already clean text with contractions and one natural em dash, usage errors, protected conditions and numbers, a wordy text cut to under 60% of its length, a polite request that must stay polite, unsupported claims kept and flagged, and two drafts (a docs section and a commit message) with no report. Each case also checks that the skill runs in the main session and starts no subagent. The cases copy their input files into the workspace, so they need `--scaffold`:

```bash
claude plugin eval plugins/humanize --scaffold --allow-tools Edit Write --judge-model opus
```

The judge graders are tuned for Opus. Weaker judge models misread some correct replies or flip on near-identical ones.

## License

MIT
