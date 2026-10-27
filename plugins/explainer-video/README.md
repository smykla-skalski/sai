# explainer-video

Make 3Blue1Brown-style explainer videos: Manim animations on black with CMU Serif text, narrated with ElevenLabs text-to-speech. The agent writes the narration, voices it, animates each beat on the words the voice says, and builds one 1080p60 MP4. Before it reports, every clip is trimmed, transcribed and checked for clicks and dead air, the soundtrack is checked against the picture, and every frame is reviewed on contact sheets.

The plugin is a portable [Agent Plugin](https://agent-plugins.org) with one [Agent Skill](https://agentskills.io), so the same package works in Claude Code, Codex and other compatible agents. It runs on macOS and Linux.

## Installation

Claude Code:

```bash
claude plugin marketplace add smykla-skalski/sai
claude plugin install explainer-video@sai
```

Codex:

```bash
codex plugin marketplace add smykla-skalski/sai
codex plugin add explainer-video@sai
```

Other agents that read Agent Skills can use `skills/explainer-video/` directly, for example by linking it into `~/.agents/skills/explainer-video`.

## Requirements

- `ffmpeg` and `ffprobe`, `uv` and Python 3. uv installs Manim (on Python 3.13), numpy and faster-whisper on first use; LaTeX is not needed.
- An ElevenLabs API key in `ELEVEN_API_KEY`, or tell the agent where to read it (for example a 1Password reference). Narration costs about 1,000 ElevenLabs characters per minute of video, plus retakes.
- Network access to ElevenLabs, PyPI, CTAN (the CMU fonts) and Hugging Face (the Whisper model). In a sandboxed agent, allow these commands to run outside the sandbox.

## Usage

Ask in plain words, for example "make a 5-minute 3b1b-style video on how RAG works", "a short narrated explainer about bloom filters" or "fix the click at 1:31 in my video". In Claude Code, `/explainer-video` works too, and in Codex `$explainer-video`.

A full video takes about an hour of agent time; a one-minute video less. The agent cannot listen to audio, so it reports what it measured and asks you to name a timestamp for anything that sounds or looks wrong.

## How it works

`skills/explainer-video/scripts/new_project.py` copies the pipeline into a project folder: `tts.py` voices `script.py` and trims each clip, `video.py` holds the Manim scenes built on the shared helpers in `explainer.py`, `build.py` renders the scenes in parallel and builds the soundtrack from the clips at the times the scenes logged, and `narration.py check` compares the final file with that reference. `transcribe.py` and `sheets.py` drive the review. `scripts/selftest.py` builds the template project with synthetic tones, at no ElevenLabs cost, then checks that a project made by an older version still renders after a refresh.

To bring a project made by an older version of the skill up to date, run `new_project.py` on it: it refreshes the shared code, removes the old `build.sh` and `sheets.sh`, and adds the Manim import that an old `video.py` needs.

When a video shows a defect in the skill itself, the agent fixes the project copy and writes a GitHub issue draft for this repository instead of editing the installed skill, which plugin updates replace.

## License

MIT
