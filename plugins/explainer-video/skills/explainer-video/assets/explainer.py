"""Shared look and narration timing for 3b1b-style scenes, imported by video.py.

new_project.py refreshes this file from the skill; put helpers for one video in
video.py.

Narrated scenes sync animation to speech:
    self.voice("key")    start a clip (logs the TIMELINE line narration.py mixes from)
    self.cue("word")     wait until about when "word" is spoken (from its offset)
    self.finish()        wait for the clip to end, plus a short pause
    self.fade_all()      fade out everything at the end of a scene or a section

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypedDict

import manimpango
import numpy as np
from manim import (
    BLACK,
    BLUE,
    BLUE_B,
    BLUE_D,
    DOWN,
    GREEN,
    GREEN_C,
    GREY_B,
    GREY_E,
    LEFT,
    ORIGIN,
    PI,
    RED,
    RED_C,
    RIGHT,
    TAU,
    UP,
    WHITE,
    YELLOW,
    YELLOW_C,
    BackgroundRectangle,
    Circle,
    Dot,
    FadeOut,
    Line,
    ManimColor,
    Mobject,
    MoveToTarget,
    NumberPlane,
    ParametricFunction,
    Rectangle,
    RoundedRectangle,
    Scene,
    Sector,
    Square,
    SurroundingRectangle,
    Text,
    ValueTracker,
    VGroup,
    VMobject,
    config,
    interpolate_color,
)
from typing_extensions import Unpack, override

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    import numpy.typing as npt
    from manim import ParsableManimColor
    from manim.typing import Point3DLike


class Clip(TypedDict):
    """One narration clip in audio/manifest.json, written by tts.py."""

    text: str
    dur: float


class TextOptions(TypedDict, total=False):
    """Text options that serif() and mono() pass on to Manim's Text."""

    fill_opacity: float
    stroke_width: float
    line_spacing: float
    slant: str
    weight: str
    t2f: dict[str, str]
    t2g: dict[str, Iterable[ParsableManimColor]]
    t2s: dict[str, str]
    t2w: dict[str, str]
    gradient: Iterable[ParsableManimColor]
    tab_width: int
    warn_missing_font: bool
    height: float
    width: float
    should_center: bool
    use_svg_cache: bool


class AnimationOptions(TypedDict, total=False):
    """Animation options that fade_to() passes on to MoveToTarget."""

    run_time: float
    rate_func: Callable[[float], float]
    lag_ratio: float
    reverse_rate_function: bool
    name: str
    remover: bool
    suspend_mobject_updating: bool
    introducer: bool


ROOT: Final = Path(__file__).parent
CLIPS: Final[dict[str, Clip]] = json.loads(
    (ROOT / "audio" / "manifest.json").read_text()
)
for font_file in (ROOT / "fonts").glob("*.otf"):
    manimpango.register_font(str(font_file))

FONT: Final = "CMU Serif"
MONO: Final = "CMU Typewriter Text"
# CMU Serif draws U+03B8 as a curly vartheta; the math-italic code point gives the
# usual closed theta.
THETA: Final = "\N{MATHEMATICAL ITALIC SMALL THETA}"
MINUS: Final = "\N{MINUS SIGN}"
LATE_AFTER: Final = 0.3  # seconds the picture may trail its cue before LATE is logged
FRAME: Final = 1 / 30  # waits shorter than a frame are skipped


def serif(
    s: str,
    size: float = 36,
    color: ParsableManimColor = WHITE,
    t2c: Mapping[str, ParsableManimColor] | None = None,
    **kw: Unpack[TextOptions],
) -> Text:
    """Return CMU Serif text with ligatures off, so glyph indexes match characters.

    t2c colors substrings, as in Text. part() needs the one glyph per character.
    """
    return Text(
        s,
        font=FONT,
        font_size=size,
        color=color,
        disable_ligatures=True,
        t2c=_hex_colors(t2c),
        **kw,
    )


def mono(
    s: str,
    size: float = 26,
    color: ParsableManimColor = WHITE,
    t2c: Mapping[str, ParsableManimColor] | None = None,
    **kw: Unpack[TextOptions],
) -> Text:
    """Return CMU Typewriter text for code, URLs, tokens and parameters."""
    return Text(
        s,
        font=MONO,
        font_size=size,
        color=color,
        disable_ligatures=True,
        t2c=_hex_colors(t2c),
        **kw,
    )


# Every video.py so far calls the text helpers T and M.
T: Final = serif
M: Final = mono


def stacked(
    *lines: str, size: float = 36, color: ParsableManimColor = WHITE, buff: float = 0.2
) -> VGroup:
    r"""Return centered lines of text: Text with "\n" aligns its lines left."""
    return VGroup(*[serif(s, size, color) for s in lines]).arrange(DOWN, buff=buff)


