---
name: explainer-video
description: Make 3Blue1Brown-style animated explainer videos (Manim animations on black, CMU Serif text, narrated with ElevenLabs text-to-speech), from a topic to a checked 1080p60 MP4. Use this whenever the user asks for a 3b1b-style video, an animated or narrated explainer, a Manim video, a video that explains a concept (math, ML, AI, RAG, algorithms, systems, protocols, security), or wants voice-over on an explainer, even if they do not say "Manim" or "ElevenLabs". Also use it to fix or re-render a video made this way (noise, clicks, gaps without voice, sync, wrong pronunciation, cut-off text).
license: MIT
compatibility: Needs ffmpeg, uv, an ElevenLabs API key and network access (ElevenLabs, PyPI, CTAN, Hugging Face). macOS or Linux.
allowed-tools: Bash Edit Read Write
user-invocable: true
metadata:
  short-description: Narrated 3b1b-style Manim explainer videos
---

# Explainer videos: 3b1b style with ElevenLabs narration

```
script.py (narration beats) --tts.py--> audio/<key>.mp3, trimmed <key>.wav, manifest.json (durations)
video.py (Narrated scenes: voice / cue / finish) --build.py--> one mp4 per scene + TIMELINE lines in logs
build.py: narration.py mix (soundtrack from the clips at TIMELINE times) -> one static gain -> mux -> narration.py check
review: transcribe.py (are the words right?), sheets.py (does every frame look right?) -> report
```

The real duration of each clip drives the animation timing, so nothing is guessed. The soundtrack is assembled sample-exactly from the trimmed clips, never from Manim's audio mix, so the checks can compare the finished file against a known-correct reference. Every rule here comes from a defect a listener found in a real build; [references/audio-pitfalls.md](references/audio-pitfalls.md) lists them with causes.

Paths here are relative to this skill's directory. `scripts/new_project.py` copies the pipeline into the project; run the copies from the project folder.

## Agent compatibility

| Claude Code feature | Elsewhere |
| :-- | :-- |
| Read on a PNG sheet or frame | Open the image with the agent's image viewer (`view_image` in Codex). If you cannot open images, say in the report that the frames were not reviewed |
| Edit and Write | The agent's file-edit tool (`apply_patch` in Codex) |
| Unsandboxed Bash | The scripts need network access and write to `~/.cache/uv`; request escalation for them (in Codex too). Renders take minutes: allow a long timeout or run them in the background |

## 1. Settle the brief

Take defaults and ask only what you cannot infer:

- Topic and audience: what the viewer should understand at the end.
- Length: 5-7 minutes for a full topic, about 1 minute when the user says "short".
- Voice: Chris (`iP95p4xoKVk53GoZ742B`) unless the user names another; `ELEVEN_VOICE_ID` changes it. Others: [references/audio-pitfalls.md](references/audio-pitfalls.md).
- API key: tts.py reads `ELEVEN_API_KEY`. If it is unset, ask the user where the key is (for example a 1Password reference) and set it in the same command as tts.py. Never print the key.
- Folder: the current directory if it is empty apart from git files, else a new `./<topic-slug>/`.
- Cost: about 1,000 ElevenLabs characters per minute of narration, plus retakes.

## 2. Scaffold

```bash
<skill dir>/scripts/new_project.py <project-dir>
```

It copies the shared code (`tts.py`, `narration.py`, `build.py`, `transcribe.py`, `sheets.py`, `explainer.py`) and the starting `script.py` and `video.py`, fetches the CMU fonts and checks the tools. Running it again refreshes the shared code, keeps `script.py` and `video.py`, and migrates a project made by an older version of the skill.

## 3. Write the narration

Read [references/narration.md](references/narration.md) before you write `script.py`: one clip per beat, written for the ear, with a distinctive word for every visual change.

## 4. Voice it and check every clip

```bash
ELEVEN_API_KEY=... python3 tts.py               # new or changed beats only
uv run --quiet --python 3.13 --with numpy python narration.py clips
uv run --quiet --python 3.12 --with faster-whisper python transcribe.py
```

`narration.py clips` must print OK. Judge every clip transcribe.py flags as [references/narration.md](references/narration.md) says, and fix real problems before you animate.

## 5. Animate (`video.py`)

Read [references/animation.md](references/animation.md) and [references/manim-pitfalls.md](references/manim-pitfalls.md) first: no LaTeX, several Manim behaviors that leave stray objects, the shared helpers, the timing rules, and the worked examples to copy recipes from. Each scene subclasses `Narrated`: `self.voice(key)`, `self.cue("word")`, `self.finish()`, `self.fade_all()`.

## 6. Preview and look at every frame

```bash
QUALITY=l ./build.py        # <folder>-480p15.mp4, ends with the audio check
./sheets.py 480p15          # media/sheets/<Scene>-<n>.png: 4x4 frames, one sheet per 40 s
```

Open and read every sheet; running sheets.py is not a review. Look for text cut at the frame edges, overlapping labels, leftovers after a fade, labels under dots or lines, empty frames, and `LATE` lines from build.py. Check each highlighted word at full size (see animation.md). Fix and repeat until the sheets are clean.

## 7. Final render

```bash
QUALITY=h ./build.py        # 1080p60; writes <folder-name>.mp4, or set OUT=name.mp4
```

It must end with `OK`. When `narration.py check` fails, fix the cause; never loosen a threshold, because each one maps to a defect someone heard. It checks: every clip clean, played once and in order without overlap; the final audio matches the expected mix; audio within 5 ms of the picture; no pause without voice over 1.6 s; peak at most -1 dBFS.

## 8. Report

Give the path, length and resolution, then what you verified, with numbers: the check output (gain, peak, longest pause), the transcription result, and that you reviewed the frames of every scene. Say plainly that you cannot listen to audio, and ask the user to watch it and name a timestamp for anything that sounds or looks wrong. Tell them how to change it: edit `script.py`, run `tts.py`, run `build.py`; `python3 tts.py <key>` retakes one clip. List any skill issue drafts (below). Keep it short: no scene-by-scene retelling and no log of the work.

## When the user reports a problem at a time

1. `uv run --quiet --python 3.13 --with numpy python narration.py where 1:31` shows the scene, the clip and the words playing then.
2. Read [references/audio-pitfalls.md](references/audio-pitfalls.md) and look at the audio there (spectrogram and waveform commands are in it) before you change anything.
3. Fix the cause, run `QUALITY=h ./build.py` to `OK` for the whole video, then read the sheets of every scene you changed.
4. Only then report it as fixed: in the first video the "tap" came back three times, from three different causes.

## Defects in this skill

Never edit files in this skill's directory: the installed copy is replaced on every plugin update. When the work shows a defect whose cause is in the skill (a script, a helper, a step, a missing pitfall), fix the project copy so the video ships, then read [references/skill-issues.md](references/skill-issues.md) and write a GitHub issue draft for `smykla-skalski/sai` that someone can implement as written. File it only when the user asks.
