# youtube-summary

Summarize a YouTube video from its transcript into a concise Markdown note: a one- or two-sentence TL;DR, 4-6 key points with `[m:ss]` timestamps, and takeaways. The note is printed in chat and saved to a folder you configure, such as an Obsidian inbox.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex, Copilot CLI and opencode.

## Requirements

- [uv](https://docs.astral.sh/uv/). The transcript script declares its dependency (`youtube-transcript-api`) inline, so `uv` installs it on first use with no manual setup.
- Network access to YouTube, and to PyPI on the first run.

## Installation

Claude Code (Copilot CLI is the same with `copilot` in place of `claude`):

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install youtube-summary@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add youtube-summary@sai
```

opencode, or any agent that reads Agent Skills, loads `skills/youtube-summary/` directly:

```bash
ln -s /path/to/sai/plugins/youtube-summary/skills/youtube-summary ~/.config/opencode/skills/youtube-summary
```

Local checkout: `claude --plugin-dir /path/to/sai/plugins/youtube-summary/`

## Configuration

Set `YOUTUBE_SUMMARY_DIR` to an existing folder where notes should go, for example in your shell profile:

```bash
export YOUTUBE_SUMMARY_DIR="$HOME/Documents/Obsidian Vault/0_Inbox"
```

In Claude Code you can also set it under `env` in `~/.claude/settings.json`. Notes are named `YouTube - <title>.md`; when another video's note has that name, the video id is appended.

When the variable is unset (or points to a missing folder), Claude Code asks where to save the note; other agents print it without saving. Summarizing the same video again replaces its earlier note.

## Usage

In Claude Code and Copilot CLI use `/youtube-summary`, in Codex `$youtube-summary`, or just share a YouTube link and ask for a summary.

```text
/youtube-summary https://www.youtube.com/watch?v=jNQXAC9IVRw
/youtube-summary https://youtu.be/jNQXAC9IVRw --no-save
/youtube-summary https://www.youtube.com/shorts/jNQXAC9IVRw --dir ~/notes/inbox
```

| Flag           | Purpose                                                       |
|:---------------|:--------------------------------------------------------------|
| (positional)   | YouTube URL (`watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`, `/live/`) or video id |
| `--no-save`    | Print the note only                                           |
| `--dir PATH`   | Save to this existing folder instead of `YOUTUBE_SUMMARY_DIR` |

An invalid URL, a video without a transcript, or an unavailable video ends with a clear message and no note.

## How it works

`skills/youtube-summary/scripts/fetch_transcript.py` fetches the transcript (English preferred, otherwise the first available language) and the title and channel, and resolves the note path. It prints JSON and never writes the note; the agent writes the summary following `skills/youtube-summary/references/output-template.md`. Offline checks: `uv run --script skills/youtube-summary/scripts/test_fetch_transcript.py`.

The PEP 723 dependency block sits directly above the first function instead of at the top of the file; PEP 723 allows it anywhere, and that placement satisfies a comment-blocking pre-write hook.

## License

MIT