def _hex_colors(
    t2c: Mapping[str, ParsableManimColor] | None,
) -> dict[str, str] | None:
    if t2c is None:
        return None
    return {k: ManimColor(v).to_hex() for k, v in t2c.items()}


def num(x: float, d: int = 2) -> str:
    """Format x with d decimals and a real minus sign."""
    return f"{x:.{d}f}".replace("-", MINUS)


def part(mob: Mobject, s: str, w: str) -> Mobject:
    """Return the glyphs of substring w inside the Text mob built from s.

    Manim 0.22 keeps an empty submobject per space, so indexes match the string;
    older versions dropped them.
    """
    i = s.index(w)
    if len(mob) == len(s):
        return mob[i : i + len(w)]
    a = len("".join(s[:i].split()))
    return mob[a : a + len("".join(w.split()))]


def sub(
    base: str, index: object, size: float = 36, color: ParsableManimColor = WHITE
) -> VGroup:
    """Return base with a subscript index: CMU Serif has no subscript digits."""
    b, i = serif(base, size, color), serif(str(index), size * 0.65, color)
    i.next_to(b, RIGHT, buff=0.03).align_to(b, DOWN).shift(DOWN * size / 400)
    return VGroup(b, i)


def sup(
    base: str, exp: object, size: float = 36, color: ParsableManimColor = WHITE
) -> VGroup:
    """Return base with a superscript exponent: CMU Serif has only 1, 2 and 3."""
    b, e = serif(base, size, color), serif(str(exp), size * 0.65, color)
    e.next_to(b, RIGHT, buff=0.03).align_to(b, UP).shift(UP * size / 300)
    return VGroup(b, e)


def tick(color: ParsableManimColor = GREEN, s: float = 0.4) -> VMobject:
    """Return a drawn check mark: CMU Serif has no check mark glyph."""
    corners = [(-0.5, 0.05, 0), (-0.15, -0.35, 0), (0.5, 0.45, 0)]
    return VMobject().set_points_as_corners(corners).scale(s).set_stroke(color, 6)


def cross(color: ParsableManimColor = RED, s: float = 0.4) -> VGroup:
    """Return a drawn cross: CMU Serif has no ballot X glyph."""
    lines = Line((-0.4, -0.4, 0), (0.4, 0.4, 0)), Line((-0.4, 0.4, 0), (0.4, -0.4, 0))
    return VGroup(*lines).scale(s).set_stroke(color, 6)


def person(color: ParsableManimColor = BLUE_B, s: float = 1.0) -> VGroup:
    """Return a filled head-and-shoulders figure."""
    head = Circle(0.2, stroke_width=0, fill_color=color, fill_opacity=1)
    body = Sector(
        radius=0.36, angle=PI, stroke_width=0, fill_color=color, fill_opacity=1
    )
    return VGroup(head.shift(UP * 0.3), body.shift(DOWN * 0.32)).scale(s)


def window(
    w: float, h: float, url: str = "", color: ParsableManimColor = GREY_B
) -> VGroup:
    """Return a browser window outline: frame, title bar with 3 dots, address."""
    frame = RoundedRectangle(corner_radius=0.12, width=w, height=h).set_stroke(color, 2)
    y = frame.get_top()[1] - 0.4
    bar = Line((frame.get_left()[0], y, 0), (frame.get_right()[0], y, 0))
    bar.set_stroke(color, 2)
    dots = VGroup(*[Dot(radius=0.045, color=c) for c in (RED_C, YELLOW_C, GREEN_C)])
    dots.arrange(RIGHT, buff=0.09).move_to((frame.get_left()[0] + 0.32, y + 0.2, 0))
    parts = VGroup(frame, bar, dots)
    if url:
        parts.add(mono(url, 18, GREY_B).next_to(dots, RIGHT, buff=0.25))
    return parts


def packet(s: str, color: ParsableManimColor = YELLOW, size: float = 22) -> VGroup:
    """Return a message in flight: monospace text on an opaque plate."""
    t = mono(s, size, color)
    plate = SurroundingRectangle(
        t,
        buff=0.1,
        corner_radius=0.08,
        color=color,
        fill_color=BLACK,
        fill_opacity=1,
        stroke_width=2,
    )
    return VGroup(plate, t)


