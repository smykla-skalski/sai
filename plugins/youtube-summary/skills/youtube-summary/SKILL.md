---
name: youtube-summary
description: Summarize a YouTube video from its transcript into a concise Markdown note with a TL;DR, key points and timestamps, then save it to the notes folder set by YOUTUBE_SUMMARY_DIR (for example an Obsidian inbox) or print it in chat. Use when the user shares a YouTube URL and wants a summary, key takeaways, or notes from a video.
license: MIT
compatibility: Needs uv and network access to YouTube (and PyPI on the first run). Works in Claude Code, Codex, opencode and Copilot CLI.
argument-hint: "[youtube-url] [--no-save] [--dir PATH]"
allowed-tools: AskUserQuestion Bash(uv run *) Read Write
user-invocable: true
metadata:
  short-description: Summarize a YouTube video into a note
---

# YouTube Summary

Fetch a YouTube video transcript, write a concise summary, print it, and save it as a Markdown note in the configured notes folder.

## Agent compatibility

Paths in this file are relative to the skill directory (the one holding this SKILL.md). The workflow is written for Claude Code; on other agents, or when a Claude feature is missing, use these fallbacks:

| Claude Code feature | Fallback |
| :-- | :-- |
| Argument substitution | If the "Parse from" line under Arguments shows no value or an unreplaced placeholder, take the URL and flags from the user's request |
| Skill directory substitution | If the script path in Phase 1 does not start with an absolute directory, use the absolute path of the directory that holds this SKILL.md instead |
| AskUserQuestion | Do not ask where to save. When no folder is configured, print the note, write no file, and mention `YOUTUBE_SUMMARY_DIR` and `--dir` |

The script needs network access and writes to the uv cache (`~/.cache/uv`). In a sandboxed agent, run it with escalated permissions or outside the sandbox (in Codex, request escalation with a short reason).

## Arguments

Parse from: $ARGUMENTS

| Flag | Default | Purpose |
| :-- | :-- | :-- |
| (positional) | required | YouTube URL in any form (`watch?v=`, `youtu.be/`, `/shorts/`, `/embed/`, `/live/`) or a bare 11-character video id. Ask for it if missing |
| `--no-save` | off | Print the note only; never write a file |
| `--dir PATH` | `YOUTUBE_SUMMARY_DIR` | Save the note in this existing folder instead of the configured one |

Default: print the note AND save it to the folder from `--dir` or the `YOUTUBE_SUMMARY_DIR` environment variable.

## Workflow

### Phase 1: Fetch transcript

Run the script and do not read it into context. Pass the URL as `--url='<url>'`: single quotes so the shell expands nothing, joined with `=` so an id starting with `-` still parses. Refuse an input that contains a single quote; no YouTube URL does. Add `--save-dir='<PATH>'` only when `--dir` was given, escaping any single quote in the path as `'\''`:

```bash
uv run --quiet --script "${CLAUDE_SKILL_DIR}/scripts/fetch_transcript.py" --url='<youtube-url>'
```

It prints one JSON object:

- `status`: `ok` or `error`; `error` holds the message when it is `error`
- `video_id`, `url`, `title`, `author`, `language`, `is_generated`
- `duration_human`, `segment_count`
- `transcript`: full plain text
- `chapters`: timestamped segments (`[m:ss] text`) for citing moments
- `note_path`: where to save the note, or `null` when no folder is configured
- `note_exists`: `true` when `note_path` already holds an earlier summary of the same video (matched by its `**URL:**` line)
- `save_dir_error`: set when the configured folder does not exist

If `status` is `error` (the script exits 1, or 2 for an input that is not a YouTube video), report the `error` message, follow Error Handling, and stop. Do not summarize and do not write any file.

### Phase 2: Pick the save location

Skip this phase when `--no-save` was passed or `note_path` is set.

- If `save_dir_error` is set, tell the user the configured folder does not exist and ask the question below.
- If no folder is configured, ask with AskUserQuestion: "Where should I save the note?" with options "Print only" (no file is written) and "Save to a folder" (the user types an existing folder path). Mention that setting `YOUTUBE_SUMMARY_DIR` skips this question next time.
- If the user gives a folder, rerun Phase 1 with `--save-dir='<PATH>'` to get `note_path`. If it still has no `note_path`, report `save_dir_error` and print only.

### Phase 3: Summarize

Base the summary ONLY on the transcript. No outside knowledge, no gap-filling.

- Read the full transcript and `chapters`.
- Distill the core thesis into a 1-2 sentence TL;DR.
- Extract 4-6 key points: the essential takeaways only, no padding.
- Cite the most important moments with `[m:ss]` timestamps from `chapters`.
- Keep it tight: this is a concise note, not a transcript rewrite.

### Phase 4: Output

Read [references/output-template.md](references/output-template.md) and produce the note in that format, with emojis, bullets and `[[wikilinks]]`. Keep the `**URL:**` line with the video URL: reruns use it to find and replace an earlier note. Print it in chat.

### Phase 5: Save

Skip when `--no-save` was passed or there is no `note_path`.

- `Write` the note to `note_path` exactly as returned. If `note_exists` is `true`, Read the file first and overwrite it, since it is an older summary of the same video.
- Confirm the saved path in chat.

## Error Handling

| Condition | Action |
| :-- | :-- |
| Not a YouTube URL or id (exit 2) | Report; ask for a valid YouTube URL. No note |
| Transcripts disabled / none available | Report; suggest the user paste a transcript. No note |
| Video unavailable, private, age-restricted | Report the message; stop. No note |
| YouTube blocked the request | Report; suggest retrying later or from another network. No note |
| Non-English transcript only | Summarize anyway; note the language in the output |
| `uv` missing or network failure | Show stderr; suggest installing uv or retrying |
| Configured folder missing | Report `save_dir_error`; ask (Phase 2) or print only |

Never invent video content when the transcript is missing.

## Quality Checklist

- [ ] Every claim traceable to the transcript
- [ ] TL;DR is 1-2 sentences; key points are 4-6 bullets
- [ ] Key timestamps cited with `[m:ss]`
- [ ] Title, channel and duration come from the script, not guessed
- [ ] Note saved to `note_path` (unless `--no-save` or print only); path confirmed
- [ ] No file written when the script reported an error

## Example Invocations

```text
/youtube-summary https://www.youtube.com/watch?v=jNQXAC9IVRw
/youtube-summary https://youtu.be/jNQXAC9IVRw --no-save
/youtube-summary https://www.youtube.com/shorts/jNQXAC9IVRw --dir ~/notes/inbox
```
