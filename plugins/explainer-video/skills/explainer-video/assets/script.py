"""Narration, one clip per beat: {scene class: [(clip key, spoken text), ...]}.

Keys are used in video.py. The text is only spoken, never shown, so write for the
ear: numbers as words, no ambiguous homographs ("close" -> "closeness"), and terms
the voice gets wrong spelled by sound ("co-sign"). Replace this example with the
real script.

Copyright 2026 Smykla Skalski, MIT License.
"""

from typing import Final

# Whisper's spelling -> the script's, for terms spelled by sound.
HEARD: Final = {"cosine": "co sign"}

BEATS: Final = {
    "Title": [
        (
            "title_1",
            (
                "How can a computer tell that two sentences mean the same thing, "
                "even when they share no words? Let's draw it."
            ),
        ),
    ],
    "Idea": [
        (
            "idea_1",
            (
                "Picture every sentence as a point in space. "
                "Sentences with similar meanings land close together."
            ),
        ),
        (
            "idea_2",
            (
                "So distance becomes a measure of meaning. "
                "Short arrow, similar. Long arrow, different."
            ),
        ),
    ],
}
