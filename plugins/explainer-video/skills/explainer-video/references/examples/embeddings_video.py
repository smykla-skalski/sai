"""Worked example: a 6-minute 3b1b-style explainer on embeddings and reranking for RAG.

Read the scene you need as a recipe; do not copy the file wholesale.

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
    Narrated,
    T,
    box,
    cells,
    column,
    faint_plane,
    num,
    page,
    part,
    unit,
)
from manim import (
    BLACK,
    BLUE,
    BLUE_B,
    BLUE_D,
    BLUE_E,
    DEGREES,
    DL,
    DOWN,
    DR,
    GOLD,
    GREEN,
    GREY_B,
    GREY_C,
    GREY_D,
    LEFT,
    MAROON_B,
    ORIGIN,
    PI,
    PURPLE_B,
    RED,
    RED_B,
    RIGHT,
    TEAL,
    UL,
    UP,
    UR,
    WHITE,
    YELLOW,
    AnimationGroup,
    Arc,
    ArcBetweenPoints,
    Arrow,
    BackgroundRectangle,
    Brace,
    Circle,
    Circumscribe,
    Create,
    Cross,
    DashedLine,
    DashedVMobject,
    Dot,
    DoubleArrow,
    FadeIn,
    FadeOut,
    GrowArrow,
    GrowFromCenter,
    GrowFromEdge,
    Indicate,
    LaggedStart,
    Line,
    Mobject,
    Polygon,
    Rectangle,
    ReplacementTransform,
    RoundedRectangle,
    Square,
    SurroundingRectangle,
    Text,
    Transform,
    ValueTracker,
    VGroup,
    Write,
    always_redraw,
    linear,
    normalize,
    smooth,
    there_and_back,
)
from typing_extensions import override

if TYPE_CHECKING:
    from manim import ParsableManimColor
    from manim.typing import Point2DLike, Point3D, Point3DLike, Vector3DLike

SCENES: Final = [
    "Intro",
    "Embeddings",
    "Training",
    "Similarity",
    "Rag",
    "Problem",
    "Rerank",
    "Cost",
    "Outro",
]
TIMES: Final = "\N{MULTIPLICATION SIGN}"

RESULTS: Final = [
    ("Subscribe today! Cancel anytime, no questions asked.", 0.89, 0.12),
    ("Subscription plans: Basic, Pro and Enterprise.", 0.86, 0.08),
    ("To cancel, open Settings → Billing → End plan.", 0.84, 0.97),
    ("Refund policy for canceled orders.", 0.81, 0.31),
]
QUESTION: Final = "How do I cancel my subscription?"
RESULT_WIDTH: Final = 8.4  # longer result lines shrink to fit before the score bars


def results_table() -> tuple[Text, SurroundingRectangle, VGroup, VGroup, Text]:
    """Return the question and its vector-search hits: q, qbox, ranks, rows, head."""
    q = T(QUESTION, 40, YELLOW).to_edge(UP, buff=0.5)
    qbox = SurroundingRectangle(q, buff=0.2, corner_radius=0.1, color=YELLOW)
    rows, ranks = VGroup(), VGroup()
    for i, (text, s, _) in enumerate(RESULTS):
        y = 1.3 - 1.2 * i
        t = T(text, 26)
        if t.width > RESULT_WIDTH:
            t.scale_to_fit_width(RESULT_WIDTH)
        t.move_to((-5.7, y, 0), aligned_edge=LEFT)
        bar = Rectangle(
            width=2.0 * s,
            height=0.24,
            fill_color=BLUE,
            fill_opacity=0.8,
            stroke_width=0,
        )
        bar.move_to((3.0, y, 0), aligned_edge=LEFT)
        rows.add(VGroup(t, bar, T(num(s), 26, BLUE).move_to((5.5, y, 0))))
        ranks.add(T(f"{i + 1}.", 26, GREY_B).move_to((-6.3, y, 0)))
    head = T("similarity", 24, GREY_B).move_to((4.2, 2.0, 0))
    return q, qbox, ranks, rows, head


class Intro(Narrated):
    """A question, a pile of docs, and RAG handing the right paragraph to an LLM."""

    @override
    def construct(self) -> None:
        pages = (
            VGroup(*[page() for _ in range(60)])
            .arrange_in_grid(6, 10, buff=(0.25, 0.2))
            .move_to(DOWN * 0.4)
        )
        question = T("How do I rotate my API keys?", 40, YELLOW).to_edge(UP, buff=0.6)
        target = pages[36]

        self.voice("intro_1")
        self.play(
            LaggedStart(*[FadeIn(p, shift=0.1 * UP) for p in pages], lag_ratio=0.03),
            run_time=3,
        )
        self.cue("Someone")
        self.play(Write(question), run_time=1.5)
        self.cue("one paragraph")
        others = VGroup(*[p for p in pages if p is not target])
        self.play(
            others.animate.set_opacity(0.25),
            target.animate.set_color(YELLOW).scale(1.4),
            run_time=1.2,
        )
        self.finish()

        self.voice("intro_2")
        llm = box("LLM", 2.2, 1.4, BLUE, 44).move_to(RIGHT * 4.2 + DOWN * 0.4)
        self.play(
            pages.animate.scale(0.6).to_edge(LEFT, buff=0.5).shift(DOWN * 0.4),
            question.animate.scale(0.6).move_to(RIGHT * 4.2 + UP * 1.9),
            FadeIn(llm),
            run_time=1.5,
        )
        q_arrow = Arrow(question.get_bottom(), llm.get_top(), buff=0.15)
        self.play(GrowArrow(q_arrow), run_time=0.6)
        self.cue("right paragraph")
        chosen = target.copy()
        self.play(
            chosen.animate.scale(1.6).move_to(RIGHT * 0.9 + DOWN * 0.4), run_time=1.2
        )
        p_arrow = Arrow(chosen.get_right(), llm.get_left(), buff=0.2)
        self.play(GrowArrow(p_arrow), run_time=0.6)
        answer = T("“Settings → API keys → Rotate”", 24, GREEN).next_to(
            llm, DOWN, buff=0.4
        )
        self.play(Write(answer), Indicate(llm, color=BLUE_B), run_time=1.2)
        self.cue("retrieval")
        words = VGroup(
            T("Retrieval", 40), T("Augmented", 40), T("Generation", 40)
        ).arrange(RIGHT, buff=0.3)
        words.to_edge(DOWN, buff=0.5)
        # w[0] would be typed Mobject; VGroup takes VMobjects.
        initials = [w.submobjects[0] for w in words]
        for initial in initials:
            initial.set_color(YELLOW)
        self.play(Write(words), run_time=1.5)
        self.cue("RAG")
        rag = T("RAG", 60, YELLOW).move_to(words)
        self.play(
            ReplacementTransform(VGroup(*initials), rag),
            *[FadeOut(w[1:]) for w in words],
            run_time=1,
        )
        self.finish()
        self._two_parts()

    def _two_parts(self) -> None:
        self.voice("intro_3")
        self.fade_all()
        q = T("How do I rotate my API keys?", 36, YELLOW).shift(UP * 1.3)
        d = T(
            "Credential renewal: generate a new token, then revoke the old one.", 30
        ).shift(DOWN * 0.1)
        self.cue("How does")
        self.play(FadeIn(q, shift=DOWN * 0.3))
        self.cue("means the same")
        self.play(FadeIn(d, shift=UP * 0.3))
        self.cue("completely different")
        no = T("same meaning, no words in common", 30, GREEN).next_to(d, DOWN, buff=0.7)
        self.play(Write(no))
        self.cue("two parts")
        self.play(FadeOut(VGroup(q, d, no)))
        e = T("Embeddings", 72, BLUE)
        amp = T("&", 48, GREY_B)
        r = T("Reranking", 72, YELLOW)
        VGroup(e, amp, r).arrange(DOWN, buff=0.4)
        self.cue("Embeddings")
        self.play(Write(e))
        self.cue("reranking")
        self.play(FadeIn(amp), Write(r))
        self.finish()
        self.fade_all()


WORDS: Final = {
    "cat": ((-3.6, 1.4), TEAL),
    "kitten": ((-2.6, 1.2), TEAL),
    "dog": ((-4.6, 0.8), TEAL),
    "puppy": ((-3.5, 0.3), TEAL),
    "car": ((3.0, 2.0), GOLD),
    "truck": ((4.0, 1.4), GOLD),
    "bus": ((2.7, 0.8), GOLD),
    "pizza": ((0.6, -2.2), RED_B),
    "pasta": ((1.6, -2.8), RED_B),
    "bread": ((-0.4, -2.8), RED_B),
}


def word_point(name: str, xy: tuple[float, float], color: ParsableManimColor) -> VGroup:
    """Return a dot at xy labeled with the word name."""
    d = Dot((*xy, 0), radius=0.09, color=color)
    return VGroup(d, T(name, 28, color).next_to(d, UR, buff=0.05))


class Embeddings(Narrated):
    """Words as points: similar meanings cluster, and directions carry meaning."""

    @override
    def construct(self) -> None:
        plane = faint_plane()
        pts = {n: word_point(n, xy, c) for n, (xy, c) in WORDS.items()}

        self.voice("emb_1")
        self.play(Create(plane), run_time=2)
        self.cue("every piece")
        word = T("cat", 60, TEAL)
        self.play(FadeIn(word, scale=1.3))
        self.cue("point in space")
        self.play(
            ReplacementTransform(word, pts["cat"][1]),
            GrowFromCenter(pts["cat"][0]),
            run_time=1.2,
        )
        self.finish()

        self.voice("emb_2")
        for cue, group in [
            ("Cat sits", ["kitten", "dog", "puppy"]),
            ("Car sits", ["car", "truck", "bus"]),
            ("pizza", ["pizza", "pasta", "bread"]),
        ]:
            self.cue(cue)
            self.play(
                LaggedStart(*[FadeIn(pts[n], scale=0.5) for n in group], lag_ratio=0.3),
                run_time=1.2,
            )
        self.finish()

        self.voice("emb_3")
        cat = pts["cat"]
        others = VGroup(*[pts[n] for n in WORDS if n != "cat"])
        header = T("embedding:  text → point", 40, t2c={"embedding:": TEAL}).to_edge(
            UP, buff=0.4
        )
        header_bg = BackgroundRectangle(header, fill_opacity=0.9, buff=0.15)
        self.play(
            others.animate.set_opacity(0.3),
            FadeIn(header_bg),
            Write(header),
            run_time=1.5,
        )
        self.cue("list of numbers")
        p = cat[0].get_center()
        dx = DashedLine(p, (p[0], 0, 0), color=GREY_B)
        dy = DashedLine(p, (0, p[1], 0), color=GREY_B)
        coords = T(f"[{MINUS}3.6, 1.4]", 34, TEAL).next_to(cat[0], UL, buff=0.15)
        self.play(Create(dx), Create(dy), Write(coords), run_time=1.5)
        self.finish()

        self.voice("emb_4")
        self.play(Indicate(coords, color=YELLOW), run_time=1.2)
        self.cue("Real embedding")
        col = column(
            [num(v) for v in (0.12, -0.53, 0.88, 0.07, -0.91)]
            + ["⋮"]
            + [num(v) for v in (0.34, -0.26)],
            TEAL,
        )
        self.play(
            FadeOut(VGroup(plane, others, cat, dx, dy, header, header_bg)),
            ReplacementTransform(coords, col),
            run_time=1.5,
        )
        brace = Brace(col, RIGHT)
        blabel = T("768 to 3072 numbers", 34).next_to(brace, RIGHT)
        self.cue("few hundred")
        self.play(GrowFromCenter(brace), Write(blabel))
        self.cue("geometry works")
        others.set_opacity(1)
        self.play(
            FadeOut(VGroup(col, brace, blabel)),
            FadeIn(plane),
            FadeIn(cat),
            FadeIn(others),
            run_time=1.5,
        )
        near = Line(
            cat[0].get_center(),
            pts["kitten"][0].get_center(),
            color=GREEN,
            stroke_width=5,
        )
        far = DashedLine(
            cat[0].get_center(), pts["car"][0].get_center(), color=RED, stroke_width=3
        )
        legend = (
            VGroup(
                VGroup(
                    Line(ORIGIN, RIGHT * 0.6, color=GREEN, stroke_width=5),
                    T("close = similar", 28, GREEN),
                ).arrange(RIGHT),
                VGroup(
                    DashedLine(ORIGIN, RIGHT * 0.6, color=RED),
                    T("far = different", 28, RED),
                ).arrange(RIGHT),
            )
            .arrange(DOWN, aligned_edge=LEFT)
            .to_corner(DL, buff=0.5)
        )
        legend_bg = BackgroundRectangle(legend, fill_opacity=0.9, buff=0.15)
        self.cue("Close means")
        self.play(
            Create(near), Create(far), FadeIn(legend_bg), FadeIn(legend), run_time=1.2
        )
        self.finish()
        self._analogy(VGroup(*pts.values(), near, far, legend, legend_bg))

    def _analogy(self, old: VGroup) -> None:
        self.voice("emb_5")
        self.play(FadeOut(old))
        pos = {
            "man": (-3.5, -2.0),
            "woman": (-2.0, 0.6),
            "king": (1.5, -2.0),
            "queen": (3.0, 0.6),
        }
        pts = {n: word_point(n, xy, BLUE_B) for n, xy in pos.items()}
        self.play(
            LaggedStart(*[FadeIn(m, scale=0.5) for m in pts.values()], lag_ratio=0.2),
            run_time=1.5,
        )

        def at(n: str) -> Point3D:
            return pts[n][0].get_center()

        self.cue("man to woman")
        a1 = Arrow(at("man"), at("woman"), buff=0.12, color=YELLOW)
        self.play(GrowArrow(a1))
        self.cue("king to queen")
        a2 = a1.copy()
        self.play(a2.animate.shift(at("king") - at("man")), run_time=1.2)
        b1 = Arrow(at("man"), at("king"), buff=0.12, color=GREY_B, stroke_width=3)
        b2 = Arrow(at("woman"), at("queen"), buff=0.12, color=GREY_B, stroke_width=3)
        self.play(GrowArrow(b1), GrowArrow(b2))
        self.cue("Nobody")
        eq = T(f"king {MINUS} man + woman ≈ queen", 40).to_edge(UP, buff=0.5)
        eq_bg = BackgroundRectangle(eq, fill_opacity=0.9, buff=0.15)
        note = T("word2vec, 2013", 24, GREY_B).to_corner(DR)
        self.play(FadeIn(eq_bg), Write(eq), FadeIn(note), run_time=1.5)
        self.finish()
        self.fade_all()


def token(w: str, size: float = 28, width: float = 1.9) -> VGroup:
    """Return the word w in a thin rounded outline."""
    r = RoundedRectangle(
        corner_radius=0.08,
        width=width,
        height=0.45,
        stroke_color=GREY_B,
        stroke_width=1.5,
    )
    return VGroup(r, T(w, size).move_to(r))


def labeled(
    xy: Point2DLike, text: str, color: ParsableManimColor, side: Vector3DLike
) -> VGroup:
    """Return a dot at xy with text on its side."""
    d = Dot((*xy, 0), radius=0.1, color=color)
    return VGroup(d, T(text, 26, color).next_to(d, side, buff=0.15))


class Training(Narrated):
    """An embedding model: tokens in, one pooled vector out, trained by contrast."""

    @override
    def construct(self) -> None:
        self.voice("train_1")
        model = RoundedRectangle(
            corner_radius=0.2,
            width=3.6,
            height=4.4,
            stroke_color=BLUE,
            fill_color=BLUE_E,
            fill_opacity=0.3,
        )
        model.move_to(DOWN * 0.2)
        layers = (
            VGroup(
                *[
                    RoundedRectangle(
                        corner_radius=0.08,
                        width=0.35,
                        height=3.6,
                        stroke_color=BLUE_B,
                        stroke_width=2,
                        fill_color=BLUE_D,
                        fill_opacity=0.25,
                    )
                    for _ in range(5)
                ]
            )
            .arrange(RIGHT, buff=0.3)
            .move_to(model)
        )
        title = T("embedding model", 36).next_to(model, UP, buff=0.2)
        sub = T("(a transformer)", 26, GREY_B).next_to(model, DOWN, buff=0.2)
        self.play(
            FadeIn(model),
            LaggedStart(
                *[FadeIn(layer, shift=UP * 0.2) for layer in layers], lag_ratio=0.15
            ),
            Write(title),
            run_time=2,
        )
        self.cue("transformer")
        self.play(FadeIn(sub))
        self.finish()

        self.voice("train_2")
        sentence = T("How do I reset my password?", 36, YELLOW).to_edge(UP, buff=0.3)
        self.play(Write(sentence), run_time=1.2)
        words = ["How", "do", "I", "reset", "my", "password", "?"]
        toks = (
            VGroup(*[token(w) for w in words])
            .arrange(DOWN, buff=0.12)
            .move_to((-5.2, -0.2, 0))
        )
        self.cue("split into tokens")
        # t[1] would be typed Mobject; VGroup and Create take VMobjects.
        self.play(
            ReplacementTransform(
                sentence, VGroup(*[g for t in toks for g in t.submobjects[1]])
            ),
            LaggedStart(*[Create(t.submobjects[0]) for t in toks], lag_ratio=0.1),
            run_time=1.5,
        )
        self.cue("flows through")
        flying = toks.copy()
        self.play(flying.animate.move_to(model).scale(0.3).set_opacity(0), run_time=1.0)
        self.remove(flying)
        # A Transform, not .animate: LaggedStart is typed to take Animations.
        self.play(
            LaggedStart(
                *[
                    Transform(
                        layer,
                        layer.copy().set_fill(YELLOW, 0.7),
                        rate_func=there_and_back,
                    )
                    for layer in layers
                ],
                lag_ratio=0.25,
            ),
            run_time=1.6,
        )
        rng = np.random.default_rng(1)
        vals = rng.uniform(-1, 1, (len(words), 6))
        rows = VGroup(*[cells(v) for v in vals])
        for row, tk in zip(rows, toks, strict=True):
            row.move_to((3.2, tk.get_y(), 0))
        self.cue("its own vector")
        self.play(
            LaggedStart(*[FadeIn(r, shift=RIGHT * 0.4) for r in rows], lag_ratio=0.1),
            run_time=1.2,
        )
        self.cue("squeezes")
        pooled = cells(vals.mean(axis=0) * 2.5).move_to((5.6, -0.2, 0))
        copies = [r.copy() for r in rows]
        self.play(*[Transform(c, pooled) for c in copies], run_time=1.4)
        self.remove(*copies)
        self.add(pooled)
        avg = T("average", 26, GREY_B).next_to(pooled, DOWN, buff=0.25)
        self.play(FadeIn(avg))
        self.cue("One fixed-size")
        brace = Brace(pooled, UP)
        one = T("one vector", 28, TEAL).next_to(brace, UP)
        self.play(GrowFromCenter(brace), Write(one))
        self.finish()
        self._pairs()

    def _pairs(self) -> None:
        self.voice("train_3")
        self.fade_all()
        plane = faint_plane(0.25)
        self.add(plane)
        q1 = labeled((-1.5, 0.8), "reset my password?", YELLOW, LEFT)
        a1 = labeled((3.0, 2.6), "Password reset steps", YELLOW, RIGHT)
        q2 = labeled((-3.5, -1.8), "Intro to Rust", TEAL, LEFT)
        a2 = labeled((2.4, -2.6), "Rust: a systems language", TEAL, RIGHT)
        links = VGroup(
            always_redraw(
                lambda: DashedLine(
                    q1[0].get_center(),
                    a1[0].get_center(),
                    color=YELLOW,
                    stroke_opacity=0.6,
                )
            ),
            always_redraw(
                lambda: DashedLine(
                    q2[0].get_center(),
                    a2[0].get_center(),
                    color=TEAL,
                    stroke_opacity=0.6,
                )
            ),
        )
        self.cue("A question")
        self.play(FadeIn(q1, scale=0.8), FadeIn(a1, scale=0.8), Create(links[0]))
        self.cue("A title")
        self.play(FadeIn(q2, scale=0.8), FadeIn(a2, scale=0.8), Create(links[1]))
        self.cue("pull")
        self.play(
            a1.animate.shift(
                q1[0].get_center() + np.array([0.8, 0.35, 0]) - a1[0].get_center()
            ),
            a2.animate.shift(
                q2[0].get_center() + np.array([0.8, -0.35, 0]) - a2[0].get_center()
            ),
            run_time=2,
        )
        self.finish(0.1)

        self.voice("train_4")
        c = q1[0].get_center()
        negs = VGroup(
            *[
                labeled(c[:2] + off, name, RED, side)
                for off, name, side in [
                    ((0.6, 0.8), "pricing", RIGHT),
                    ((-0.9, -0.5), "team photos", LEFT),
                    ((1.0, -0.6), "API limits", RIGHT),
                ]
            ]
        )
        self.play(
            LaggedStart(*[FadeIn(n, scale=0.6) for n in negs], lag_ratio=0.2),
            run_time=0.8,
        )
        self.play(
            *[n.animate.shift(1.6 * normalize(n[0].get_center() - c)) for n in negs],
            run_time=1.5,
        )
        self.cue("Repeat")
        self.play(FadeOut(VGroup(q1, a1, q2, a2, links, negs)))
        rng = np.random.default_rng(4)
        centers = [(-4, 2, BLUE), (3.5, 2, YELLOW), (-3, -2, GREEN), (3, -1.8, RED_B)]
        cloud = VGroup()
        targets: list[Point3DLike] = []
        for cx, cy, color in centers:
            for _ in range(22):
                cloud.add(
                    Dot(
                        (rng.uniform(-6.5, 6.5), rng.uniform(-3.5, 3.5), 0),
                        radius=0.07,
                        color=color,
                    )
                )
                targets.append((cx + rng.normal(0, 0.55), cy + rng.normal(0, 0.45), 0))
        self.play(
            LaggedStart(*[FadeIn(d, scale=0.3) for d in cloud], lag_ratio=0.01),
            run_time=1.2,
        )
        self.play(
            *[d.animate.move_to(t) for d, t in zip(cloud, targets, strict=True)],
            run_time=3,
            rate_func=smooth,
        )
        self.cue("contrastive")
        name = T("contrastive learning", 48).move_to(DOWN * 0.1)
        self.play(
            FadeIn(BackgroundRectangle(name, fill_opacity=0.9, buff=0.2)), Write(name)
        )
        self.finish()
        self.fade_all()


class Similarity(Narrated):
    """Cosine similarity: the angle between two arrows, then the dot product."""

    @override
    def construct(self) -> None:
        plane = faint_plane(0.4)
        a_ang = 20 * DEGREES
        ang = ValueTracker(70 * DEGREES)
        ln = ValueTracker(3.0)

        a = Arrow(ORIGIN, 3 * unit(a_ang), buff=0, color=BLUE, stroke_width=6)
        la = T("a", 40, BLUE).move_to(3.4 * unit(a_ang))
        b = always_redraw(
            lambda: Arrow(
                ORIGIN,
                ln.get_value() * unit(ang.get_value()),
                buff=0,
                color=YELLOW,
                stroke_width=6,
            )
        )
        lb = always_redraw(
            lambda: T("b", 40, YELLOW).move_to(
                (ln.get_value() + 0.4) * unit(ang.get_value())
            )
        )
        arc = always_redraw(
            lambda: Arc(
                radius=0.8,
                start_angle=a_ang,
                angle=ang.get_value() - a_ang,
                color=WHITE,
            )
        )
        theta = always_redraw(
            lambda: T(THETA, 32).move_to(1.15 * unit((a_ang + ang.get_value()) / 2))
        )
        title = T("cosine similarity", 44).to_corner(UL)
        title_bg = BackgroundRectangle(title, fill_opacity=0.9, buff=0.15)
        readout_bg = Rectangle(
            width=3.8, height=0.9, fill_color=BLACK, fill_opacity=0.9, stroke_width=0
        ).move_to((5.0, 3.3, 0))
        readout = always_redraw(
            lambda: (
                VGroup(
                    T(f"cos {THETA} =", 40),
                    T(num(np.cos(ang.get_value() - a_ang)), 40, YELLOW),
                )
                .arrange(RIGHT)
                .move_to((3.4, 3.3, 0), aligned_edge=LEFT)
            )
        )

        self.voice("sim_1")
        self.play(Create(plane), run_time=1.5)
        self.cue("co-sign")
        self.play(FadeIn(title_bg), Write(title))
        self.cue("Think of")
        dots = VGroup(
            Dot(3 * unit(a_ang), color=BLUE),
            Dot(3 * unit(ang.get_value()), color=YELLOW),
        )
        self.play(FadeIn(dots, scale=0.5))
        self.cue("arrow")
        self.play(
            GrowArrow(a),
            GrowArrow(b),
            FadeIn(la),
            FadeIn(lb),
            FadeOut(dots),
            run_time=1.5,
        )
        self.finish()

        self.voice("sim_2")
        self.play(
            Create(arc),
            FadeIn(theta),
            FadeIn(readout_bg),
            FadeIn(readout),
            run_time=0.8,
        )
        self.play(ln.animate.set_value(1.6), run_time=0.9)
        self.play(ln.animate.set_value(3.6), run_time=0.9)
        self.play(ln.animate.set_value(3.0), run_time=0.5)
        self.cue("same way")
        self.play(ang.animate.set_value(28 * DEGREES), run_time=1.5)
        self.finish()

        self.voice("sim_3")
        self.play(ang.animate.set_value(a_ang + PI / 2), run_time=1.5)
        tag = T("unrelated", 30, GREY_B).move_to((5.0, 2.6, 0))
        self.play(FadeIn(tag))
        self.cue("opposite")
        self.play(ang.animate.set_value(a_ang + PI), FadeOut(tag), run_time=1.5)
        self.finish()
        self._formula()

    def _formula(self) -> None:
        self.voice("sim_4")
        self.fade_all()
        lhs = T(f"cos {THETA}  =", 44)
        numr = T("a · b", 44)
        den = T("‖a‖ ‖b‖", 44)
        bar = Line(LEFT, RIGHT).set_width(max(numr.width, den.width) + 0.3)
        frac = VGroup(numr, bar, den).arrange(DOWN, buff=0.18)
        formula = VGroup(lhs, frac).arrange(RIGHT, buff=0.3).to_edge(UP, buff=0.6)
        self.play(Write(lhs), Write(numr))
        exs = VGroup(
            T("a = [0.6, 0.8]", 36, BLUE), T("b = [0.8, 0.6]", 36, YELLOW)
        ).arrange(RIGHT, buff=1.2)
        exs.next_to(formula, DOWN, buff=0.7)
        self.cue("Multiply")
        self.play(FadeIn(exs))
        dot = T(f"a · b  =  0.6 {TIMES} 0.8  +  0.8 {TIMES} 0.6  =  0.96", 36).next_to(
            exs, DOWN, buff=0.5
        )
        self.play(Write(dot), run_time=2)
        self.cue("divide")
        self.play(Create(bar), Write(den))
        self.cue("normalize")
        norm = T("‖a‖ = ‖b‖ = 1", 36, GREEN).next_to(dot, DOWN, buff=0.6)
        self.play(Write(norm))
        self.cue("just the dot")
        result = T(f"cos {THETA}  =  a · b", 44, YELLOW).next_to(norm, DOWN, buff=0.6)
        self.play(
            Write(result), Create(SurroundingRectangle(result, color=YELLOW, buff=0.2))
        )
        self.finish()
        self.fade_all()


CHUNK_COLORS: Final = [BLUE, TEAL, GREEN, GOLD, MAROON_B, PURPLE_B]
# The chunks that answer the question, by index, and where they sit from its point.
ANSWER_OFFSETS: Final = {1: (0.45, 0.3), 3: (-0.4, 0.35), 4: (0.25, -0.45)}


def chunk_card(color: ParsableManimColor) -> VGroup:
    """Return a document chunk: a tinted card with two text lines."""
    r = RoundedRectangle(
        corner_radius=0.06,
        width=1.7,
        height=0.48,
        stroke_color=color,
        fill_color=color,
        fill_opacity=0.2,
    )
    lines = VGroup(
        Line(LEFT * 0.6, RIGHT * 0.6), Line(LEFT * 0.6, RIGHT * 0.2)
    ).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
    return VGroup(r, lines.set_stroke(color, 1.5).move_to(r))


def index_points(center: Point3D, q: Point3D) -> tuple[list[Point3D], list[Point3D]]:
    """Return the chunk points and 70 filler points of the vector index around q."""
    rng = np.random.default_rng(7)

    def random_point(min_dist: float) -> Point3D:
        while True:
            p = center + np.array(
                [rng.uniform(-2.75, 2.75), rng.uniform(-2.25, 2.25), 0]
            )
            if np.linalg.norm(p - q) > min_dist:
                return p

    chunk_pts = [
        q + np.array([*ANSWER_OFFSETS[i], 0])
        if i in ANSWER_OFFSETS
        else random_point(1.3)
        for i in range(len(CHUNK_COLORS))
    ]
    grey_pts = [random_point(0.9) for _ in range(70)]
    return chunk_pts, grey_pts


class Rag(Narrated):
    """RAG end to end: chunk, embed, index, search the graph, prompt the LLM."""

    @override
    def construct(self) -> None:
        center = np.array([3.7, -0.4, 0])
        space = Rectangle(
            width=6.0, height=5.0, stroke_color=GREY_B, stroke_width=2
        ).move_to(center)
        space_lbl = T("vector index", 28, GREY_B).next_to(space, DOWN, buff=0.15)
        q = center + np.array([0.6, 0.7, 0])
        chunk_pts, grey_pts = index_points(center, q)
        doc = page(1.6, 2.2, WHITE).move_to((-5.2, -0.4, 0))
        chunks = (
            VGroup(*[chunk_card(c) for c in CHUNK_COLORS])
            .arrange(DOWN, buff=0.14)
            .move_to(doc)
        )
        embed = box("embed", 1.9, 1.2, BLUE, 32).move_to((-1.6, -0.4, 0))
        title = T("indexing (offline)", 32, GREY_B).to_corner(UL)

        self.voice("rag_1")
        self.cue("First")
        self.play(Write(title))
        self.cue("Take your")
        self.play(FadeIn(doc, shift=RIGHT * 0.3))
        self.cue("cut them")
        starts = VGroup(
            *[
                c.copy()
                .stretch_to_fit_width(doc.width)
                .stretch_to_fit_height(doc.height / 6)
                for c in chunks
            ]
        )
        starts.arrange(DOWN, buff=0).move_to(doc)
        self.play(FadeOut(doc), FadeIn(starts), run_time=0.6)
        self.play(
            LaggedStart(
                *[
                    ReplacementTransform(s, c)
                    for s, c in zip(starts, chunks, strict=True)
                ],
                lag_ratio=0.15,
            ),
            run_time=1.5,
        )
        self.finish()

        self.voice("rag_2")
        self.play(FadeIn(embed), Create(space), Write(space_lbl), run_time=1.2)
        mids = VGroup(
            *[Dot(embed.get_center(), radius=0.08, color=c) for c in CHUNK_COLORS]
        )
        self.play(
            LaggedStart(
                *[
                    ReplacementTransform(ch.copy(), m)
                    for ch, m in zip(chunks, mids, strict=True)
                ],
                lag_ratio=0.2,
            ),
            run_time=1.8,
        )
        # A Transform, not .animate: LaggedStart is typed to take Animations.
        self.play(
            LaggedStart(
                *[
                    Transform(m, m.copy().move_to(p))
                    for m, p in zip(mids, chunk_pts, strict=True)
                ],
                lag_ratio=0.2,
            ),
            run_time=1.6,
        )
        self.cue("vector database")
        greys = VGroup(*[Dot(p, radius=0.05, color=GREY_C) for p in grey_pts])
        self.play(
            LaggedStart(*[FadeIn(g, scale=0.3) for g in greys], lag_ratio=0.02),
            run_time=1.5,
        )
        self.finish()

        self.voice("rag_3")
        question = T("How do I rotate API keys?", 32, YELLOW).move_to((-2.4, 2.4, 0))
        self.play(
            Transform(title, T("query time (online)", 32, GREY_B).to_corner(UL)),
            FadeIn(question, shift=DOWN * 0.3),
            run_time=1,
        )
        mid = Dot(embed.get_center(), radius=0.1, color=YELLOW)
        self.play(ReplacementTransform(question.copy(), mid), run_time=1)
        qdot = Dot(q, radius=0.11, color=YELLOW)
        ring = Circle(radius=0.2, color=YELLOW, stroke_width=2).move_to(q)
        self.play(ReplacementTransform(mid, qdot), Create(ring), run_time=1)
        self.finish()

        self._search(q, grey_pts, chunk_pts, space, mids)
        self._prompt(chunks, question)

    def _search(
        self,
        q: Point3D,
        grey_pts: list[Point3D],
        chunk_pts: list[Point3D],
        space: Mobject,
        mids: VGroup,
    ) -> None:
        self.voice("rag_4")
        pts = np.array(grey_pts + chunk_pts)
        self.cue("checking every")
        brute = VGroup(
            *[Line(q, p, stroke_width=1, color=RED, stroke_opacity=0.5) for p in pts]
        )
        self.play(
            LaggedStart(*[Create(line) for line in brute], lag_ratio=0.01),
            run_time=1.5,
        )
        self.play(FadeOut(brute), run_time=0.6)
        self.cue("approximate")
        ann = T("approximate nearest neighbor search", 28, YELLOW).next_to(
            space, UP, buff=0.15
        )
        self.play(Write(ann))
        edges: set[tuple[int, int]] = set()
        for i in range(len(pts)):
            for j in np.argsort(np.linalg.norm(pts - pts[i], axis=1))[1:4]:
                edges.add((min(i, j), max(i, j)))
        graph = VGroup(
            *[
                Line(pts[i], pts[j], stroke_width=1, color=BLUE_B, stroke_opacity=0.35)
                for i, j in edges
            ]
        )
        self.cue("Clever")
        self.play(Create(graph, lag_ratio=0.02), run_time=1.5)
        adj: dict[int, set[int]] = {i: set() for i in range(len(pts))}
        for i, j in edges:
            adj[i].add(j)
            adj[j].add(i)

        def dist(i: int) -> float:
            return np.linalg.norm(pts[i] - q)

        # Greedy walk on the neighbor graph, from the point farthest from the query.
        cur = int(np.argmax([dist(i) for i in range(len(pts))]))
        path = [cur]
        while dist(nxt := min(adj[cur], key=dist)) < dist(cur):
            cur = nxt
            path.append(cur)
        walker = Dot(pts[path[0]], radius=0.09, color=YELLOW)
        self.play(FadeIn(walker, scale=0.5), run_time=0.3)
        hop_time = min(0.4, 2.4 / max(len(path) - 1, 1))
        for i, j in pairwise(path):
            self.play(
                Create(Line(pts[i], pts[j], color=YELLOW, stroke_width=4)),
                walker.animate.move_to(pts[j]),
                run_time=hop_time,
            )
        top3 = np.argsort([dist(i) for i in range(len(pts))])[:3]
        circ = Circle(radius=dist(top3[-1]) + 0.18, color=YELLOW).move_to(q)
        ms = T("milliseconds", 28, GREEN).next_to(circ, UP, buff=0.1)
        ms_bg = BackgroundRectangle(ms, fill_opacity=0.85, buff=0.06)
        self.play(
            GrowFromCenter(circ),
            *[
                Indicate(mids[i - len(grey_pts)], scale_factor=1.8, color=WHITE)
                for i in top3
            ],
            FadeIn(ms_bg),
            FadeIn(ms, shift=LEFT * 0.2),
        )
        self.finish()

    def _prompt(self, chunks: VGroup, question: Text) -> None:
        self.voice("rag_5")
        top = [chunks[i] for i in sorted(ANSWER_OFFSETS)]
        rest = [c for i, c in enumerate(chunks) if i not in ANSWER_OFFSETS]
        self.play(
            *[
                FadeOut(m)
                for m in self.mobjects
                if not isinstance(m, ValueTracker) and m not in (chunks, question)
            ],
            *[FadeOut(c) for c in rest],
        )
        prompt_box = RoundedRectangle(
            corner_radius=0.15, width=4.4, height=3.6, stroke_color=GREY_B
        ).move_to(LEFT * 3.3)
        prompt_lbl = T("prompt", 28, GREY_B).next_to(prompt_box, UP, buff=0.15)
        layout = (
            VGroup(question.copy().scale(0.8), *[c.copy() for c in top])
            .arrange(DOWN, buff=0.25)
            .move_to(prompt_box)
        )
        self.play(
            Create(prompt_box),
            FadeIn(prompt_lbl),
            question.animate.scale(0.8).move_to(layout[0]),
            *[c.animate.move_to(t) for c, t in zip(top, layout[1:], strict=True)],
            run_time=1.5,
        )
        llm = box("LLM", 2.0, 1.3, BLUE, 40).move_to(RIGHT * 1.6)
        arr1 = Arrow(prompt_box.get_right(), llm.get_left(), buff=0.15)
        answer = T("answer", 36, GREEN).move_to(RIGHT * 5.2)
        arr2 = Arrow(llm.get_right(), answer.get_left(), buff=0.2)
        self.cue("language model")
        self.play(GrowArrow(arr1), FadeIn(llm))
        self.cue("answer")
        self.play(GrowArrow(arr2), Write(answer))
        self.finish()
        self.fade_all()


class Problem(Narrated):
    """Vector search ranks a keyword match above the real answer, and why."""

    @override
    def construct(self) -> None:
        q, qbox, ranks, rows, head = results_table()

        self.voice("prob_1")
        self.cue("How do")
        self.play(Write(q), Create(qbox), run_time=1.5)
        self.finish()

        self.voice("prob_2")
        self.play(
            FadeIn(head),
            LaggedStart(
                *[
                    AnimationGroup(
                        FadeIn(rk),
                        FadeIn(row[0], shift=RIGHT * 0.2),
                        GrowFromEdge(row[1], LEFT),
                        FadeIn(row[2]),
                    )
                    for rk, row in zip(ranks, rows, strict=True)
                ],
                lag_ratio=0.3,
            ),
            run_time=2.5,
        )
        self.finish()

        self.voice("prob_3")
        good = SurroundingRectangle(
            VGroup(ranks[2], rows[2]), color=GREEN, buff=0.12, corner_radius=0.08
        )
        good_lbl = T("the actual answer", 24, GREEN).next_to(
            good, DOWN, buff=0.08, aligned_edge=LEFT
        )
        self.play(Create(good), FadeIn(good_lbl))
        self.cue("top hit")
        bad = SurroundingRectangle(
            VGroup(ranks[0], rows[0]), color=RED, buff=0.12, corner_radius=0.08
        )
        self.play(Create(bad))
        self.cue("right words")
        s0 = RESULTS[0][0]
        self.play(
            *[
                part(rows[0][0], s0, w).animate.set_color(RED)
                for w in ("Subscribe", "Cancel")
            ],
            *[
                part(q, QUESTION, w).animate.set_color(RED)
                for w in ("cancel", "subscription")
            ],
        )
        self.finish()
        self._never_meet()

    def _never_meet(self) -> None:
        self.voice("prob_4")
        self.fade_all()
        chunk = T(RESULTS[0][0], 22).move_to((-6.6, 1.5, 0), aligned_edge=LEFT)
        question = T(QUESTION, 24, YELLOW).move_to((-6.6, -1.5, 0), aligned_edge=LEFT)
        e1 = box("embed", 1.6, 0.8, BLUE, 26).move_to((2.3, 1.5, 0))
        e2 = box("embed", 1.6, 0.8, BLUE, 26).move_to((2.3, -1.5, 0))
        rng = np.random.default_rng(2)
        v1 = cells(rng.uniform(-1, 1, 8), 0.2).move_to((4.9, 1.5, 0))
        v2 = cells(rng.uniform(-1, 1, 8), 0.2).move_to((4.9, -1.5, 0))
        when1 = T("indexed days ago", 24, GREY_B).next_to(
            chunk, UP, buff=0.3, aligned_edge=LEFT
        )
        when2 = T("asked just now", 24, GREY_B).next_to(
            question, UP, buff=0.3, aligned_edge=LEFT
        )
        self.cue("compresses")
        self.play(FadeIn(when1), FadeIn(chunk))
        self.play(
            GrowArrow(Arrow(chunk.get_right(), e1.get_left(), buff=0.15)),
            FadeIn(e1),
            run_time=0.8,
        )
        self.play(
            GrowArrow(Arrow(e1.get_right(), v1.get_left(), buff=0.15)),
            FadeIn(v1, shift=RIGHT * 0.3),
            run_time=0.8,
        )
        self.cue("before it ever")
        self.play(FadeIn(when2), FadeIn(question))
        self.play(
            GrowArrow(Arrow(question.get_right(), e2.get_left(), buff=0.15)),
            FadeIn(e2),
            run_time=0.8,
        )
        self.play(
            GrowArrow(Arrow(e2.get_right(), v2.get_left(), buff=0.15)),
            FadeIn(v2, shift=RIGHT * 0.3),
            run_time=0.8,
        )
        self.cue("guess")
        cmp = DoubleArrow(v1.get_bottom(), v2.get_top(), buff=0.15, color=WHITE)
        score = T("0.89", 30, BLUE).next_to(cmp, RIGHT, buff=0.2)
        fixed = T("fixed in advance", 22, GREY_B).next_to(v1, UP, buff=0.2)
        self.play(GrowFromCenter(cmp), FadeIn(score), FadeIn(fixed))
        self.cue("never actually")
        gap = DashedLine((-3, 1.2, 0), (-3, -1.0, 0), color=RED)
        cross = Cross(Square(0.5), stroke_color=RED, stroke_width=6).move_to(gap)
        self.play(Create(gap), Create(cross))
        self.finish()
        self.fade_all()


class Rerank(Narrated):
    """Bi-encoder versus cross-encoder, attention across the pair, and the re-sort."""

    @override
    def construct(self) -> None:
        self.voice("rr_1")
        title = T("Reranking", 72, YELLOW)
        sub = T("cross-encoder", 40, GREY_B).next_to(title, DOWN, buff=0.4)
        self.play(Write(title))
        self.cue("cross-encoder")
        self.play(FadeIn(sub, shift=UP * 0.2))
        self.finish()

        self.voice("rr_2")
        self.play(FadeOut(VGroup(title, sub)), run_time=0.5)
        divider = DashedLine(UP * 3.2, DOWN * 3.2, color=GREY_D)
        bi_head = T("bi-encoder", 36, BLUE).move_to((-3.6, 2.8, 0))
        qlab = T("query", 26, YELLOW).move_to((-6.0, 1.1, 0))
        dlab = T("document", 26).move_to((-6.0, -1.1, 0))
        enc1 = box("encoder", 1.7, 0.75, BLUE, 24).move_to((-3.75, 1.1, 0))
        enc2 = box("encoder", 1.7, 0.75, BLUE, 24).move_to((-3.75, -1.1, 0))
        rng = np.random.default_rng(5)
        v1 = cells(rng.uniform(-1, 1, 5), 0.18).move_to((-2.4, 1.1, 0))
        v2 = cells(rng.uniform(-1, 1, 5), 0.18).move_to((-2.4, -1.1, 0))
        cos = VGroup(Circle(radius=0.42, color=WHITE), T("cos", 24)).move_to(
            (-1.0, 0, 0)
        )
        s_bi = T("0.89", 28, BLUE).move_to((-1.0, -1.9, 0))
        self.play(Create(divider), Write(bi_head))
        self.cue("query and")
        self.play(FadeIn(qlab), FadeIn(dlab))
        self.cue("separately")
        self.play(
            FadeIn(enc1),
            FadeIn(enc2),
            GrowArrow(Arrow(qlab.get_right(), enc1.get_left(), buff=0.1)),
            GrowArrow(Arrow(dlab.get_right(), enc2.get_left(), buff=0.1)),
        )
        self.play(
            GrowArrow(Arrow(enc1.get_right(), v1.get_left(), buff=0.1)),
            FadeIn(v1),
            GrowArrow(Arrow(enc2.get_right(), v2.get_left(), buff=0.1)),
            FadeIn(v2),
        )
        self.cue("compare")
        self.play(
            FadeIn(cos),
            GrowArrow(Arrow(v1.get_right(), cos.get_top() + LEFT * 0.1, buff=0.1)),
            GrowArrow(Arrow(v2.get_right(), cos.get_bottom() + LEFT * 0.1, buff=0.1)),
        )
        self.play(
            GrowArrow(Arrow(cos.get_bottom(), s_bi.get_top(), buff=0.1)), FadeIn(s_bi)
        )
        self.finish()
        self._cross_encoder()
        self._attention()
        self._rerank()

    def _cross_encoder(self) -> None:
        self.voice("rr_3")
        cross_head = T("cross-encoder", 36, YELLOW).move_to((3.6, 2.8, 0))
        inp = VGroup(T("query", 26, YELLOW), T("+", 26), T("document", 26)).arrange(
            RIGHT, buff=0.25
        )
        inbox = SurroundingRectangle(inp, buff=0.18, corner_radius=0.1, color=GREY_B)
        VGroup(inp, inbox).move_to((3.6, 1.3, 0))
        enc3 = box("encoder", 3.0, 0.9, YELLOW, 28).move_to((3.6, -0.3, 0))
        s_cross = T("relevance score", 28, YELLOW).move_to((3.6, -1.9, 0))
        self.play(Write(cross_head))
        self.cue("together")
        self.play(FadeIn(inp), Create(inbox))
        self.play(
            GrowArrow(Arrow(inbox.get_bottom(), enc3.get_top(), buff=0.1)),
            FadeIn(enc3),
        )
        self.cue("Every word")
        arcs = VGroup(
            *[
                ArcBetweenPoints(
                    inp[0].get_top() + RIGHT * dx,
                    inp[2].get_top() + RIGHT * dy,
                    angle=-PI / 2,
                    color=YELLOW,
                    stroke_width=2,
                )
                for dx, dy in [(-0.3, -0.4), (0, 0), (0.3, 0.4), (-0.1, 0.3)]
            ]
        )
        self.play(LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.2), run_time=1.5)
        self.play(
            GrowArrow(Arrow(enc3.get_bottom(), s_cross.get_top(), buff=0.1)),
            FadeIn(s_cross),
        )
        self.finish()

    def _attention(self) -> None:
        self.voice("rr_4")
        self.fade_all()
        qwords = ["How", "do", "I", "cancel", "my", "subscription?"]
        qrow = (
            VGroup(*[T(w, 30, YELLOW) for w in qwords])
            .arrange(RIGHT, buff=0.35)
            .move_to(UP * 2.2)
        )
        cancel = qwords.index("cancel")

        def doc_row(words: list[str]) -> VGroup:
            return (
                VGroup(*[T(w, 30) for w in words])
                .arrange(RIGHT, buff=0.35)
                .move_to(DOWN * 0.5)
            )

        def attention(dr: VGroup, *, hot: bool) -> VGroup:
            lines = VGroup()
            for i, a in enumerate(qrow):
                for b in dr:
                    on = hot and i == cancel
                    lines.add(
                        Line(
                            a.get_bottom() + DOWN * 0.12,
                            b.get_top() + UP * 0.12,
                            stroke_width=2.5 if on else 1,
                            color=YELLOW if on else GREY_B,
                            stroke_opacity=0.9 if on else 0.18,
                        )
                    )
            return lines

        d1 = doc_row(
            ["Subscribe", "today!", "Cancel", "anytime,", "no", "questions", "asked."]
        )
        d3 = doc_row(
            ["To", "cancel,", "open", "Settings", "→", "Billing", "→", "End", "plan."]
        )
        lines = attention(d1, hot=False)
        self.play(FadeIn(qrow), FadeIn(d1), Create(lines, lag_ratio=0.01), run_time=1.5)
        self.cue("cancel")
        self.play(
            Transform(lines, attention(d1, hot=True)),
            qrow[cancel].animate.scale(1.15),
            run_time=1,
        )
        score_lbl = T("relevance", 30, GREY_B)
        s1 = T("0.12", 48, RED)
        VGroup(score_lbl, s1).arrange(RIGHT, buff=0.4).move_to(DOWN * 2.4)
        self.cue("marketing")
        self.play(FadeIn(score_lbl), FadeIn(s1, scale=1.4))
        self.cue("instead")
        s3 = T("0.97", 48, GREEN).move_to(s1)
        self.play(
            Transform(d1, d3),
            Transform(lines, attention(d3, hot=True)),
            Transform(s1, s3),
            run_time=1.2,
        )
        self.cue("one number")
        self.play(Circumscribe(s1, color=YELLOW, buff=0.15), run_time=1.5)
        self.finish()

    def _rerank(self) -> None:
        self.voice("rr_5")
        self.fade_all(0.4)
        q, qbox, ranks, rows, head = results_table()
        self.play(FadeIn(VGroup(q, qbox, ranks, rows, head)), run_time=0.6)
        rhead = T("rerank", 24, YELLOW).move_to((6.5, 2.0, 0))
        rs = VGroup(
            *[
                T(num(r), 26, YELLOW).move_to((6.5, row.get_y(), 0))
                for row, (_, _, r) in zip(rows, RESULTS, strict=True)
            ]
        )
        self.play(
            FadeIn(rhead),
            LaggedStart(*[FadeIn(x, shift=LEFT * 0.2) for x in rs], lag_ratio=0.15),
            run_time=1.0,
        )
        self.cue("sort")
        order = sorted(range(len(RESULTS)), key=lambda i: -RESULTS[i][2])
        ys = [r.get_y() for r in rows]
        self.play(
            *[
                VGroup(rows[i], rs[i]).animate.shift(UP * (ys[k] - ys[i]))
                for k, i in enumerate(order)
            ],
            run_time=1.5,
        )
        self.play(
            Create(
                SurroundingRectangle(
                    VGroup(ranks[0], rows[order[0]], rs[order[0]]),
                    color=GREEN,
                    buff=0.12,
                    corner_radius=0.08,
                )
            )
        )
        self.finish()
        self.fade_all()


class Cost(Narrated):
    """Why the reranker cannot see every document, and the two-stage funnel."""

    @override
    def construct(self) -> None:
        self.voice("cost_1")
        title = T("Why not rerank everything?", 44).to_edge(UP, buff=0.5)
        self.play(Write(title))
        ce = box("cross-encoder", 3.2, 1.4, YELLOW, 32).move_to(DOWN * 0.3)
        qtag = T("query", 28, YELLOW).next_to(ce, UP, buff=0.8)
        self.cue("Because")
        self.play(
            FadeIn(ce),
            FadeIn(qtag),
            GrowArrow(Arrow(qtag.get_bottom(), ce.get_top(), buff=0.1)),
        )
        pre = T("nothing to precompute", 28, RED).next_to(ce, DOWN, buff=0.4)
        self.play(FadeIn(pre))
        count = ValueTracker(0)
        counter_lbl = T("model passes", 26, GREY_B).move_to((4.8, 0.4, 0))
        counter = always_redraw(
            lambda: T(f"{round(count.get_value()):,}", 44).next_to(counter_lbl, DOWN)
        )
        docs = (
            VGroup(*[page(0.5, 0.65) for _ in range(8)])
            .arrange(RIGHT, buff=0.12)
            .move_to((-4.4, -0.3, 0))
        )
        self.cue("every new")
        self.play(FadeIn(docs), FadeIn(counter_lbl), FadeIn(counter))
        self.play(
            LaggedStart(
                *[
                    d.animate.move_to(ce).scale(0.3).set_opacity(0)
                    for d in reversed(docs)
                ],
                lag_ratio=0.5,
            ),
            count.animate.set_value(len(docs)),
            run_time=4,
            rate_func=linear,
        )
        self.finish()

        self.voice("cost_2")
        start, end = len(docs), 10_000_000
        # Exponential growth, so the count visibly climbs through every power of ten.
        self.play(
            count.animate.set_value(end),
            rate_func=lambda t: (start * (end / start) ** t - start) / (end - start),
            run_time=2.5,
        )
        per = T("for ONE question", 30, RED).next_to(counter, DOWN, buff=0.3)
        self.play(FadeIn(per, shift=UP * 0.2))
        self.finish()
        self._two_lanes()
        self._funnel()

    def _two_lanes(self) -> None:
        self.voice("cost_3")
        self.fade_all()
        lane1 = T("once, ahead of time", 26, GREY_B).move_to((-4.4, 2.5, 0))
        docs = (
            VGroup(*[page(0.4, 0.52) for _ in range(5)])
            .arrange(RIGHT, buff=0.1)
            .move_to((-4.4, 1.5, 0))
        )
        emb1 = box("embed", 1.6, 0.8, BLUE, 26).move_to((-1.2, 1.5, 0))
        idx_rect = Rectangle(width=2.6, height=3.6, stroke_color=GREY_B).move_to(
            (4.4, 0, 0)
        )
        rng = np.random.default_rng(9)
        idx_dots = VGroup(
            *[
                Dot(
                    (4.4 + rng.uniform(-1.1, 1.1), rng.uniform(-1.6, 1.6), 0),
                    radius=0.04,
                    color=GREY_C,
                )
                for _ in range(40)
            ]
        )
        idx_lbl = T("vector index", 24, GREY_B).next_to(idx_rect, DOWN, buff=0.15)
        lane2 = T("per question", 26, GREY_B).move_to((-4.4, -0.6, 0))
        query = T("query", 30, YELLOW).move_to((-4.4, -1.5, 0))
        emb2 = box("embed", 1.6, 0.8, BLUE, 26).move_to((-1.2, -1.5, 0))
        a2 = Arrow(emb1.get_right(), idx_rect.get_left() + UP * 1.0, buff=0.15)
        b2 = Arrow(emb2.get_right(), idx_rect.get_left() + DOWN * 1.0, buff=0.15)
        self.cue("Documents")
        self.play(
            FadeIn(lane1),
            FadeIn(docs),
            FadeIn(emb1),
            GrowArrow(Arrow(docs.get_right(), emb1.get_left(), buff=0.15)),
        )
        self.play(GrowArrow(a2), Create(idx_rect), FadeIn(idx_dots), FadeIn(idx_lbl))
        self.cue("A query")
        self.play(
            FadeIn(lane2),
            FadeIn(query),
            FadeIn(emb2),
            GrowArrow(Arrow(query.get_right(), emb2.get_left(), buff=0.15)),
        )
        self.play(FadeIn(T("1 pass", 24, GREEN).next_to(emb2, DOWN, buff=0.15)))
        self.cue("fast index")
        self.play(
            GrowArrow(b2),
            FadeIn(T("ms lookup", 24, GREEN).next_to(b2.get_center(), DOWN, buff=0.35)),
        )
        self.finish()

    def _funnel(self) -> None:
        self.voice("cost_4")
        self.fade_all()
        cx = -1.2
        rng = np.random.default_rng(11)
        dots_a = VGroup(
            *[
                Dot(
                    (cx + rng.uniform(-4.4, 4.4), 2.7 + rng.uniform(-0.25, 0.25), 0),
                    radius=0.03,
                    color=GREY_B,
                )
                for _ in range(400)
            ]
        )
        pos_b = [
            (cx + rng.uniform(-1.9, 1.9), 0.4 + rng.uniform(-0.2, 0.2), 0)
            for _ in range(100)
        ]
        pos_c = [(cx + (k - 2) * 0.35, -1.8, 0) for k in range(5)]
        funnel1 = Polygon(
            (cx - 4.6, 2.3, 0),
            (cx + 4.6, 2.3, 0),
            (cx + 2.1, 0.8, 0),
            (cx - 2.1, 0.8, 0),
            stroke_color=BLUE,
            fill_color=BLUE,
            fill_opacity=0.12,
        )
        funnel2 = Polygon(
            (cx - 2.1, 0.0, 0),
            (cx + 2.1, 0.0, 0),
            (cx + 0.9, -1.4, 0),
            (cx - 0.9, -1.4, 0),
            stroke_color=YELLOW,
            fill_color=YELLOW,
            fill_opacity=0.12,
        )
        right = 5.3
        lbl_a = T("10,000,000 chunks", 28).move_to((right, 2.7, 0))
        self.play(FadeIn(dots_a, lag_ratio=0.002), FadeIn(lbl_a), run_time=1.2)
        self.cue("Vector search")
        self.play(
            FadeIn(funnel1), Write(T("vector search", 30, BLUE).move_to((cx, 1.55, 0)))
        )
        keep = rng.choice(len(dots_a), 100, replace=False)
        drop = [d for i, d in enumerate(dots_a) if i not in set(keep)]
        self.play(
            *[
                dots_a[i].animate.move_to(p).set_color(BLUE_B).scale(1.3)
                for i, p in zip(keep, pos_b, strict=True)
            ],
            *[FadeOut(d) for d in drop],
            run_time=1.8,
        )
        self.play(FadeIn(T("100 candidates", 28).move_to((right, 0.4, 0))))
        self.cue("Fast, but")
        self.play(FadeIn(T("fast · rough", 26, BLUE).move_to((right, 1.55, 0))))
        self.cue("The reranker")
        self.play(
            FadeIn(funnel2), Write(T("reranker", 30, YELLOW).move_to((cx, -0.7, 0)))
        )
        best = keep[:5]
        self.play(
            *[
                dots_a[i].animate.move_to(p).set_color(YELLOW).scale(2.5)
                for i, p in zip(best, pos_c, strict=True)
            ],
            *[FadeOut(dots_a[i]) for i in keep[5:]],
            run_time=1.5,
        )
        self.play(
            FadeIn(T("top 5", 28).move_to((right, -1.8, 0))),
            FadeIn(T("slow · careful", 26, YELLOW).move_to((right, -0.7, 0))),
        )
        self.cue("those five")
        llm = box("LLM", 1.8, 0.8, GREEN, 30).move_to((cx, -3.2, 0))
        self.play(GrowArrow(Arrow((cx, -2.0, 0), llm.get_top(), buff=0.1)), FadeIn(llm))
        self.finish()
        self.fade_all()


class Outro(Narrated):
    """Recap: embeddings cast a wide net, reranking looks closely."""

    @override
    def construct(self) -> None:
        rng = np.random.default_rng(13)
        divider = DashedLine(UP * 3, DOWN * 2.6, color=GREY_D)

        self.voice("out_1")
        eh = T("Embeddings", 48, BLUE).move_to((-3.6, 2.6, 0))
        cloud = VGroup(
            *[
                Dot(
                    (
                        np.clip(-3.6 + rng.normal(0, 1.1), -6.4, -0.8),
                        np.clip(rng.normal(0.2, 0.75), -1.4, 1.9),
                        0,
                    ),
                    radius=0.05,
                    color=GREY_B,
                )
                for _ in range(70)
            ]
        )
        self.play(
            Write(eh), FadeIn(cloud, lag_ratio=0.02), Create(divider), run_time=1.5
        )
        self.cue("geometry")
        e1 = T("meaning → geometry", 28).move_to((-3.6, -1.9, 0))
        self.play(FadeIn(e1))
        self.cue("recall")
        net_center = np.array([-3.4, 0.3, 0])
        net_radius = 1.5
        net = DashedVMobject(
            Circle(radius=net_radius, color=BLUE), num_dashes=40
        ).move_to(net_center)
        caught = [
            d for d in cloud if np.linalg.norm(d.get_center() - net_center) < net_radius
        ]
        e2 = T("recall: a wide net, fast", 28, BLUE).next_to(e1, DOWN, buff=0.25)
        self.play(
            GrowFromCenter(net),
            *[d.animate.set_color(BLUE) for d in caught],
            FadeIn(e2),
            run_time=1.2,
        )
        self.finish()

        self.voice("out_2")
        rh = T("Reranking", 48, YELLOW).move_to((3.6, 2.6, 0))
        cards = VGroup(
            *[
                RoundedRectangle(
                    corner_radius=0.08, width=2.6, height=0.4, stroke_color=GREY_B
                )
                for _ in range(5)
            ]
        )
        cards.arrange(DOWN, buff=0.15).move_to((3.6, 0.2, 0))
        glass = Circle(radius=0.4, color=YELLOW, stroke_width=5)
        handle = Line(ORIGIN, DR * 0.45, color=YELLOW, stroke_width=7)
        handle.shift(glass.point_at_angle(-PI / 4) - handle.get_start())
        lens = VGroup(glass, handle).move_to(cards[0].get_right() + RIGHT * 0.3)
        r1 = T("precision: a careful look", 28, YELLOW).move_to((3.6, -1.9, 0))
        self.play(Write(rh), FadeIn(cards, lag_ratio=0.1), FadeIn(lens), run_time=1.2)
        self.play(
            lens.animate.move_to(cards[-1].get_right() + RIGHT * 0.3), run_time=1.5
        )
        self.play(cards[1].animate.set_fill(YELLOW, 0.5), FadeIn(r1))
        self.finish()

        self.voice("out_3")
        tag = T("fast & rough   →   slow & careful", 36).move_to(DOWN * 3.2)
        self.play(Write(tag), run_time=1.5)
        self.cue("And your")
        self.fade_all()
        final = page(1.4, 1.9, YELLOW)
        self.play(FadeIn(final, scale=0.6), run_time=1)
        self.finish(1.0)
        self.fade_all(1.0)
