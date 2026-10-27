# Manim pitfalls and the 3b1b look

Manim Community 0.22, run as `uv tool run --python 3.13 --from manim manim`. Every item here broke or looked wrong at least once.

## Contents
- Environment and text
- Animation behavior
- Layout and visual review
- The 3b1b look

## Environment and text

- **Do not depend on LaTeX.** It is often not installed, and the pipeline does not need it. `MathTex`, `Tex`, `DecimalNumber`, `Integer`, `Brace.get_text`/`get_tex` and `add_coordinates()` all need LaTeX. Use `T()` (Pango text) for everything, `always_redraw(lambda: T(num(x)))` for live numbers, and position a `T` next to a `Brace` yourself. `Brace` itself works.
- **Math in Pango text.** Write formulas from Unicode and build fractions as `VGroup(numerator, Line, denominator).arrange(DOWN)`. CMU Serif has `· × ‖ − → ← ± √ ° % “ ” … ¹ ² ³` and `𝜃` (use `−` U+2212, not `-`). It lacks `≈ ⋮ ↔ ⇒ ≤ ≥ ≠ ∞ ∑ ∫ ∈ ✓ ✗ ∥ ⟨ ⟩` and all subscript digits: Pango silently draws those in a fallback font, which looks slightly off. Prefer words, draw the shape (`tick()`, `cross()`), or use `sub("h", 1)` and `sup("4", 7)` for subscripts and superscripts. `M()` uses CMU Typewriter Text, which has the same glyph set plus `•`. To test another character: `uv run --with fonttools python -c 'from fontTools.ttLib import TTFont; print(ord("≈") in TTFont("fonts/cmunrm.otf").getBestCmap())'`.
- **Theta.** CMU Serif draws `θ` (U+03B8) as a curly ϑ. Use `THETA` (`𝜃`, U+1D703) from explainer.py.
- **Glyph indexing.** In Manim 0.22 `Text` keeps an empty, zero-width submobject per space (older versions dropped them), and ligatures (fi, ff) merge glyphs. `T()` turns ligatures off; `part(mob, string, word)` handles both space behaviors and returns a word's glyphs, for coloring or underlining one word. Check a colored word at full resolution: at 480p a shift by a few letters is easy to miss (it happened).
- **System Python can be too new** for manim's wheels (pycairo, manimpango); always go through the uv tool with `--python 3.13`.
- **Imports in video.py**: manim does not put the project folder on `sys.path`; the template inserts it before the explainer import. explainer.py does not re-export Manim, so import Manim names from `manim` (new_project.py adds `from manim import *` above the explainer import of an old video.py that has only `from explainer import *`; above, so that explainer's `unit` still wins over Manim's module of that name).
- **Parallel renders share `media/texts`.** Two scenes building the same `Text` at the same time write and delete the same temp SVG, and one fails with `FileNotFoundError .../media/texts/<hash>_.svg`. `Narrated.setup()` gives each scene its own text folder; keep it if you override `setup()` (call `super().setup()`).
- **Debugging a scene**: a subclass in another file is only found if it is defined in that file (`class DIntro(video.Intro): pass`), not imported.

## Animation behavior

- **`fade_all` must fade Groups too.** `LaggedStart(*[m.animate...])` adds a plain `Group` (not a VMobject) to the scene; filtering on `VMobject` left those dots on screen. Exclude only `ValueTracker`.
- **`TransformFromCopy(a, b)` leaves the copy in the scene and never adds `b`.** If you animate `b` afterwards you get a stale duplicate (a dot stuck inside a box). Use `ReplacementTransform(a.copy(), b)`.
- **`Succession` with introducers** (Create, FadeIn of new objects) can show later mobjects before their turn. Play sequential steps with separate `self.play` calls.
- **`always_redraw` + `GrowArrow`/`FadeIn` is fine**: updaters are suspended during the animation and resume after.
- **Removing a submobject** (`FadeOut(group[i])`) is fine; the scene restructures the parent.
- **`mob.animate.set_opacity(x)` fills outlines.** It sets the fill opacity too, so a frame, box or window with no fill becomes a grey slab. Use `fade_to(mob, x)`, which dims strokes and only the fills that exist.
- **Color part of a text** at creation with `t2c`: `T("hash(edited payload) =", 38, t2c={"edited": RED})`. To animate one word later, use `part()` on a target: `line.generate_target(); part(line.target, s, word).set_color(YELLOW); self.play(MoveToTarget(line))`.
- **`Circumscribe` ends with a short tail** of its passing flash. A single frame near its end shows a small dash; it is removed when the animation ends, so it is not a leftover.
- **Exponential counters**: animate a `ValueTracker` with a custom `rate_func` (e.g. `lambda t: (a * (b / a) ** t - a) / (b - a)`) so 8 → 10,000,000 reads as growth, not a jump.
- **Animations longer than their clip** push the next clip later and leave silence. Keep the sum of `run_time`s in a beat below the clip length; `narration.py check` fails on pauses over 1.6 s.
- **Cues** are estimated from character offsets, so they can be up to ~0.5 s off. Cue on distinctive words that appear once in the clip; use `nth=` for repeats.

## Layout and visual review

- The frame is 14.2 × 8 units, centered at the origin. Text wider than the room left of a box, or labels placed `RIGHT`/`UR` of points near x = ±5, run off the edge. Measure: at font size 26 in CMU Serif a character is roughly 0.15 units wide; guard long text with `if t.width > w: t.scale_to_fit_width(w)`.
- Labels over a grid, graph or dot cloud need a plate: `backed(T(...))`.
- Random dot clouds: clip coordinates (`np.clip`) so dots do not land on labels or titles.
- `next_to(mob, RIGHT)` for labels on moving points: move the group (dot + label) together.
- Always render a low-quality pass and read every contact sheet (`./sheets.py 480p15`). Look for: text cut at the edges, overlaps, objects left over after a fade, frames with nothing on screen, and labels drawn under dots.

## The 3b1b look

- Black background (manim default), CMU Serif via `T()`, faint blue `NumberPlane` (`faint_plane()`).
- Palette: `BLUE`/`BLUE_B` for the main objects, `YELLOW` for the question or the focus, `TEAL`, `GOLD`, `GREEN` (good), `RED` (bad), `GREY_B` for secondary labels.
- One idea per beat; transform objects into the next idea instead of cutting (`ReplacementTransform`, text morphing into a vector, rows sliding to a new rank).
- `Write` for titles and formulas, `Create` for lines and graphs, `GrowArrow` for vectors, `LaggedStart` for groups, `Indicate`/`Circumscribe` to point at something while the voice names it.
- Live readouts (a value that updates while an arrow rotates) and moving parts teach better than static diagrams.
- End each scene with `fade_all()` so the joins between scene files are clean.