def fade_to(
    mob: Mobject, opacity: float = 0.25, **kw: Unpack[AnimationOptions]
) -> MoveToTarget:
    """Return an animation that dims mob in place.

    mob.animate.set_opacity() also sets the fill of outlines (frames, boxes) and
    turns them into grey slabs.
    """
    target = mob.generate_target()
    for m in target.family_members_with_points():
        m.set_stroke(opacity=opacity)
        if m.get_fill_opacity() > 0:
            m.set_fill(opacity=opacity)
    return MoveToTarget(mob, **kw)


def lit(
    line: Mobject, s: str, word: str, color: ParsableManimColor = YELLOW
) -> MoveToTarget:
    """Return an animation that turns a dim code line white, with word in color.

    line is the Text built from string s.
    """
    target = line.generate_target()
    target.set_color(WHITE)
    part(target, s, word).set_color(color)
    return MoveToTarget(line)


def server(color: ParsableManimColor = GREY_B, s: float = 1.0) -> VGroup:
    """Return a server rack: three units, each with a green light."""
    units = VGroup(
        *[
            RoundedRectangle(corner_radius=0.06, width=1.3, height=0.36).set_stroke(
                color, 2
            )
            for _ in range(3)
        ]
    )
    units.arrange(DOWN, buff=0.08)
    leds = VGroup(
        *[Dot(u.get_left() + RIGHT * 0.18, radius=0.04, color=GREEN) for u in units]
    )
    slots = VGroup(
        *[
            Line(u.get_center() + LEFT * 0.15, u.get_right() + LEFT * 0.15).set_stroke(
                color, 2
            )
            for u in units
        ]
    )
    return VGroup(units, leds, slots).scale(s)


def bubble(
    s: str,
    color: ParsableManimColor = BLUE_B,
    size: float = 24,
    width: float | None = None,
) -> VGroup:
    r"""Return a chat message: text on a tinted rounded plate.

    Use "\n" for line breaks; width caps the text width.
    """
    t = serif(s, size, WHITE)
    if width and t.width > width:
        t.scale_to_fit_width(width)
    plate = SurroundingRectangle(
        t,
        buff=0.2,
        corner_radius=0.18,
        color=color,
        fill_color=color,
        fill_opacity=0.18,
        stroke_width=2,
    )
    return VGroup(plate, t)


def database(
    color: ParsableManimColor = GREY_B, w: float = 1.4, h: float = 1.5
) -> VGroup:
    """Return a database cylinder: top ellipse, side walls and two bands."""
    rx, ry = w / 2, w / 7

    def rim(y: float, start: float = PI, end: float = TAU) -> ParametricFunction:
        return ParametricFunction(
            lambda t: np.array([rx * np.cos(t), y + ry * np.sin(t), 0]),
            t_range=(start, end),
        )

    walls = [Line((x, h / 2, 0), (x, -h / 2, 0)) for x in (-rx, rx)]
    bands = [rim(y) for y in (h / 6, -h / 6, -h / 2)]
    return VGroup(rim(h / 2, 0, TAU), *bands, *walls).set_stroke(color, 2)


def flow(
    a: Point3DLike,
    b: Point3DLike,
    n: int,
    color: ParsableManimColor,
    side: float = 0.2,
) -> tuple[ValueTracker, VGroup]:
    """Return (tracker, squares): a steady stream of n squares from a to b.

    Grow the tracker to move them:
    self.play(phase.animate(rate_func=linear).increment_value(0.35 * t), run_time=t).
    The squares fade in and out at the ends. Call clear_updaters() on one square
    before you animate it alone (a lost packet).
    """
    phase = ValueTracker(0)
    start, end = np.array(a, float), np.array(b, float)
    sqs = VGroup(
        *[
            Square(side, stroke_width=0, fill_color=color, fill_opacity=1)
            for _ in range(n)
        ]
    )

    def place(m: Mobject, i: int) -> None:
        x = (phase.get_value() + i / n) % 1
        m.move_to(start + (end - start) * x).set_fill(
            opacity=min(1, 6 * x, 6 * (1 - x))
        )

    for i, m in enumerate(sqs):
        m.add_updater(lambda m, i=i: place(m, i))
        place(m, i)
    return phase, sqs


def unit(angle: float) -> npt.NDArray[np.float64]:
    """Return the unit vector at angle radians in the screen plane."""
    return np.array([np.cos(angle), np.sin(angle), 0])


def backed(mob: VMobject, opacity: float = 0.9, buff: float = 0.12) -> VGroup:
    """Return mob on a black plate, for labels over grids, graphs and dot clouds."""
    return VGroup(BackgroundRectangle(mob, fill_opacity=opacity, buff=buff), mob)


