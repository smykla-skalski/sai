# Animating video.py

Read [manim-pitfalls.md](manim-pitfalls.md) too: several Manim behaviors leave stray objects on screen.

## Shared helpers

`explainer.py` has the shared look, so use it before you draw your own. Import its names explicitly (`from explainer import Narrated, T, box`), and Manim's from `manim`.

| Helper | Draws |
| :-- | :-- |
| `T`, `M` | CMU Serif text and CMU Typewriter text (code, URLs, tokens); they take Text's options, and `t2c=` colors substrings |
| `sub`, `sup` | Subscripts and superscripts, which CMU Serif lacks |
| `tick`, `cross` | Drawn check mark and cross (no ✓ ✗ glyphs) |
| `person`, `window`, `server`, `database` | A figure, a browser window, a rack, a cylinder |
| `packet`, `flow` | A message that travels along an arrow; a steady stream of packets on a link |
| `bubble`, `box`, `page`, `backed` | A chat message, a labeled box, a document icon, a label on a black plate |
| `column`, `cells`, `faint_plane` | A bracketed column vector, a vector as colored squares, the faint grid |
| `lit`, `fade_to`, `part` | Light up a code line and one word in it, dim in place, the glyphs of one word |
| `num`, `MINUS`, `THETA` | A number with a real minus sign, and the glyphs that look right in CMU Serif |

Put helpers that only one video needs in video.py, not in explainer.py: new_project.py overwrites explainer.py.

## Narrated scenes

Each scene subclasses `Narrated` and is listed in `SCENES` in order:

```python
class Idea(Narrated):
    def construct(self) -> None:
        self.voice("idea_1")  # start the clip
        self.play(Create(plane))  # animations run while it speaks
        self.cue("point in space")  # wait for that phrase
        self.play(GrowFromCenter(dot))
        self.finish()  # wait for the clip to end, plus 0.4 s
        self.fade_all()  # end every scene clean
```

## Timing

- Keep the animations of a beat shorter than its clip: anything longer delays the next clip and leaves silence, and the check fails on pauses over 1.6 s.
- Between two cues, keep the `run_time`s shorter than the speech between the two words.
- build.py prints `LATE <clip> '<cue>' by 1.0s` when the picture reaches a cue after the voice said it: shorten the animations before that cue, or remove the cue. A cue on a word in the first second of a clip is always late if anything plays before it.
- Start the first clip of a scene with an animation before the first cue: a scene that waits for a cue first shows an empty screen for seconds.
- Preview one scene with sound: `uv tool run --python 3.13 --from manim manim -ql video.py Idea`.

## Checking a highlighted word

Wherever one word is colored or highlighted, extract that single frame at full size and check that exactly the right letters changed. At contact-sheet size a shift of a few letters is invisible, and it shipped once:

```bash
grep TIMELINE media/<Scene>.log        # each clip's start time inside that scene file
ffmpeg -ss <t> -i media/videos/video/1080p60/<Scene>.mp4 -frames:v 1 f.png
```

## Worked examples

Each pair in `examples/` is a finished video: copy `<topic>_script.py` and `<topic>_video.py` into a project as script.py and video.py to render it. Read the matching scene for a visual recipe.

- `examples/embeddings_video.py` is a complete 6-minute video (embeddings and reranking) with recipes for: words as points on a plane, a column vector with a brace, rotating vectors with a live cosine readout, tokens through a model and mean pooling, contrastive pull/push, chunking and a vector index, a kNN graph with a greedy ANN walk, a ranked table that re-sorts, bi- versus cross-encoder diagrams, attention lines between token rows, an exponential counter, and a funnel..
- `examples/oidc_video.py` is a 5.5-minute video on OpenID Connect, built on explainer.py, with recipes for: a browser mock with a cursor click, a three-party trust diagram, an analogy that morphs into the real parts (passport to ID token), a protocol triangle with messages that travel the front and back channels, a URL whose parameters light up as they are named, a JWT split into colored parts and decoded into a JSON panel with side labels, toy RSA signing and verification with superscripts, a checklist ticked on cue, a replay attack rejected, a timeline of two logins, and a recap chain of boxes.
- `examples/webtransport_video.py` is a 5-minute video on WebTransport, built on explainer.py, with recipes for: packets that stream along lanes with `flow` (continuous, with one packet lost and the lane stopped), numbered packets that queue in a buffer (head-of-line blocking), a protocol stack that is rebuilt layer by layer, two round-trip ladder diagrams side by side with message names along the arrows, an HTTP request panel whose fields light up, datagrams that overtake each other, a firewall that stops UDP, and a code panel lit line by line with `lit`.
