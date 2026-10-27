"""Scenes, in order. Each Narrated scene plays its clips from script.py.

build.py renders and stitches them. Replace these example scenes, and keep SCENES in
sync with the BEATS keys in script.py.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

# Manim does not put the project folder on sys.path.
sys.path.insert(0, str(Path(__file__).parent))
from explainer import Narrated, T, backed, faint_plane
from manim import (
    GOLD,
    GREEN,
    RED,
    TEAL,
    UP,
    UR,
    YELLOW,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    GrowFromCenter,
    LaggedStart,
    Line,
    VGroup,
    Write,
)
from typing_extensions import override

SCENES: Final = ["Title", "Idea"]


class Title(Narrated):
    """The hook question."""

    @override
    def construct(self) -> None:
        q = T("Same meaning, different words?", 52, YELLOW)
        self.voice("title_1")
        self.play(Write(q), run_time=2)
        self.cue("Let's draw")
        self.play(q.animate.scale(0.6).to_edge(UP))
        self.finish()
        self.fade_all()


class Idea(Narrated):
    """Sentences as points: near means similar."""

    @override
    def construct(self) -> None:
        plane = faint_plane()
        points = {
            "a cat sleeps": (-3, 1.2, TEAL),
            "a kitten naps": (-2.2, 0.6, TEAL),
            "stock prices fell": (3.2, -1.6, GOLD),
        }
        dots = {
            n: Dot((x, y, 0), radius=0.09, color=c) for n, (x, y, c) in points.items()
        }
        labels = VGroup(
            *[
                backed(T(n, 26, points[n][2])).next_to(d, UR, buff=0.05)
                for n, d in dots.items()
            ]
        )

        self.voice("idea_1")
        self.play(Create(plane), run_time=1.5)
        self.cue("point in space")
        grow = [GrowFromCenter(d) for d in dots.values()]
        self.play(LaggedStart(*grow, lag_ratio=0.3), FadeIn(labels))
        self.finish()

        self.voice("idea_2")
        cat, kitten = dots["a cat sleeps"], dots["a kitten naps"]
        near = Line(cat.get_center(), kitten.get_center(), color=GREEN, stroke_width=5)
        far = DashedLine(
            cat.get_center(), dots["stock prices fell"].get_center(), color=RED
        )
        self.cue("Short")
        self.play(Create(near))
        self.cue("Long")
        self.play(Create(far))
        self.finish()
        self.fade_all()