def page(
    w: float = 0.42, h: float = 0.56, color: ParsableManimColor = GREY_B
) -> VGroup:
    """Return a document icon: an outline with four text lines."""
    r = Rectangle(width=w, height=h, stroke_color=color, stroke_width=2)
    lines = VGroup(*[Line(ORIGIN, RIGHT * w * f) for f in (0.65, 0.65, 0.65, 0.35)])
    lines.arrange(DOWN, buff=h * 0.13, aligned_edge=LEFT).move_to(r).set_stroke(
        color, 1.5
    )
    return VGroup(r, lines)


def box(
    label: str,
    w: float = 2.2,
    h: float = 1.0,
    color: ParsableManimColor = BLUE,
    size: float = 30,
) -> VGroup:
    r"""Return a tinted rounded box with a centered label; "\n" gives centered lines."""
    r = RoundedRectangle(
        corner_radius=0.15,
        width=w,
        height=h,
        stroke_color=color,
        fill_color=color,
        fill_opacity=0.15,
    )
    if "\n" in label:
        text: VGroup | Text = stacked(*label.split("\n"), size=size, buff=0.12)
    else:
        text = serif(label, size)
    return VGroup(r, text.move_to(r))


def heat(v: float) -> ManimColor:
    """Return the cell color for v: blue positive, red negative, grey near 0."""
    return interpolate_color(GREY_E, BLUE if v > 0 else RED, min(abs(v), 1))


def cells(vals: Iterable[float], side: float = 0.22) -> VGroup:
    """Return a vector as a row of colored squares: blue positive, red negative."""
    squares = [
        Square(side, stroke_width=1, stroke_color=GREY_B).set_fill(heat(v), 1)
        for v in vals
    ]
    return VGroup(*squares).arrange(RIGHT, buff=0)


def column(
    entries: Iterable[str], color: ParsableManimColor = WHITE, size: float = 32
) -> VGroup:
    """Return a column vector with square brackets around the entries."""
    col = VGroup(*[serif(e, size, color) for e in entries]).arrange(DOWN, buff=0.2)
    h = col.height + 0.3
    lb = VMobject().set_points_as_corners(
        [
            RIGHT * 0.15 + UP * h / 2,
            UP * h / 2,
            DOWN * h / 2,
            RIGHT * 0.15 + DOWN * h / 2,
        ]
    )
    lb.set_stroke(WHITE, 2)
    rb = lb.copy().flip(UP)
    lb.next_to(col, LEFT, buff=0.15)
    rb.next_to(col, RIGHT, buff=0.15)
    return VGroup(lb, col, rb)


def faint_plane(opacity: float = 0.45) -> NumberPlane:
    """Return a dim blue coordinate grid for backgrounds."""
    return NumberPlane(
        background_line_style={
            "stroke_color": BLUE_D,
            "stroke_width": 1.5,
            "stroke_opacity": opacity,
        }
    )


class Narrated(Scene):
    """A scene whose animations wait for words in its narration clips."""

    key: str
    t0: float

    @override
    def setup(self) -> None:
        # build.py renders scenes in parallel; in a shared media/texts two scenes
        # building the same Text write and unlink the same <hash>_.svg temp file,
        # and one render fails with FileNotFoundError.
        config.text_dir = str(ROOT / "media" / "texts" / type(self).__name__)

    def voice(self, key: str) -> None:
        """Start clip key and log its TIMELINE line for narration.py."""
        self.key, self.t0 = key, self.time
        # Manim's own audio is only for previewing a single scene's mp4.
        self.add_sound(str(ROOT / "audio" / f"{key}.wav"))
        print(f"TIMELINE {key} {self.t0:.6f}", flush=True)

    def cue(self, word: str, nth: int = 0) -> None:
        """Wait until about when word is spoken, from its offset in the clip text."""
        text = CLIPS[self.key]["text"]
        i = -1
        for _ in range(nth + 1):
            i = text.index(word, i + 1)
        self._until(self.t0 + CLIPS[self.key]["dur"] * i / len(text), word)

    def finish(self, pad: float = 0.4) -> None:
        """Wait for the clip to end, plus pad seconds."""
        self._until(self.t0 + CLIPS[self.key]["dur"] + pad, "end of clip")

    def _until(self, t: float, what: str = "wait") -> None:
        if self.time - t > LATE_AFTER:
            # The animations before this point outlast the speech: the picture lags.
            print(f"LATE {self.key} '{what}' by {self.time - t:.1f}s", flush=True)
        if t - self.time > FRAME:
            self.wait(t - self.time)

    def fade_all(self, run_time: float = 0.6) -> None:
        """Fade out everything on screen and clear the scene."""
        # Not only VMobjects: a LaggedStart of .animate calls adds a plain Group.
        mobs = [m for m in self.mobjects if not isinstance(m, ValueTracker)]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=run_time)
        self.clear()
