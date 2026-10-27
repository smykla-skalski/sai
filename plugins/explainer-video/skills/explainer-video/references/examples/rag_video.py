"""Retrieval augmented generation, 3b1b style. Narration is in script.py.

build.py renders SCENES in order and stitches them. Read the scene you need as a
recipe.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import sys
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np

# Manim does not put the project folder on sys.path.
sys.path.insert(0, str(Path(__file__).parent))
from explainer import (
    MINUS,
    THETA,
    M,
    Narrated,
    T,
    backed,
    box,
    bubble,
    cells,
    column,
    cross,
    database,
    fade_to,
    faint_plane,
    lit,
    num,
    page,
    part,
    person,
    stacked,
    tick,
    unit,
    window,
)
from manim import (
    BLACK,
    BLUE,
    BLUE_B,
    BLUE_D,
    DL,
    DOWN,
    DR,
    GOLD,
    GREEN,
    GREY_B,
    GREY_D,
    LEFT,
    ORIGIN,
    PI,
    PURPLE_B,
    RED,
    RIGHT,
    TEAL,
    UL,
    UP,
    UR,
    WHITE,
    YELLOW,
    Arc,
    Arrow,
    Circle,
    Circumscribe,
    Create,
    DashedLine,
    DashedVMobject,
    Dot,
    Ellipse,
    FadeIn,
    FadeOut,
    FadeTransform,
    GrowArrow,
    GrowFromCenter,
    GrowFromEdge,
    Indicate,
    LaggedStart,
    Line,
    MoveAlongPath,
    NumberPlane,
    Polygon,
    Rectangle,
    ReplacementTransform,
    RightAngle,
    RoundedRectangle,
    SurroundingRectangle,
    Text,
    Transform,
    ValueTracker,
    VGroup,
    VMobject,
    Write,
    always_redraw,
    linear,
)
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from manim import ParsableManimColor

SCENES: Final = [
    "Hook",
    "OpenBook",
    "Chunks",
    "Embed",
    "Query",
    "Cosine",
    "Prompt",
    "Failure",
    "Hybrid",
    "Dials",
    "Recap",
]
TIMES: Final = "\N{MULTIPLICATION SIGN}"
QUESTION: Final = "Can I get a refund on an annual plan?"
CLUSTERS: Final = {  # topic: (center, color, side of its label)
    "refunds": ((-3.0, -0.8), TEAL, LEFT),
    "passwords": ((3.6, 0.6), GOLD, RIGHT),
    "shipping": ((2.2, -2.2), PURPLE_B, RIGHT),
}
# Two refund chunks that share no words.
CHUNK_A: Final = np.array([-3.4, -0.35, 0])
CHUNK_B: Final = np.array([-2.6, -1.25, 0])
Q_POS: Final = np.array([-2.35, -0.55, 0])  # where the embedded question lands

# Cosine draws its vectors from TAIL, LENGTH long, at the angles of its 2D examples.
TAIL: Final = np.array([-2.6, -2.4, 0])
LENGTH: Final = 4.0
Q_ANGLE: Final = np.arctan2(0.6, 0.8)  # the question (0.8, 0.6)
R_ANGLE: Final = np.arctan2(0.8, 0.6)  # the refund chunk (0.6, 0.8)
P_ANGLE: Final = np.arctan2(0.8, -0.6)  # the password chunk (-0.6, 0.8)

INSTRUCTION: Final = [
    "Answer using only the sources below.",
    "Name the source you use, like [1].",
    "If the sources do not say, answer: I don't know.",
]
SOURCES: Final = [  # file, the chunk retrieved from it
    ("refund-policy.md", "Annual plans can be refunded within 30 days of purchase."),
    ("billing-faq.md", "Monthly plans renew on the first day of each month."),
    ("plans.md", "The annual plan costs 20% less than monthly billing."),
]
PROMPT_YS: Final = [2.45, 1.95, 1.45, 0.65, 0.2, -0.4, -0.85, -1.45, -1.9, -2.7]

HITS: Final = [  # vector search for E417: page title, score, row y
    ("E412: disk quota exceeded", 0.91, 0.5),
    ("Error codes: overview", 0.89, -0.2),
    ("Timeouts and retries", 0.87, -0.9),
    ("E417: unknown region", 0.86, -2.2),
]


def halves(active: int | None = None) -> tuple[VGroup, Line]:
    """Return the header of RAG's two halves and an underline for the active one."""
    labels = [
        T("1  ahead of time", 28).move_to((-3.6, 3.45, 0)),
        T("2  for every question", 28).move_to((3.6, 3.45, 0)),
    ]
    # active is the number of the half the scene is about; None greys neither.
    for number, label in enumerate(labels, start=1):
        if active and number != active:
            label.set_color(GREY_D)
    on = labels[(active or 1) - 1]
    under = (
        Line(LEFT, RIGHT)
        .set_stroke(YELLOW, 3)
        .set_width(on.width)
        .next_to(on, DOWN, buff=0.1)
    )
    return VGroup(backed(labels[0]), backed(labels[1])), under


def clusters() -> tuple[dict[str, VGroup], VGroup]:
    """Return the dots of each topic in CLUSTERS, and their labels."""
    rng = np.random.default_rng(4)
    dots: dict[str, VGroup] = {}
    labels = VGroup()
    for name, ((x, y), color, side) in CLUSTERS.items():
        pts = [
            np.array([x, y, 0])
            + np.append(np.clip(rng.normal(0, 0.42, 2), -0.8, 0.8), 0)
            for _ in range(7)
        ]
        if name == "refunds":
            pts[:2] = [CHUNK_A, CHUNK_B]
        dots[name] = VGroup(*[Dot(p, radius=0.08, color=color) for p in pts])
        labels.add(backed(T(name, 26, color)).next_to(dots[name], side, buff=0.2))
    return dots, labels


def source_card(
    n: int, name: str, color: ParsableManimColor = TEAL, w: float = 3.6
) -> VGroup:
    """Return a numbered source file name on an opaque plate."""
    r = RoundedRectangle(corner_radius=0.1, width=w, height=0.6)
    r.set_stroke(color, 2).set_fill(BLACK, 1)
    return VGroup(r, M(f"[{n}] {name}", 22, color).move_to(r))


def closed_book(color: ParsableManimColor = GREY_B) -> VGroup:
    """Return a closed book: a cover with a spine."""
    r = Rectangle(width=0.9, height=1.2).set_stroke(color, 3)
    spine = Line(r.get_corner(UL) + RIGHT * 0.14, r.get_corner(DL) + RIGHT * 0.14)
    return VGroup(r, spine.set_stroke(color, 3))


def open_book(color: ParsableManimColor = GREY_B) -> VGroup:
    """Return an open book: two pages with three lines each."""
    left = Polygon((-0.9, 0.5, 0), (0, 0.4, 0), (0, -0.5, 0), (-0.9, -0.4, 0))
    left.set_stroke(color, 3)
    rows = VGroup(
        *[Line((-0.75, y, 0), (-0.15, y - 0.07, 0)) for y in (0.25, 0.05, -0.15)]
    ).set_stroke(color, 2)
    return VGroup(
        left,
        left.copy().flip(UP, about_point=ORIGIN),
        rows,
        rows.copy().flip(UP, about_point=ORIGIN),
    )


def text_lines(
    n: int,
    width: float,
    seed: int,
    color: ParsableManimColor = GREY_B,
    buff: float = 0.2,
) -> VGroup:
    """Return n left-aligned lines of random length that stand for text."""
    rng = np.random.default_rng(seed)
    lines = VGroup(
        *[Line(ORIGIN, RIGHT * width * rng.uniform(0.55, 1)) for _ in range(n)]
    )
    return lines.arrange(DOWN, buff=buff, aligned_edge=LEFT).set_stroke(color, 2)


def ranked(
    items: Sequence[str],
    x: float,
    y0: float,
    colors: Mapping[str, ParsableManimColor] | None = None,
) -> tuple[VGroup, VGroup]:
    """Return rank numbers and titles apart, so a re-sort moves only the titles."""
    nums, rows = VGroup(), VGroup()
    for i, s in enumerate(items):
        y = y0 - i * 0.6
        nums.add(T(f"{i + 1}", 28, GREY_B).move_to((x, y, 0)))
        rows.add(
            T(s, 28, (colors or {}).get(s, WHITE)).move_to(
                (x + 0.45, y, 0), aligned_edge=LEFT
            )
        )
    return nums, rows


def vector(angle: float, color: ParsableManimColor) -> Arrow:
    """Return a Cosine vector: an arrow from TAIL at angle."""
    return Arrow(
        TAIL,
        TAIL + LENGTH * unit(angle),
        buff=0,
        color=color,
        stroke_width=6,
        max_tip_length_to_length_ratio=0.07,
    )


