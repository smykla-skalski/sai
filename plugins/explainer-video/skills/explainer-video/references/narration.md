# Writing and checking the narration

## script.py

`BEATS = {SceneName: [(clip_key, text), ...]}`. One clip per beat; a beat is one visual step, 1-3 sentences, about 5-17 seconds.

Plan the length by characters: the trimmed voice speaks about 16 characters per second, about 950 per minute (160-200 words, more for short words). Planning at 150 words per minute made three one-minute videos come out about 20% short. After tts.py, add up the durations it prints and adjust the script before you animate.

A story arc that works: a concrete hook (a question the viewer has), the intuition, the mechanism, the math (small numbers, worked once), the system or pipeline, a failure case, the fix, the trade-offs, a recap that calls back to the hook. Introduce one idea per beat and plan its visual while you write it, because every beat must change what is on screen.

## Write for the ear

The text is spoken and never shown:

- Numbers as words ("ten million"), no symbols or abbreviations the voice would spell out.
- No ambiguous homographs: "measure closeness", not "measure close" (it was read as "clothes").
- Spell a term by sound when the voice says it wrong ("co-sign similarity" for cosine, "Quick" for QUIC). Keep a note in the docstring, and add Whisper's spelling to `HEARD` in script.py (`{"quic": "quick"}`) so transcribe.py does not flag it.
- Hyphenate acronyms that must be read letter by letter ("O-I-D-C", "J-W-T", "O-Auth" so it is not read "oath"). transcribe.py joins them back before it compares.
- Give each beat at least one distinctive word per visual change; the animation cues on those words.

## Judging the clip checks

`narration.py clips` must print OK: no clicks, no dead air.

`transcribe.py` flags clips whose words differ from the script. Numbers in digits or words, spacing such as "keycard" or "HTTP3", hyphenated acronyms and the `HEARD` words already count as equal. Judge each flag, because some are harmless ("Here is" spoken as "Here's"). It runs Whisper without a prompt on purpose: a prompt with the expected words hid a mispronunciation. Read the heard text for homophones too: "your write waits" was heard as "you're right weights", and a listener hears it the same way, so rewrite the sentence.

For a real problem:

- Mispronounced or ambiguous word: change the text in script.py and run tts.py again (changed text is voiced again automatically), then update any `cue()` that used the old word.
- Artifact in an otherwise right take (tap, glitch, odd intonation): `python3 tts.py <key>` for a new take. Takes are not deterministic.

Every take costs ElevenLabs characters, about 1,000 per minute of narration, so retake only flagged clips.
