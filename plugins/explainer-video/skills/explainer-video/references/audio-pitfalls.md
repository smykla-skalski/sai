# Audio pitfalls: symptom, cause, fix

Each row is a defect a listener heard in a real build. The bundled scripts already contain every fix; this file explains why they look the way they do, and how to investigate a new report.

| Symptom | Cause | Fix (in the scripts) |
|---|---|---|
| Click or "mic tap" at a scene change | Joining the per-scene AAC tracks with the concat demuxer: encoder padding at every seam | Never join encoded audio. narration.py builds one PCM track from the clips; encode once. |
| Narration drifts earlier and earlier (13 s by the end) | Manim's scene audio stops at the last sound, before the video ends; joining the tracks dropped those gaps | The track is built on the video timeline: each scene's span is its video duration. |
| Whole clips missing, 6-11 s of silence with text on screen | Manim's partial-movie cache drops `add_sound` clips when a scene is rendered again | `--disable_caching` in build.py, and the soundtrack no longer comes from Manim at all. |
| Audio 21 ms late | AAC encoder priming in Manim's mp4s, not removed on decode | Soundtrack from the clips (TIMELINE), not from Manim's mix. |
| Dead air at every beat and scene end ("text with no voice") | ElevenLabs adds up to 1.5 s of silence at the start and end of each clip | `tts.py` trims to 50 ms before and 150 ms after the speech. |
| Loud 50 ms blip right after a clip | ffmpeg `silenceremove` + `areverse` trimming copies a speech fragment to the end | Trim in Python, sample-exact (`trim()` in tts.py). Do not use silenceremove for trimming. |
| Tap about 1 s after the last word | Some ElevenLabs takes end with a lone click | `trim()` drops short sound runs separated from the speech at either edge. |
| Tap inside a sentence | The take itself: an abrupt restart after a gated silence | Retake: `python3 tts.py <key>`. Takes are not deterministic. |
| Speech starts abruptly | Some takes start speaking at sample 0 | `trim()` pads silence in front and fades 10 ms in / 30 ms out. |
| Volume pumps | ffmpeg `loudnorm` single-pass mode is dynamic | build.py measures once and applies one static gain (-16 LUFS, peak at most -1.5 dBTP). |
| `narration.py clips` reports an isolated short sound at 0.05 s, but the clip starts with a short word ("So ...") | The voice paused after the first word, so the word looks like a click: under 0.3 s, with silence on both sides | Look at the spectrogram: a word has a hiss or a vowel with harmonics, a click is one thin vertical line. For a word, rewrite the sentence without it; do not change the check. |
| Wrong word ("close" heard as "clothes", "cosine" as "co-zeen") | Homographs and technical terms | Rewrite the text: "closeness", "co-sign". The script is never shown on screen. Check with transcribe.py. |

## Investigating a reported noise or gap

1. `narration.py where 1:31` maps the time to the scene, the clip and the words playing.
2. Look at the clip and the final track around that time instead of guessing:
   - spectrogram: `ffmpeg -ss 88 -t 6 -i video.mp4 -vn -lavfi "showspectrumpic=s=1600x450:legend=1:scale=log:fscale=log" spec.png`; a click is a thin vertical line across all frequencies.
   - waveform: same with `showwavespic=s=1600x250:draw=full`.
3. Decide where the defect lives: in the source mp3 (retake), in the trimmed wav (trim bug), or only in the final file (mix or encode bug). The isolated-sound and comparison checks in narration.py separate these cases.
4. Fix the cause, rebuild, and let `narration.py check` pass on the whole video before you report. A fix at one timestamp often hides the same defect elsewhere (the "tap" came back three times from three different causes).

## Facts about the ElevenLabs setup

- tts.py reads the key from `ELEVEN_API_KEY`. Never print it. From a password manager, set it in the same command: `ELEVEN_API_KEY=$(op read "<reference>") python3 tts.py`.
- The key may lack `user_read`: `/v1/user/subscription` and `/v1/models` return 401, while `/v1/voices` and text-to-speech work. Do not depend on quota checks.
- API calls use Python `urllib` (tts.py does), so the scripts need no HTTP client tools.
- `previous_text` / `next_text` keep the intonation natural across clips.
- Premade voices that suit explainers: Chris `iP95p4xoKVk53GoZ742B` (default, warm, American), Eric `cjVigY5qzO86Huf0OWal`, Brian `nPczCjzI2devNBz1zQrb` (deep), George `JBFqnCBsd6RMkjVDRZzb` and Daniel `onwK4e9ZLuTAKqWW03F9` (British).
- Speech rate with Chris, after trim(): about 16 characters per second, 2.7-3.3 words per second (three one-minute bloom filter scripts: 800-865 characters in 51-53 s of clips).