def cos_readout(angle: float) -> VGroup:
    """Return the cos θ readout for the angle between the question and angle."""
    # Rounding leaves -0.0 for a tiny negative cosine; adding 0.0 drops the sign.
    c = round(np.cos(angle - Q_ANGLE), 2) + 0.0
    return backed(T(f"cos {THETA} = {num(c)}", 36)).move_to((-4.0, 2.6, 0))


def meter(
    k: ValueTracker,
    share: Callable[[float], float],
    y: float,
    color: ParsableManimColor,
) -> Rectangle:
    """Return a bar that redraws to share(k) of its full width."""
    return always_redraw(
        lambda: Rectangle(
            width=max(0.02, 6.4 * share(k.get_value())),
            height=0.36,
            stroke_width=0,
            fill_color=color,
            fill_opacity=0.85,
        ).move_to((-1.2, y, 0), aligned_edge=LEFT)
    )


class Hook(Narrated):
    """A chatbot answers a refund question at once, and wrongly."""

    @override
    def construct(self) -> None:
        win = window(9.4, 5.6, "help.example.com")
        ask = bubble(QUESTION, BLUE_B, 28).move_to((4.3, 1.1, 0), aligned_edge=RIGHT)
        reply = bubble(
            "Yes! Annual plans can be refunded\nwithin 90 days, no questions asked.",
            GREY_B,
            28,
        )
        reply.move_to((-4.3, -0.6, 0), aligned_edge=LEFT)
        no = cross(s=0.5).next_to(reply, RIGHT, buff=0.4)

        self.voice("hook_1")
        self.play(FadeIn(win), run_time=0.8)
        self.cue("simple question")
        self.play(FadeIn(ask, shift=UP * 0.2), run_time=0.6)
        self.cue("Can I get")
        self.play(Indicate(ask, color=BLUE_B, scale_factor=1.04), run_time=0.6)
        self.cue("answers at once")
        self.play(FadeIn(reply, shift=UP * 0.2), run_time=0.6)
        self.cue("wrong")
        self.play(Create(no), reply[0].animate.set_stroke(RED), run_time=0.5)
        self.finish()

        self.voice("hook_2")
        chat = VGroup(win, ask, reply, no)
        model = box("language model", 3.4, 1.2, BLUE, 32).move_to((0, -0.6, 0))
        self.play(
            chat.animate.scale(0.45).move_to((-4.5, 2.4, 0)),
            FadeIn(model),
            run_time=0.9,
        )
        self.cue("refund policy")
        doc = (
            VGroup(page(1.5, 2.0), M("refund-policy.md", 20, TEAL))
            .arrange(DOWN, buff=0.2)
            .move_to((4.7, -0.6, 0))
        )
        wall = DashedLine((2.75, 1.0, 0), (2.75, -2.3, 0), color=RED)
        self.play(FadeIn(doc), Create(wall), run_time=0.8)
        self.cue("learned in training")
        stack = VGroup(
            *[page(1.2, 1.6).shift((RIGHT + UP) * 0.12 * i) for i in range(4)]
        ).move_to((-4.6, -0.5, 0))
        stack_l = stacked(
            "public text,", "months ago", size=24, color=GREY_B, buff=0.1
        ).next_to(stack, DOWN, buff=0.25)
        feed = Arrow(stack.get_right(), model.get_left(), buff=0.25, color=GREY_B)
        self.play(FadeIn(stack), FadeIn(stack_l), GrowArrow(feed), run_time=0.9)
        self.cue("guesses")
        q = T("?", 80, YELLOW).next_to(model, UP, buff=0.3)
        self.play(FadeIn(q, scale=1.5), run_time=0.5)
        self.cue("How can it")
        title = stacked(
            "How can it answer from", "your own documents?", size=54, color=YELLOW
        )
        self.play(
            *[FadeOut(m) for m in (chat, model, doc, wall, stack, stack_l, feed, q)],
            run_time=0.4,
        )
        self.play(Write(title), run_time=1.0)
        self.finish()
        self.fade_all()


class OpenBook(Narrated):
    """Open-book RAG against pasting every document or training on them."""

    @override
    def construct(self) -> None:
        divider = DashedLine(UP * 2.9, DOWN * 3.2, color=GREY_D)
        lp = person(BLUE_B, 1.3).move_to((-3.6, -1.2, 0))
        rp = person(BLUE_B, 1.3).move_to((3.6, -1.2, 0))
        lh = T("closed book", 44).move_to((-3.6, 2.4, 0))
        rh = T("open book", 44).move_to((3.6, 2.4, 0))
        closed = closed_book().move_to((-5.4, -1.3, 0))
        no = cross(s=0.7).move_to(closed)
        cloud = VGroup(
            Ellipse(width=2.2, height=1.1).set_stroke(GREY_B, 2),
            T("memory", 28, GREY_B),
        ).move_to((-1.9, 0.6, 0))
        puffs = VGroup(Circle(0.07), Circle(0.11)).set_stroke(GREY_B, 2)
        puffs[0].move_to((-2.95, -0.35, 0))
        puffs[1].move_to((-2.6, -0.05, 0))
        opened = open_book().move_to((5.6, -1.3, 0))
        sheet = page(0.9, 1.2).move_to((1.9, -1.3, 0))
        ok = tick(s=0.5).move_to(sheet)

        self.voice("book_1")
        self.play(Create(divider), FadeIn(lp), FadeIn(rp), run_time=0.8)
        self.cue("closed-book")
        self.play(Write(lh), FadeIn(closed), Create(no), run_time=0.8)
        self.cue("from memory")
        self.play(FadeIn(puffs), FadeIn(cloud), run_time=0.6)
        self.cue("open-book")
        self.play(Write(rh), FadeIn(opened), run_time=0.8)
        self.cue("look up")
        look = Arrow(opened.get_left(), rp.get_right(), buff=0.15, color=YELLOW)
        self.play(Indicate(opened, color=YELLOW), GrowArrow(look), run_time=0.8)
        self.cue("then you answer")
        self.play(FadeIn(sheet), Create(ok), run_time=0.6)
        self.finish()
        self._acronym()
        self._paste_all()
        self._train()
        self.fade_all()

    def _acronym(self) -> None:
        self.voice("book_2")
        s = "Retrieval Augmented Generation"
        title = T(s, 60).move_to(UP * 1.6)
        self.play(*[FadeOut(m) for m in self.mobjects], Write(title), run_time=1.5)
        self.cue("or RAG")
        firsts = [
            part(title, s, w)[0] for w in ("Retrieval", "Augmented", "Generation")
        ]
        rag = T("RAG", 80, YELLOW).move_to(UP * 0.1)
        self.play(
            *[f.animate.set_color(YELLOW) for f in firsts],
            *[ReplacementTransform(f.copy(), rag[i]) for i, f in enumerate(firsts)],
            run_time=1.0,
        )
        steps = VGroup(
            *[box(w, 3.0, 1.0, BLUE, 34) for w in ("Retrieve", "Augment", "Generate")]
        )
        steps.arrange(RIGHT, buff=1.4).move_to(DOWN * 1.9)
        for b in steps:
            b[1][0].set_color(YELLOW)
        arrows = [
            Arrow(a.get_right(), b.get_left(), buff=0.15) for a, b in pairwise(steps)
        ]
        for i, word in enumerate(("Retrieve the", "Augment the", "generate the")):
            self.cue(word)
            self.play(
                FadeIn(steps[i], shift=UP * 0.2),
                *([GrowArrow(arrows[i - 1])] if i else []),
                run_time=0.6,
            )
        self.finish()

    def _paste_all(self) -> None:
        self.voice("book_3")
        prompt = Rectangle(width=3.2, height=4.2).set_stroke(GREY_B, 2)
        prompt.move_to((2.8, -0.3, 0))
        prompt_l = T("prompt", 30, GREY_B).next_to(prompt, DOWN, buff=0.2)
        stack = VGroup(
            *[page(1.1, 1.45).shift((RIGHT + UP) * 0.1 * i) for i in range(6)]
        ).move_to((-4.2, 0.3, 0))
        stack_l = T("10,000 pages", 30).next_to(stack, DOWN, buff=0.3)
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            FadeIn(prompt),
            FadeIn(prompt_l),
            FadeIn(stack),
            FadeIn(stack_l),
            run_time=1.0,
        )
        self.cue("Ten thousand")
        slots = [
            (2.8 + dx, y, 0)
            for y in (1.25, 0.2, -0.85, -1.9, 2.3, 3.2)
            for dx in (-1.1, -0.37, 0.37, 1.1)
        ]
        pages = [page(0.6, 0.8).move_to(stack) for _ in slots]
        self.add(*pages)
        # A Transform, not .animate: LaggedStart is typed to take Animations.
        fill_up = [
            Transform(p, p.copy().move_to(t)) for p, t in zip(pages, slots, strict=True)
        ]
        self.play(LaggedStart(*fill_up, lag_ratio=0.06), run_time=1.8)
        full = T("does not fit", 28, RED).next_to(prompt, RIGHT, buff=0.35)
        self.play(prompt.animate.set_stroke(RED), FadeIn(full), run_time=0.4)
        self.cue("pay for every word")
        cost_l = T("cost per question", 28, GOLD).move_to((-4.2, -2.3, 0))
        cost = Rectangle(
            width=4.6, height=0.32, stroke_width=0, fill_color=GOLD, fill_opacity=0.8
        ).move_to((-4.2, -2.9, 0))
        self.play(FadeIn(cost_l), GrowFromEdge(cost, LEFT), run_time=1.2)
        self.cue("gets worse")
        lines = text_lines(20, 2.6, 3, buff=0.13).move_to(prompt)
        self.play(
            *[FadeOut(p) for p in pages],
            FadeOut(full),
            prompt.animate.set_stroke(GREY_B),
            FadeIn(lines),
            run_time=1.0,
        )
        self.cue("one line")
        self.play(lines[12].animate.set_stroke(YELLOW, 5), run_time=0.4)
        self.play(Circumscribe(lines[12], color=YELLOW, buff=0.08), run_time=0.8)
        self.finish()

    def _train(self) -> None:
        self.voice("book_4")
        pages = [page(1.0, 1.3).shift((RIGHT + UP) * 0.12 * i) for i in range(3)]
        docs = VGroup(*pages).move_to((-4.6, 0.8, 0))
        docs_l = T("your documents", 26, TEAL).next_to(docs, DOWN, buff=0.25)
        model = box("language model", 3.2, 1.1, BLUE, 30).move_to((0, 0.8, 0))
        feed = Arrow(docs.get_right(), model.get_left(), buff=0.25, color=GREY_B)
        feed_l = T("train", 26, GREY_B).next_to(feed, UP, buff=0.1)
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            FadeIn(docs),
            FadeIn(docs_l),
            FadeIn(model),
            GrowArrow(feed),
            FadeIn(feed_l),
            run_time=1.0,
        )
        self.cue("Training is")
        track = Rectangle(width=3.2, height=0.3).set_stroke(GREY_B, 2)
        track.move_to((0, -0.6, 0))
        fill = Rectangle(
            width=3.2, height=0.3, stroke_width=0, fill_color=BLUE, fill_opacity=0.8
        ).move_to(track)
        slow = T("slow and costly", 26, GREY_B).next_to(track, DOWN, buff=0.25)
        self.play(Create(track), FadeIn(slow), run_time=0.4)
        self.play(GrowFromEdge(fill, LEFT), run_time=1.6, rate_func=linear)
        self.cue("every change")
        again = T("again", 26, YELLOW).next_to(track, RIGHT, buff=0.3)
        self.play(
            pages[-1][1].animate.set_stroke(YELLOW),
            fill.animate.stretch_to_fit_width(0.01, about_edge=LEFT),
            FadeIn(again),
            run_time=0.5,
        )
        self.play(
            fill.animate.stretch_to_fit_width(3.2, about_edge=LEFT),
            run_time=1.2,
            rate_func=linear,
        )
        self.cue("where an answer")
        ans = bubble("within 30 days", GREY_B, 28).move_to((4.6, 0.8, 0))
        where = T("source?", 30, YELLOW).next_to(ans, DOWN, buff=0.3)
        self.play(
            GrowArrow(Arrow(model.get_right(), ans.get_left(), buff=0.15)),
            FadeIn(ans),
            FadeIn(where),
            run_time=0.8,
        )
        self.finish()


class Chunks(Narrated):
    """Cut documents into chunks: too small, too large, and overlapping."""

    @override
    def construct(self) -> None:
        head, under = halves()
        frame = Rectangle(width=2.6, height=4.6).set_stroke(GREY_B, 2)
        frame.move_to((-4.6, -0.6, 0))
        lines = text_lines(15, 2.0, 1, buff=0.26).move_to(frame)
        groups = [VGroup(*lines[3 * i : 3 * i + 3]) for i in range(5)]
        rects = [
            SurroundingRectangle(g, buff=0.15, color=TEAL, corner_radius=0.08)
            for g in groups
        ]

        self.voice("chunk_1")
        self.play(FadeIn(head), run_time=0.8)
        self.cue("ahead of time")
        self.play(Create(under), head[1][1].animate.set_color(GREY_D), run_time=0.6)
        self.cue("Take every")
        self.play(FadeIn(frame), FadeIn(lines), run_time=0.6)
        self.cue("cut it")
        self.play(*[Create(r) for r in rects], run_time=0.5)
        chunks = [VGroup(r, g) for r, g in zip(rects, groups, strict=True)]
        self.play(
            FadeOut(frame),
            *[c.animate.move_to((1.4, 2.3 - 1.2 * i, 0)) for i, c in enumerate(chunks)],
            run_time=1.0,
        )
        self.finish()
        self._overlap(self._sizes(chunks))
        self.fade_all()

    def _sizes(self, chunks: list[VGroup]) -> list[VMobject]:
        self.voice("chunk_2")
        self.cue("only says")
        t = T("“within 30 days”", 32)
        tiny = VGroup(
            SurroundingRectangle(t, buff=0.25, color=TEAL, corner_radius=0.1), t
        ).move_to((-4.4, 0.4, 0))
        small_l = T("too small", 30, GREY_B).next_to(tiny, UP, buff=0.4)
        self.play(
            *[FadeOut(c) for c in chunks], FadeIn(tiny), FadeIn(small_l), run_time=0.7
        )
        self.cue("lost what")
        what = T("about what?", 30, YELLOW).next_to(tiny, DOWN, buff=0.4)
        self.play(FadeIn(what, shift=UP * 0.2), run_time=0.5)
        self.cue("huge chunk")
        colors = [TEAL, GOLD, PURPLE_B, BLUE_B]
        big_lines = text_lines(16, 2.6, 2, buff=0.16)
        for i, line in enumerate(big_lines):
            line.set_stroke(colors[i // 4])
        big = VGroup(
            RoundedRectangle(corner_radius=0.12, width=3.4, height=4.0).set_stroke(
                TEAL, 2
            ),
            big_lines,
        ).move_to((0.8, -0.5, 0))
        big_lines.move_to(big[0])
        big_l = T("too large", 30, GREY_B).next_to(big, UP, buff=0.3)
        self.play(FadeIn(big), FadeIn(big_l), run_time=0.8)
        self.cue("everything a little")
        topics = ("refunds", "passwords", "shipping", "invoices")
        chips = VGroup(*[T(n, 26, c) for n, c in zip(topics, colors, strict=True)])
        chips.arrange(DOWN, buff=0.45).move_to((5.3, -0.4, 0))
        links = VGroup(
            *[
                Line(big.get_right() + UP * (0.9 - 0.6 * i), c.get_left() + LEFT * 0.15)
                for i, c in enumerate(chips)
            ]
        )
        links.set_stroke(GREY_B, 2, opacity=0.6)
        self.play(FadeIn(chips), Create(links), run_time=0.9)
        self.cue("nothing well")
        weak = T("a weak match for all", 26, GREY_B).next_to(chips, DOWN, buff=0.4)
        self.play(fade_to(links, 0.15), FadeIn(weak), run_time=0.6)
        self.finish()
        return [tiny, small_l, what, big, big_l, chips, links, weak]

    def _overlap(self, old: list[VMobject]) -> None:
        self.voice("chunk_3")
        self.play(*[FadeOut(m) for m in old], run_time=0.5)
        self.cue("few hundred words")
        mid = VGroup(
            RoundedRectangle(corner_radius=0.1, width=2.6, height=1.3).set_stroke(
                TEAL, 2
            ),
            text_lines(4, 2.0, 5, buff=0.2),
        )
        mid[1].move_to(mid[0])
        mid.move_to((-1.6, 1.7, 0))
        mid_l = T("a few hundred words", 30).next_to(mid, RIGHT, buff=0.4)
        mid_ok = tick(s=0.45).next_to(mid_l, RIGHT, buff=0.3)
        self.play(FadeIn(mid), FadeIn(mid_l), Create(mid_ok), run_time=0.7)
        self.cue("overlap")
        s = (
            "… Refunds. Annual plans can be refunded within 30 days of purchase. "
            "Monthly …"
        )
        strip = T(s, 26).move_to(DOWN * 0.9)
        r1 = SurroundingRectangle(
            part(strip, s, "… Refunds. Annual plans can be refunded"),
            buff=0.18,
            color=TEAL,
            corner_radius=0.06,
        )
        r2 = SurroundingRectangle(
            part(
                strip,
                s,
                "Annual plans can be refunded within 30 days of purchase. Monthly …",
            ),
            buff=0.1,
            color=BLUE_B,
            corner_radius=0.06,
        )
        r2.stretch_to_fit_height(r1.height + 0.32)
        l1 = T("chunk 1", 24, TEAL).next_to(r1, UP, buff=0.35).align_to(r1, LEFT)
        l2 = T("chunk 2", 24, BLUE_B).next_to(r2, DOWN, buff=0.15).align_to(r2, RIGHT)
        self.play(
            FadeIn(strip), Create(r1), Create(r2), FadeIn(l1), FadeIn(l2), run_time=1.0
        )
        self.cue("sentence cut")
        sentence = part(
            strip, s, "Annual plans can be refunded within 30 days of purchase."
        )
        edge = DashedLine(
            r1.get_corner(UR) + UP * 0.3, r1.get_corner(DR) + DOWN * 0.6, color=RED
        )
        self.play(sentence.animate.set_color(YELLOW), Create(edge), run_time=0.6)
        self.cue("whole in")
        self.play(
            r2.animate.set_stroke(GREEN, 4),
            Create(tick(s=0.4).next_to(l2, LEFT, buff=0.3)),
            run_time=0.5,
        )
        self.finish()


class Embed(Narrated):
    """Chunks become vectors: similar meaning points the same way."""

    @override
    def construct(self) -> None:
        head, under = halves(1)
        card = VGroup(
            RoundedRectangle(corner_radius=0.1, width=3.4, height=1.5).set_stroke(
                TEAL, 2
            ),
            M("refund-policy.md", 18, TEAL),
            stacked(
                "Annual plans can be refunded",
                "within 30 days of purchase.",
                size=18,
                buff=0.08,
            ),
        )
        card[1].move_to(card[0]).shift(UP * 0.4)
        card[2].scale_to_fit_width(min(card[2].width, 3.0)).move_to(card[0]).shift(
            DOWN * 0.15
        )
        card.move_to((-4.9, 1.0, 0))
        model = box("embedding model", 3.2, 1.0, BLUE, 26).move_to((-1.2, 1.0, 0))
        vec = cells([0.4, -0.7, 0.1, 0.9, -0.3, 0.6, -0.9, 0.2], 0.32)
        vec.move_to((2.9, 1.0, 0))
        a1 = Arrow(card.get_right(), model.get_left(), buff=0.12)
        a2 = Arrow(model.get_right(), vec.get_left(), buff=0.15)
        numbers = M(f"[0.12, {MINUS}0.53, 0.08, …, 0.34]", 22)
        numbers.next_to(vec, DOWN, buff=0.3)
        hundreds = T("hundreds of numbers", 24, GREY_B).next_to(numbers, DOWN, buff=0.2)

        self.voice("emb_1")
        self.play(
            FadeIn(head),
            FadeIn(under),
            FadeIn(card),
            FadeIn(model),
            GrowArrow(a1),
            run_time=0.8,
        )
        self.cue("a vector")
        self.play(GrowArrow(a2), FadeIn(vec, shift=RIGHT * 0.3), run_time=0.8)
        self.cue("hundreds of numbers")
        self.play(FadeIn(numbers), FadeIn(hundreds), run_time=0.6)
        self.cue("similar meaning")
        plane = faint_plane().set_z_index(-1)
        dots, labels = clusters()
        self.play(
            *[FadeOut(m) for m in (card, model, vec, a1, a2, numbers, hundreds)],
            Create(plane),
            run_time=1.0,
        )
        self.play(
            LaggedStart(
                *[GrowFromCenter(d) for g in dots.values() for d in g], lag_ratio=0.04
            ),
            FadeIn(labels),
            run_time=1.0,
        )
        self.cue("point the same way")
        va, vb = [
            Arrow(ORIGIN, p, buff=0, color=TEAL, stroke_width=5)
            for p in (CHUNK_A, CHUNK_B)
        ]
        self.play(GrowArrow(va), GrowArrow(vb), run_time=0.7)
        self.cue("share no words")
        la = backed(T("“Money back in the first month.”", 24, TEAL))
        la.next_to(CHUNK_A, UP, buff=0.25)
        lb = backed(T("“Refunds are possible for 30 days.”", 24, TEAL))
        lb.next_to(CHUNK_B, DOWN, buff=0.3)
        self.play(FadeIn(la), FadeIn(lb), run_time=0.6)
        self.finish()
        self._index(dots, labels, [va, vb, la, lb])
        self.fade_all()

    def _index(
        self, dots: dict[str, VGroup], labels: VGroup, old: list[VMobject]
    ) -> None:
        self.voice("emb_2")
        self.play(*[FadeOut(m) for m in old], run_time=0.5)
        self.cue("into an index")
        db = database(BLUE_B).move_to((5.6, -1.5, 0))
        db_l = backed(T("vector database", 26, BLUE_B)).next_to(db, UP, buff=0.25)
        self.play(FadeIn(db), FadeIn(db_l), run_time=0.6)
        every = [d for g in dots.values() for d in g]
        # A Transform, not .animate: LaggedStart is typed to take Animations.
        sink = [
            Transform(d, d.copy().move_to(db.get_center()).scale(0.5).set_opacity(0))
            for d in every
        ]
        self.play(LaggedStart(*sink, lag_ratio=0.03), FadeOut(labels), run_time=1.6)
        self.cue("once per chunk")
        once = backed(T("once per chunk", 26, GREY_B)).next_to(db, DOWN, buff=0.25)
        self.play(FadeIn(once), run_time=0.5)
        self.cue("document that changes")
        sheet = page(1.0, 1.3)
        changed = VGroup(sheet, M("refund-policy.md", 18, TEAL))
        changed.arrange(DOWN, buff=0.15).move_to((-4.6, -1.4, 0))
        self.play(FadeIn(changed), run_time=0.4)
        bit = Dot(changed.get_right(), radius=0.09, color=YELLOW)
        self.play(
            sheet[1].animate.set_stroke(YELLOW),
            MoveAlongPath(bit, Line(changed.get_right(), db.get_center())),
            run_time=1.0,
        )
        self.play(FadeOut(bit), Indicate(db, color=YELLOW), run_time=0.5)
        self.finish()


class Query(Narrated):
    """The question is embedded with the same model and lands near its topic."""

    @override
    def construct(self) -> None:
        head, under = halves(2)
        plane = faint_plane().set_z_index(-1)
        dots, labels = clusters()
        ask = bubble(QUESTION, YELLOW, 26).move_to((-3.2, 2.3, 0))
        model = box("embedding model", 2.9, 0.8, BLUE, 26).move_to((1.9, 2.3, 0))
        q = Dot(model.get_bottom(), radius=0.11, color=YELLOW)

        self.voice("query_1")
        self.play(
            FadeIn(head),
            FadeIn(under),
            FadeIn(plane),
            *[FadeIn(g) for g in dots.values()],
            FadeIn(labels),
            run_time=1.0,
        )
        self.cue("Embed the question")
        self.play(FadeIn(ask, shift=DOWN * 0.2), run_time=0.6)
        self.cue("same model")
        self.play(
            GrowArrow(Arrow(ask.get_right(), model.get_left(), buff=0.12)),
            FadeIn(model),
            run_time=0.8,
        )
        self.cue("lands")
        self.play(FadeIn(q, scale=2), run_time=0.3)
        self.play(q.animate.move_to(Q_POS), run_time=0.9)
        self.cue("same topic")
        self.play(
            Create(Circle(radius=1.3, color=YELLOW).move_to((-3.0, -0.75, 0))),
            run_time=0.7,
        )
        self.finish()
        self.fade_all()


class Cosine(Narrated):
    """Cosine similarity: the angle between two arrows, then a worked dot product."""

    @override
    def construct(self) -> None:
        ang = ValueTracker(R_ANGLE)
        plane = faint_plane()
        title = backed(T("cosine similarity", 44)).move_to((-4.0, 3.35, 0))
        qv = vector(Q_ANGLE, YELLOW)
        dv = always_redraw(lambda: vector(ang.get_value(), TEAL))
        arc = always_redraw(
            lambda: Arc(
                radius=0.9,
                start_angle=Q_ANGLE,
                angle=ang.get_value() - Q_ANGLE,
                arc_center=TAIL,
                color=WHITE,
            )
        )
        theta = always_redraw(
            lambda: T(THETA, 32).move_to(
                TAIL + 1.3 * unit((Q_ANGLE + ang.get_value()) / 2)
            )
        )
        readout = always_redraw(lambda: cos_readout(ang.get_value()))

        self.voice("cos_1")
        self.play(Create(plane), run_time=1.0)
        self.play(GrowFromCenter(Dot(TAIL, radius=0.06)), run_time=0.3)
        self.cue("co-sign similarity")
        self.play(Write(title), run_time=1.0)
        self.cue("as an arrow")
        self.play(GrowArrow(qv), GrowArrow(dv), run_time=0.8)
        self.cue("angle between")
        self.play(Create(arc), FadeIn(theta), FadeIn(readout), run_time=0.8)
        self.cue("same direction")
        self.play(ang.animate.set_value(Q_ANGLE), run_time=1.0)
        self.cue("right angle")
        self.play(ang.animate.set_value(Q_ANGLE + PI / 2), run_time=1.0)
        self.finish()
        panel, sums = self._dot_product(ang, qv)
        self._unit_length(panel, sums)
        self.fade_all()

    def _dot_product(self, ang: ValueTracker, qv: Arrow) -> tuple[Rectangle, VGroup]:
        self.voice("cos_2")
        panel = Rectangle(
            width=5.6, height=5.6, stroke_width=0, fill_color=BLACK, fill_opacity=0.92
        ).move_to((4.2, -0.1, 0))
        self.play(ang.animate.set_value(R_ANGLE), FadeIn(panel), run_time=1.0)
        self.cue("question is")
        qc = column(["0.8", "0.6"], YELLOW, 36).move_to((2.7, 1.5, 0))
        ql = backed(T("(0.8, 0.6)", 26, YELLOW)).next_to(qv.get_end(), DOWN, buff=0.2)
        self.play(FadeIn(qc), FadeIn(ql), run_time=0.7)
        self.cue("refund chunk")
        dot = T("·", 60).next_to(qc, RIGHT, buff=0.35)
        dc = column(["0.6", "0.8"], TEAL, 36).next_to(dot, RIGHT, buff=0.35)
        dl = backed(T("(0.6, 0.8)", 26, TEAL))
        dl.next_to(TAIL + LENGTH * unit(R_ANGLE), UP, buff=0.15)
        self.play(FadeIn(dot), FadeIn(dc), FadeIn(dl), run_time=0.7)
        self.cue("Multiply")
        prod = T(f"0.8 {TIMES} 0.6  +  0.6 {TIMES} 0.8", 36).move_to((4.2, 0.1, 0))
        self.play(Write(prod), run_time=1.0)
        self.cue("Point four eight plus")
        s1 = T("=  0.48 + 0.48", 36).next_to(prod, DOWN, buff=0.45)
        s1.align_to(prod, LEFT)
        self.play(FadeIn(s1), run_time=0.6)
        self.cue("nine six")
        s2 = T("=  0.96", 44, GREEN).next_to(s1, DOWN, buff=0.45).align_to(prod, LEFT)
        self.play(FadeIn(s2), run_time=0.5)
        self.play(Circumscribe(s2, color=GREEN), run_time=0.7)
        self.finish()
        return panel, VGroup(qc, dot, dc, prod, s1, s2)

    def _unit_length(self, panel: Rectangle, sums: VGroup) -> None:
        self.voice("cos_3")
        pv = vector(P_ANGLE, GOLD)
        pl = backed(T(f"({MINUS}0.6, 0.8)", 26, GOLD))
        pl.next_to(pv.get_end(), UP, buff=0.15)
        refund = T("refund  0.48 + 0.48 = 0.96", 28, TEAL)
        refund.move_to((1.6, 1.6, 0), aligned_edge=LEFT)
        self.play(
            GrowArrow(pv),
            FadeIn(pl),
            ReplacementTransform(sums, refund),
            run_time=1.0,
        )
        self.cue("scores zero")
        password = T(f"password  {MINUS}0.48 + 0.48 = 0", 28, GOLD)
        password.next_to(refund, DOWN, buff=0.4, aligned_edge=LEFT)
        square = RightAngle(
            Line(TAIL, TAIL + unit(Q_ANGLE)),
            Line(TAIL, TAIL + unit(P_ANGLE)),
            length=0.45,
            color=GOLD,
        )
        self.play(FadeIn(password), Create(square), run_time=0.8)
        self.cue("one unit long")
        ring = DashedVMobject(
            Arc(radius=LENGTH, start_angle=0.25, angle=2.65, arc_center=TAIL),
            num_dashes=40,
        ).set_stroke(GREY_B, 2)
        ring_l = backed(T("length 1", 26, GREY_B))
        ring_l.move_to(TAIL + (LENGTH + 0.4) * unit(1.75))
        self.play(Create(ring), FadeIn(ring_l), run_time=0.8)
        self.cue("just this sum")
        rule = stacked(
            "cosine  =  sum of products", "when lengths are 1", size=30, buff=0.2
        ).next_to(password, DOWN, buff=0.7)
        self.play(FadeIn(rule), run_time=0.7)
        self.cue("millions")
        rng = np.random.default_rng(9)
        angles = rng.uniform(0.3, 2.85, 220)
        many = VGroup(
            *[
                Dot(
                    TAIL + LENGTH * unit(a) + 0.15 * rng.normal(0, 1) * unit(a),
                    radius=0.035,
                    color=GREY_B,
                )
                for a in angles
            ]
        )
        self.play(
            *[FadeOut(m) for m in (panel, refund, password, rule)],
            LaggedStart(*[FadeIn(d) for d in many], lag_ratio=0.004),
            run_time=1.0,
        )
        self.cue("milliseconds")
        near = sorted(range(len(angles)), key=lambda i: abs(angles[i] - Q_ANGLE))[:3]
        top = backed(T("top 3, in milliseconds", 30, YELLOW)).move_to((4.3, 0.9, 0))
        self.play(
            *[many[i].animate.set_color(YELLOW).scale(2.5) for i in near],
            FadeIn(top),
            run_time=0.7,
        )
        self.finish()


class Prompt(Narrated):
    """The top chunks, the prompt built from them, and the cited answer."""

    @override
    def construct(self) -> None:
        plane = faint_plane().set_z_index(-1)
        dots, labels = clusters()
        q = Dot(Q_POS, radius=0.11, color=YELLOW)
        every = [d for g in dots.values() for d in g]
        near = sorted(every, key=lambda d: np.linalg.norm(d.get_center() - Q_POS))[:3]
        cards = VGroup(
            *[
                source_card(i, name, w=3.3)
                for i, (name, _) in enumerate(SOURCES, start=1)
            ]
        )
        cards.arrange(DOWN, buff=0.3).move_to((-4.6, 2.2, 0))

        self.voice("top_1")
        self.play(
            FadeIn(plane),
            *[FadeIn(g) for g in dots.values()],
            FadeIn(labels),
            FadeIn(q),
            run_time=1.0,
        )
        self.cue("three chunks")
        rays = VGroup(
            *[Line(Q_POS, d.get_center(), color=YELLOW, stroke_width=3) for d in near]
        )
        self.play(Create(rays), *[d.animate.scale(1.6) for d in near], run_time=0.8)
        self.cue("pages the model")
        self.play(
            *[
                ReplacementTransform(d.copy(), c)
                for d, c in zip(near, cards, strict=True)
            ],
            run_time=1.2,
        )
        self.cue("nothing else")
        self.play(
            *[fade_to(m, 0.15) for m in (plane, labels, rays, q, *every)], run_time=0.8
        )
        self.finish()
        instruction, prompt, source = self._augment(cards)
        self._instruct(instruction)
        self._generate(prompt, source)
        self.fade_all()

    def _augment(self, cards: VGroup) -> tuple[list[Text], VGroup, tuple[Text, Text]]:
        self.voice("aug_1")
        instruction = [M(s, 21, GREY_B) for s in INSTRUCTION]
        names = [f"[{i}] {name}" for i, (name, _) in enumerate(SOURCES, start=1)]
        heads = [M(s, 21, TEAL) for s in names]
        chunks = [M(chunk, 21) for _, chunk in SOURCES]
        question = M("Question: " + QUESTION, 21, YELLOW, t2c={"Question:": GREY_B})
        lines = VGroup(*instruction)
        for head, chunk in zip(heads, chunks, strict=True):
            lines.add(head, chunk)
        lines.add(question)
        for line, y in zip(lines, PROMPT_YS, strict=True):
            indent = 0.55 if line in chunks else 0
            line.move_to((-5.9 + indent, y, 0), aligned_edge=LEFT)
        frame = SurroundingRectangle(lines, buff=0.3, corner_radius=0.1, color=GREY_B)
        frame_l = T("prompt", 28, GREY_B).next_to(frame, UP, buff=0.15)
        frame_l.align_to(frame, LEFT)
        self.play(
            *[FadeOut(m) for m in self.mobjects if m not in cards.submobjects],
            cards.animate.move_to((5.2, 0.6, 0)),
            FadeIn(frame),
            FadeIn(frame_l),
            run_time=0.7,
        )
        self.cue("an instruction")
        self.play(*[FadeIn(line) for line in instruction], run_time=0.6)
        self.cue("the chunks")
        self.play(
            *[
                ReplacementTransform(c, VGroup(h, b))
                for c, h, b in zip(cards, heads, chunks, strict=True)
            ],
            run_time=1.0,
        )
        self.cue("source number")
        refs = [
            part(head, s, f"[{i}]")
            for i, (head, s) in enumerate(zip(heads, names, strict=True), start=1)
        ]
        self.play(*[r.animate.set_color(GOLD) for r in refs], run_time=0.6)
        self.cue("question at the end")
        self.play(FadeIn(question, shift=UP * 0.15), run_time=0.6)
        self.finish()
        return instruction, VGroup(frame, frame_l, lines), (heads[0], chunks[0])

    def _instruct(self, instruction: list[Text]) -> None:
        self.voice("aug_2")
        self.cue("real work")
        self.play(
            Circumscribe(VGroup(*instruction), color=WHITE, buff=0.1), run_time=0.8
        )
        self.cue("only from")
        self.play(lit(instruction[0], INSTRUCTION[0], "only"), run_time=0.5)
        self.cue("Name the source")
        self.play(lit(instruction[1], INSTRUCTION[1], "Name the source"), run_time=0.5)
        self.cue("do not say")
        self.play(lit(instruction[2], INSTRUCTION[2], "I don't know"), run_time=0.6)
        self.finish()

    def _generate(self, prompt: VGroup, source: tuple[Text, Text]) -> None:
        self.voice("gen_1")
        self.play(prompt.animate.scale(0.6).move_to((-4.1, 0, 0)), run_time=1.0)
        self.cue("generates")
        frame = prompt[0]
        model = box("language\nmodel", 2.2, 1.3, BLUE, 28).move_to((0.3, 0, 0))
        self.play(
            GrowArrow(Arrow(frame.get_right(), model.get_left(), buff=0.1)),
            FadeIn(model),
            run_time=0.8,
        )
        self.cue("takes the facts")
        head, chunk = source
        self.play(chunk.animate.set_color(YELLOW), run_time=0.6)
        self.cue("Annual plans")
        ans = bubble(
            "Annual plans can be refunded\nwithin 30 days of purchase.", GREEN, 24
        ).move_to((4.0, 0, 0))
        ref = M("[1]", 26, GOLD).next_to(ans, DOWN, buff=0.2, aligned_edge=RIGHT)
        self.play(
            GrowArrow(Arrow(model.get_right(), ans.get_left(), buff=0.1)),
            FadeIn(ans),
            FadeIn(ref),
            run_time=1.0,
        )
        self.cue("source one")
        self.play(
            Create(SurroundingRectangle(ref, buff=0.08, color=GOLD)),
            Create(SurroundingRectangle(VGroup(head, chunk), buff=0.08, color=GOLD)),
            Create(tick(s=0.45).next_to(ref, LEFT, buff=0.4)),
            run_time=0.6,
        )
        self.finish()


class Failure(Narrated):
    """Vector search misses an exact error code, and the answer goes wrong."""

    @override
    def construct(self) -> None:
        user = person(BLUE_B, 0.9).move_to((-5.8, 2.6, 0))
        ask = bubble("What does error E417 mean?", YELLOW, 28)
        ask.next_to(user, RIGHT, buff=0.35)

        self.voice("fail_1")
        self.play(FadeIn(user), run_time=0.6)
        self.cue("what does")
        self.play(FadeIn(ask, shift=RIGHT * 0.2), run_time=0.8)
        self.finish()
        self._ranking()
        self._near_strings()
        self._wrong_answer()
        self.fade_all()

    def _ranking(self) -> None:
        self.voice("fail_2")
        head = T("vector search", 32, BLUE).move_to((-5.9, 1.3, 0), aligned_edge=LEFT)
        rows = []
        for i, (s, v, y) in enumerate(HITS):
            bar = Rectangle(
                width=(v - 0.8) * 22,
                height=0.26,
                stroke_width=0,
                fill_color=BLUE,
                fill_opacity=0.8,
            )
            color = YELLOW if s.startswith("E417") else WHITE
            rows.append(
                VGroup(
                    T(f"{i + 1}", 28, GREY_B).move_to((-5.7, y, 0)),
                    T(s, 28, color).move_to((-5.2, y, 0), aligned_edge=LEFT),
                    bar.move_to((0.6, y, 0), aligned_edge=LEFT),
                    T(f"{v:.2f}", 26, GREY_B).move_to((3.4, y, 0), aligned_edge=LEFT),
                )
            )
        fourth = rows[3]
        cut = DashedLine((-6.0, -1.55, 0), (4.3, -1.55, 0), color=RED)
        cut_l = T("top 3", 24, RED).next_to(cut, RIGHT, buff=0.2)

        self.play(FadeIn(head), run_time=0.6)
        for i, word in enumerate(("E four twelve", "overview", "timeouts")):
            self.cue(word)
            self.play(FadeIn(rows[i], shift=RIGHT * 0.2), run_time=0.6)
        self.cue("explains")
        self.play(
            Create(cut), FadeIn(cut_l), FadeIn(fourth, shift=RIGHT * 0.2), run_time=0.8
        )
        self.cue("fourth place")
        self.play(
            Create(SurroundingRectangle(fourth[:2], buff=0.12, color=YELLOW)),
            run_time=0.6,
        )
        self.cue("never reaches")
        self.play(Create(cross(s=0.4).next_to(fourth, RIGHT, buff=0.4)), run_time=0.5)
        self.finish()

    def _near_strings(self) -> None:
        self.voice("fail_3")
        s7, s2 = M("E417", 80, YELLOW), M("E412", 80, RED)
        strings = VGroup(s7, s2).arrange(DOWN, buff=0.6).move_to((-4.3, 0.6, 0))
        self.play(*[FadeOut(m) for m in self.mobjects], FadeIn(strings), run_time=0.8)
        self.cue("exact strings")
        diff = VGroup(
            *[SurroundingRectangle(s[-1], buff=0.08, color=WHITE) for s in (s7, s2)]
        )
        diff_l = T("different strings", 28, GREY_B).next_to(strings, DOWN, buff=0.4)
        self.play(Create(diff), FadeIn(diff_l), run_time=0.6)
        self.cue("E four seventeen and")
        mini = NumberPlane(
            x_range=(-3, 3, 1),
            y_range=(-3, 3, 1),
            x_length=5.6,
            y_length=5.6,
            background_line_style={
                "stroke_color": BLUE_D,
                "stroke_width": 1.5,
                "stroke_opacity": 0.45,
            },
        ).move_to((3.4, 0, 0))
        rng = np.random.default_rng(2)
        others = VGroup(
            *[
                Dot(mini.c2p(*rng.uniform(-2.5, 2.5, 2)), radius=0.06, color=GREY_B)
                for _ in range(14)
            ]
        )
        self.play(Create(mini), FadeIn(others), run_time=1.0)
        self.cue("some error")
        meaning = T("both mean: some error", 28, GREY_B)
        meaning.next_to(diff_l, DOWN, buff=0.3)
        self.play(FadeIn(meaning), run_time=0.5)
        self.cue("their vectors")
        p7, p2 = mini.c2p(0.9, 1.1), mini.c2p(1.05, 0.95)
        d7, d2 = Dot(p7, radius=0.1, color=YELLOW), Dot(p2, radius=0.1, color=RED)
        self.play(
            ReplacementTransform(s7.copy(), d7),
            ReplacementTransform(s2.copy(), d2),
            run_time=1.0,
        )
        self.cue("on top of")
        tag = backed(T("cosine 0.99", 28)).next_to(VGroup(d7, d2), RIGHT, buff=0.3)
        self.play(
            FadeIn(tag),
            Create(Circle(radius=0.45, color=WHITE).move_to(VGroup(d7, d2))),
            run_time=0.6,
        )
        self.finish()

    def _wrong_answer(self) -> None:
        self.voice("fail_4")
        got = VGroup(
            *[
                M(s, 20, TEAL)
                for s in (
                    "[1] E412: disk quota",
                    "[2] Error codes: overview",
                    "[3] Timeouts and retries",
                )
            ]
        )
        got.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        frame = SurroundingRectangle(got, buff=0.3, corner_radius=0.1, color=GREY_B)
        prompt = VGroup(
            frame, got, T("prompt", 26, GREY_B).next_to(frame, UP, buff=0.15)
        ).move_to((-3.8, 0, 0))
        self.play(*[FadeOut(m) for m in self.mobjects], FadeIn(prompt), run_time=0.7)
        self.cue("does not know")
        idk = bubble("I don't know.", GREY_B, 28).move_to((2.8, 1.2, 0))
        self.play(FadeIn(idk, shift=UP * 0.2), run_time=0.6)
        self.cue("Or worse")
        bad = bubble("E417 means your disk\nquota is exceeded.", RED, 28)
        bad.move_to((2.8, -1.1, 0))
        self.play(FadeIn(bad, shift=UP * 0.2), run_time=0.6)
        self.cue("wrong error")
        self.play(Create(cross(s=0.5).next_to(bad, RIGHT, buff=0.35)), run_time=0.4)
        self.finish()


class Hybrid(Narrated):
    """Keyword search, merged ranks and a reranker bring the right page back."""

    @override
    def construct(self) -> None:
        title = T("keyword search", 44, GOLD).move_to((0, 3.3, 0))
        qw = ["What", "does", "error", "E417", "mean?"]
        qrow = VGroup(*[T(w, 36, YELLOW) for w in qw]).arrange(RIGHT, buff=0.4)
        qrow.move_to((0, 0.9, 0))
        cw = ["Error", "E417:", "the", "region", "name", "is", "unknown."]
        crow = VGroup(*[T(w, 32) for w in cw]).arrange(RIGHT, buff=0.3)
        crow.move_to((0, -1.9, 0))
        cbox = SurroundingRectangle(crow, buff=0.25, corner_radius=0.1, color=TEAL)

        self.voice("fix_1")
        self.play(Write(title), FadeIn(qrow), run_time=1.0)
        self.cue("exact words")
        links = VGroup(
            *[
                Line(qrow[a].get_bottom() + DOWN * 0.12, crow[b].get_top() + UP * 0.12)
                for a, b in ((2, 0), (3, 1))
            ]
        ).set_stroke(GOLD, 3)
        self.play(FadeIn(crow), Create(cbox), run_time=0.7)
        self.play(
            Create(links),
            *[w.animate.set_color(GOLD) for w in (crow[0], crow[1])],
            run_time=0.6,
        )
        self.cue("rare words")
        weights = [0.15, 0.15, 0.45, 1.3, 0.3]
        rare = qw.index("E417")
        bars = VGroup(
            *[
                Rectangle(
                    width=0.5,
                    height=h,
                    stroke_width=0,
                    fill_color=GOLD if i == rare else GREY_B,
                    fill_opacity=0.85,
                ).next_to(qrow[i], UP, buff=0.2)
                for i, h in enumerate(weights)
            ]
        )
        weight_l = T("weight", 26, GREY_B).next_to(bars, LEFT, buff=0.5)
        weight_l.align_to(bars, DOWN)
        self.play(
            *[GrowFromEdge(b, DOWN) for b in bars], FadeIn(weight_l), run_time=1.0
        )
        self.cue("count the most")
        self.play(
            Circumscribe(VGroup(qrow[rare], bars[rare]), color=GOLD), run_time=0.8
        )
        self.finish()
        merged, old = self._merge()
        self._rerank(merged, old)
        self.fade_all()

    def _merge(self) -> tuple[tuple[Text, VGroup, VGroup], list[VMobject]]:
        self.voice("fix_2")
        colors = {"E417": YELLOW}
        vh = T("vector search", 32, BLUE).move_to((-3.6, 3.1, 0))
        kh = T("keyword search", 32, GOLD).move_to((3.6, 3.1, 0))
        vn, vr = ranked(["E412", "Overview", "Timeouts", "E417"], -4.9, 2.35, colors)
        kn, kr = ranked(["E417", "Overview", "E412", "Changelog"], 2.3, 2.35, colors)
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            FadeIn(vh),
            FadeIn(kh),
            FadeIn(vn),
            FadeIn(vr),
            FadeIn(kn),
            FadeIn(kr),
            run_time=1.2,
        )
        self.cue("merge")
        # The same page in both lists: its vector rank, its keyword rank.
        pairs = [(0, 2, GREY_B), (1, 1, GREY_B), (3, 0, YELLOW)]
        joins = VGroup(
            *[
                Line(
                    vr[a].get_right() + RIGHT * 0.2,
                    kn[b].get_left() + LEFT * 0.2,
                    color=color,
                    stroke_width=2,
                )
                for a, b, color in pairs
            ]
        )
        self.play(Create(joins), run_time=0.8)
        self.cue("points for its rank")
        rule = T("each list gives a chunk  1 / (60 + rank)  points", 28, GREY_B)
        rule.move_to((0, -0.4, 0))
        self.play(FadeIn(rule), run_time=0.7)
        self.cue("top of both")
        mh = T("merged", 32).move_to((0, -1.2, 0))
        mn, mr = ranked(["E412", "Overview", "E417"], -1.0, -1.85, colors)
        self.play(
            FadeIn(mh),
            FadeIn(mn),
            *[
                ReplacementTransform(vr[i].copy(), mr[j])
                for i, j in ((0, 0), (1, 1), (3, 2))
            ],
            run_time=1.2,
        )
        self.cue("back in the top three")
        hit = SurroundingRectangle(VGroup(mn[2], mr[2]), buff=0.12, color=GREEN)
        back = T("back in the top 3", 28, GREEN).next_to(hit, RIGHT, buff=0.3)
        self.play(Create(hit), FadeIn(back), run_time=0.6)
        self.finish()
        return (mh, mn, mr), [vh, kh, vn, vr, kn, kr, joins, rule, hit, back]

    def _rerank(self, merged: tuple[Text, VGroup, VGroup], old: list[VMobject]) -> None:
        self.voice("fix_3")
        _, nums, titles = merged
        self.play(
            *[FadeOut(m) for m in old],
            VGroup(*merged).animate.move_to((-4.2, 0.2, 0)),
            run_time=1.0,
        )
        self.cue("reranker")
        rr = box("reranker", 2.6, 1.0, YELLOW, 32).move_to((0.3, 0, 0))
        self.play(FadeIn(rr), run_time=0.6)
        self.cue("together")
        chip = bubble("What does error E417 mean?", YELLOW, 24).move_to((0.3, 1.9, 0))
        feeds = VGroup(
            *[
                Line(
                    r.get_right() + RIGHT * 0.15,
                    rr.get_left(),
                    stroke_width=2,
                    color=GREY_B,
                )
                for r in titles
            ]
        )
        self.play(
            FadeIn(chip),
            GrowArrow(Arrow(chip.get_bottom(), rr.get_top(), buff=0.1)),
            Create(feeds),
            run_time=0.8,
        )
        self.cue("sorts them")
        ys = [r.get_center()[1] for r in titles]
        self.play(
            FadeOut(feeds),
            *[r.animate.set_y(ys[j]) for r, j in zip(titles, (1, 2, 0), strict=True)],
            run_time=1.0,
        )
        self.cue("right page is first")
        self.play(
            Create(
                SurroundingRectangle(VGroup(nums[0], titles[2]), buff=0.12, color=GREEN)
            ),
            run_time=0.5,
        )
        self.cue("right error")
        ans = bubble("E417 means the region\nname is unknown. [1]", GREEN, 26)
        ans.move_to((4.1, 0, 0))
        self.play(
            GrowArrow(Arrow(rr.get_right(), ans.get_left(), buff=0.1)),
            FadeIn(ans),
            run_time=0.6,
        )
        self.finish()


class Dials(Narrated):
    """How many chunks to send, a fresh index, and testing each half."""

    @override
    def construct(self) -> None:
        k = ValueTracker(3)
        x0, x1 = -3.0, 3.0

        def kx() -> float:
            return x0 + (x1 - x0) * (k.get_value() - 1) / 19

        track = Line((x0, 2.1, 0), (x1, 2.1, 0)).set_stroke(GREY_B, 4)
        knob = always_redraw(lambda: Dot((kx(), 2.1, 0), radius=0.14, color=WHITE))
        k_l = always_redraw(
            lambda: T(f"chunks in the prompt: {round(k.get_value())}", 32).move_to(
                (0, 2.8, 0)
            )
        )
        specs: list[tuple[str, ParsableManimColor, Callable[[float], float]]] = [
            # label, color, share of the full bar at k chunks
            (
                "answer is in the prompt",
                GREEN,
                lambda v: 1 - 0.75 * np.exp(-(v - 1) / 3.5),
            ),
            ("noise", RED, lambda v: 0.08 + 0.88 * (v - 1) / 19),
            ("cost", GOLD, lambda v: v / 20),
            ("wait", BLUE_B, lambda v: 0.15 + 0.8 * v / 20),
        ]
        rows = []
        for i, (name, color, share) in enumerate(specs):
            y = 0.9 - 1.0 * i
            label = T(name, 30, color).move_to((-6.3, y, 0), aligned_edge=LEFT)
            rows.append(VGroup(label, meter(k, share, y, color)))

        self.voice("dial_1")
        self.play(
            Create(track), FadeIn(knob), FadeIn(k_l), FadeIn(rows[0]), run_time=0.8
        )
        self.cue("more chunks")
        self.play(k.animate.set_value(20), run_time=2.0)
        words = ("more noise", "pay more", "wait longer")
        for row, word in zip(rows[1:], words, strict=True):
            self.cue(word)
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.5)
        self.play(k.animate.set_value(5), run_time=1.2)
        self.finish()
        self._reindex()
        self._test_halves()
        self.fade_all()

    def _reindex(self) -> None:
        self.voice("dial_2")
        # The edit is to the monthly line: the annual answer (30 days) is the one the
        # recap repeats.
        sheet = page(1.3, 1.7)
        doc = VGroup(sheet, M("refund-policy.md", 20, TEAL))
        doc.arrange(DOWN, buff=0.2).move_to((-4.6, 1.6, 0))
        s = "monthly: refund within 7 days"
        rules = VGroup(
            T("annual: refund within 30 days", 24), T("monthly: no refunds", 24)
        )
        rules.arrange(DOWN, buff=0.2, aligned_edge=LEFT).next_to(doc, DOWN, buff=0.3)
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            FadeIn(doc),
            FadeIn(rules),
            run_time=0.8,
        )
        new = T(s, 24).move_to(rules[1], aligned_edge=LEFT)
        part(new, s, "refund within 7 days").set_color(YELLOW)
        self.play(
            FadeTransform(rules[1], new),
            sheet[1].animate.set_stroke(YELLOW),
            run_time=0.7,
        )
        self.cue("embed its chunks again")
        model = box("embedding\nmodel", 2.3, 1.2, BLUE, 26).move_to((-1.4, 1.6, 0))
        db = database(BLUE_B).move_to((1.8, 1.6, 0))
        db_l = T("vector index", 26, BLUE_B).next_to(db, RIGHT, buff=0.3)
        a1 = Arrow(doc.get_right(), model.get_left(), buff=0.15)
        a2 = Arrow(model.get_right(), db.get_left(), buff=0.15)
        self.play(GrowArrow(a1), FadeIn(model), run_time=0.6)
        self.play(GrowArrow(a2), FadeIn(db), FadeIn(db_l), run_time=0.6)
        bit = Dot(a1.get_start(), radius=0.09, color=YELLOW)
        self.play(
            MoveAlongPath(bit, Line(a1.get_start(), db.get_center())), run_time=0.8
        )
        self.remove(bit)
        ask = bubble("Can I get a refund on a monthly plan?", YELLOW, 24)
        ask.move_to((3.7, -1.0, 0))
        self.play(FadeIn(ask, shift=DOWN * 0.2), run_time=0.5)
        self.cue("new text")
        ans = bubble("Yes, within 7 days. [1]", GREEN, 26).next_to(ask, DOWN, buff=0.35)
        self.play(
            GrowArrow(
                Arrow(db.get_bottom(), (db.get_x(), ask.get_top()[1], 0), buff=0.15)
            ),
            FadeIn(ans, shift=DOWN * 0.2),
            run_time=0.6,
        )
        self.cue("No retraining")
        self.play(
            FadeIn(T("no retraining", 36, GREEN).move_to((-3.6, -2.4, 0))),
            run_time=0.5,
        )
        self.cue("as the index")
        self.play(Circumscribe(VGroup(db, db_l), color=YELLOW), run_time=0.7)
        self.finish()

    def _test_halves(self) -> None:
        self.voice("dial_3")
        lh = stacked("1  retrieval", "right chunk in the top 3?", size=30, buff=0.2)
        lh.move_to((-3.4, 2.3, 0))
        rh = stacked(
            "2  generation",
            "answer says only what its sources say?",
            size=30,
            buff=0.2,
        ).move_to((3.4, 2.3, 0))
        lh[0].set_color(BLUE_B)
        rh[0].set_color(GREEN)
        lh[1].set_color(GREY_B)
        rh[1].set_color(GREY_B)
        max_width = 6.4  # half the frame, less a margin
        if rh.width > max_width:
            rh.scale_to_fit_width(max_width)
        ys = [1.0, 0.25, -0.5, -1.25, -2.0]
        qs = VGroup(
            *[
                M(f"question {i + 1}", 22, GREY_B).move_to(
                    (-6.1, y, 0), aligned_edge=LEFT
                )
                for i, y in enumerate(ys)
            ]
        )
        failed = 2  # bad retrieval for question 3 makes its answer bad too
        marks = [
            [
                (cross if i == failed else tick)(s=0.35).move_to((x, y, 0))
                for i, y in enumerate(ys)
            ]
            for x in (-3.4, 3.4)
        ]
        self.play(
            *[FadeOut(m) for m in self.mobjects],
            FadeIn(lh),
            FadeIn(rh),
            FadeIn(qs),
            run_time=1.0,
        )
        self.cue("right chunk")
        self.play(
            LaggedStart(*[Create(m) for m in marks[0]], lag_ratio=0.25), run_time=1.0
        )
        self.cue("say only what")
        self.play(
            LaggedStart(*[Create(m) for m in marks[1]], lag_ratio=0.25), run_time=1.0
        )
        self.cue("Most bad answers")
        cause = Arrow(
            marks[0][failed].get_right(),
            marks[1][failed].get_left(),
            buff=0.3,
            color=RED,
        )
        self.play(
            GrowArrow(cause),
            FadeIn(T("causes", 26, RED).next_to(cause, UP, buff=0.1)),
            run_time=0.7,
        )
        self.cue("bad retrieval")
        self.play(Circumscribe(lh, color=BLUE_B), run_time=0.7)
        self.finish()


class Recap(Narrated):
    """The whole pipeline once more, on the opening question."""

    @override
    def construct(self) -> None:
        ask = bubble("Can I get a refund\non an annual plan?", YELLOW, 28)
        ask.move_to((-4.6, 1.6, 0))
        search = box("vector + keyword\nsearch", 3.0, 1.3, BLUE, 26)
        search.move_to((0, 1.6, 0))
        card = source_card(1, "refund-policy.md", w=3.8).move_to((4.6, 1.6, 0))
        prompt = box("prompt", 2.6, 1.1, GREY_B, 30).move_to((4.6, -1.6, 0))
        model = box("language model", 3.0, 1.1, BLUE, 28).move_to((0, -1.6, 0))
        ans = bubble("Yes, within 30 days. [1]", GREEN, 28).move_to((-4.6, -1.6, 0))
        arrows = [
            Arrow(a.get_right(), b.get_left(), buff=0.2)
            for a, b in ((ask, search), (search, card))
        ]
        arrows.append(Arrow(card.get_bottom(), prompt.get_top(), buff=0.2))
        arrows += [
            Arrow(a.get_left(), b.get_right(), buff=0.2)
            for a, b in ((prompt, model), (model, ans))
        ]

        self.voice("rec_1")
        self.play(FadeIn(ask, shift=RIGHT * 0.2), run_time=0.8)
        self.cue("Can I get")
        self.play(Indicate(ask, color=YELLOW, scale_factor=1.05), run_time=0.6)
        self.cue("Search finds")
        self.play(GrowArrow(arrows[0]), FadeIn(search), run_time=0.7)
        self.play(GrowArrow(arrows[1]), FadeIn(card), run_time=0.7)
        self.cue("prompt carries")
        self.play(GrowArrow(arrows[2]), FadeIn(prompt), run_time=0.7)
        chip = M("[1]", 24, GOLD).next_to(prompt[1], DOWN, buff=0.08)
        self.play(
            ReplacementTransform(card.copy(), chip),
            prompt[1].animate.shift(UP * 0.15),
            run_time=0.7,
        )
        self.cue("model answers")
        self.play(GrowArrow(arrows[3]), FadeIn(model), run_time=0.7)
        self.play(GrowArrow(arrows[4]), FadeIn(ans), run_time=0.8)
        self.cue("source one")
        self.play(
            Create(tick(s=0.45).next_to(ans, DOWN, buff=0.3)),
            Indicate(chip, color=GOLD),
            run_time=0.6,
        )
        self.finish()

        self.voice("rec_2")
        self.play(Indicate(model, color=BLUE_B, scale_factor=1.05), run_time=0.7)
        self.cue("reads first")
        self.play(Indicate(prompt, color=WHITE, scale_factor=1.05), run_time=0.6)
        self.cue("That is")
        s = "Retrieval Augmented Generation"
        title = T(s, 64)
        for w in ("Retrieval", "Augmented", "Generation"):
            part(title, s, w)[0].set_color(YELLOW)
        self.play(*[FadeOut(m) for m in self.mobjects], Write(title), run_time=1.6)
        self.finish()
        self.fade_all()
