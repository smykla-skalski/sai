"""WebTransport, 3b1b style. Each Narrated scene plays its clips from script.py.

build.py renders SCENES in order and stitches them.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

# Manim does not put the project folder on sys.path.
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from explainer import (
    M,
    Narrated,
    T,
    box,
    cross,
    flow,
    lit,
    packet,
    part,
    server,
    tick,
    unit,
    window,
)
from manim import (
    BLACK,
    BLUE,
    BLUE_B,
    BLUE_C,
    DOWN,
    GOLD,
    GREEN,
    GREY_A,
    GREY_B,
    GREY_C,
    GREY_D,
    GREY_E,
    LEFT,
    ORANGE,
    PI,
    PURPLE_B,
    RED,
    RED_E,
    RIGHT,
    TEAL,
    UP,
    YELLOW,
    Arc,
    ArcBetweenPoints,
    Arrow,
    Brace,
    Create,
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
    MoveToTarget,
    Rectangle,
    ReplacementTransform,
    RoundedRectangle,
    Square,
    SurroundingRectangle,
    Transform,
    ValueTracker,
    VGroup,
    VMobject,
    Write,
    linear,
    rush_into,
)
from typing_extensions import override

if TYPE_CHECKING:
    from manim import Animation, Mobject, ParsableManimColor, Text

SCENES: Final = [
    "Hook",
    "Pipe",
    "Layers",
    "Handshake",
    "Streams",
    "Datagrams",
    "Code",
    "Tradeoffs",
    "Outro",
]
SPEED: Final = 0.35  # flow phase per second: a packet crosses a lane in about 3 s


def sq(label: str, color: ParsableManimColor = BLUE, side: float = 0.42) -> VGroup:
    """Return a packet: a filled square with its label in black."""
    s = Square(
        side, stroke_color=color, stroke_width=2, fill_color=color, fill_opacity=0.9
    )
    return VGroup(s, T(label, side * 50, BLACK).move_to(s))


def browser(w: float = 2.0, h: float = 1.4) -> VGroup:
    """Return a browser window without an address."""
    return window(w, h)


def tube(
    x0: float, x1: float, y: float, h: float = 0.5, color: ParsableManimColor = GREY_B
) -> VGroup:
    """Return a pipe from x0 to x1 at height y: two parallel lines h apart."""
    return VGroup(
        Line((x0, y + h / 2, 0), (x1, y + h / 2, 0)),
        Line((x0, y - h / 2, 0), (x1, y - h / 2, 0)),
    ).set_stroke(color, 2)


def middle(phase: ValueTracker, sqs: VGroup) -> VMobject:
    """Return the square of a flow nearest the middle of its lane."""
    n = len(sqs)
    return sqs[min(range(n), key=lambda i: abs((phase.get_value() + i / n) % 1 - 0.5))]


def lock(color: ParsableManimColor = YELLOW, s: float = 1.0) -> VGroup:
    """Return a padlock."""
    body = (
        RoundedRectangle(corner_radius=0.05, width=0.5, height=0.4)
        .set_fill(color, 1)
        .set_stroke(color, 2)
    )
    shackle = (
        Arc(radius=0.16, start_angle=0, angle=PI)
        .set_stroke(color, 5)
        .next_to(body, UP, buff=0)
    )
    return VGroup(body, shackle).scale(s)


def glide(tracker: ValueTracker, value: float) -> MoveToTarget:
    """Return an animation that moves tracker to value at a constant speed.

    Same as tracker.animate(rate_func=linear).set_value(value), which mypy rejects:
    Manim types .animate as the builder or the mobject, and only the builder can be
    called.
    """
    tracker.generate_target().set_value(value)
    return MoveToTarget(tracker, rate_func=linear)


class Flowing(Narrated):
    """A scene with flows of packets that move while other animations play."""

    def go(self, phases: list[ValueTracker], t: float, *anims: Animation) -> None:
        """Play the flows for t seconds, with any other animations."""
        self.play(
            *[glide(p, p.get_value() + SPEED * t) for p in phases], *anims, run_time=t
        )

    def drop(self, m: VMobject, color: ParsableManimColor = RED) -> None:
        """Lose packet m on the way: it turns red and falls out."""
        m.clear_updaters()
        self.play(m.animate.set_fill(color, 1), run_time=0.2)
        self.play(m.animate.shift(DOWN * 0.7).set_opacity(0), run_time=0.5)


class Hook(Flowing):
    """A browser game freezes when one packet is lost."""

    @override
    def construct(self) -> None:
        win = window(7.0, 4.4, "https://game.example").move_to((-2.2, -0.3, 0))
        mid = win[0].get_center() + DOWN * 0.2
        you = VGroup(Dot(mid + LEFT * 2.2 + DOWN * 0.6, radius=0.16, color=BLUE))
        you.add(T("you", 24, BLUE_B).next_to(you[0], DOWN, buff=0.12))
        third = Dot(mid + RIGHT * 2.3 + DOWN * 1.2, radius=0.16, color=GREEN)
        path = ArcBetweenPoints(
            mid + LEFT * 1.4 + UP * 1.0, mid + RIGHT * 2.2 + UP * 0.2, angle=-PI / 2
        )
        t = ValueTracker(0)
        other = Dot(path.get_start(), radius=0.16, color=RED).add_updater(
            lambda m: m.move_to(path.point_from_proportion(t.get_value()))
        )
        srv = server().move_to((5.6, 0.6, 0))
        srv_l = T("server", 24, GREY_B).next_to(srv, DOWN, buff=0.15)
        link = Line((4.8, 0.6, 0), (win.get_right()[0] + 0.05, 0.6, 0)).set_stroke(
            GREY_D, 2
        )
        phase, dots = flow(link.get_start(), link.get_end(), 7, YELLOW, 0.16)

        self.voice("hook_1")
        self.play(FadeIn(win), FadeIn(you), FadeIn(third), FadeIn(other), run_time=0.8)
        self.play(glide(t, 0.12), run_time=1.4)
        self.cue("Sixty times")
        rate = T("60 updates per second", 22, GREY_B).next_to(link, UP, buff=0.15)
        self.play(
            FadeIn(srv),
            FadeIn(srv_l),
            Create(link),
            FadeIn(rate),
            glide(t, 0.17),
            run_time=0.6,
        )
        self.add(dots)
        self.go([phase], 3.8, glide(t, 0.45))
        self.cue("busy Wi-Fi")
        wifi = T("busy Wi-Fi", 22, GREY_B).next_to(link, DOWN, buff=0.15)
        self.go([phase], 1.6, FadeIn(wifi), glide(t, 0.57))
        self.cue("gets lost")
        self.drop(middle(phase, dots))
        self.cue("freezes")
        frozen = T("frozen", 28, RED).next_to(other, UP, buff=0.15)
        self.play(FadeIn(frozen), run_time=0.3)
        self.cue("then jumps")
        ghost = other.copy().clear_updaters().set_opacity(0.3)
        self.add(ghost)
        self.play(t.animate.set_value(0.95), FadeOut(frozen), run_time=0.2)
        self.finish()

        self.voice("hook_2")
        self.fade_all(run_time=0.5)
        good = (
            VGroup(tick(), T("one missed update", 40, GREEN))
            .arrange(RIGHT, buff=0.35)
            .move_to((0, 0.9, 0))
        )
        bad = (
            VGroup(cross(), T("a frozen screen", 40, RED))
            .arrange(RIGHT, buff=0.35)
            .move_to((0, -0.3, 0))
        )
        bad.align_to(good, LEFT)
        self.cue("one small update")
        self.play(FadeIn(good), run_time=0.5)
        self.cue("frozen screen")
        self.play(FadeIn(bad), run_time=0.5)
        self.cue("called WebTransport")
        title = T("WebTransport", 80, BLUE_B).shift(UP * 0.4)
        self.play(FadeOut(good), FadeOut(bad), Write(title), run_time=1.2)
        self.cue("start with the tool")
        self.play(
            FadeIn(
                T("first, the tool of today: the WebSocket", 32, GREY_B).next_to(
                    title, DOWN, buff=0.6
                )
            ),
            run_time=0.6,
        )
        self.finish()
        self.fade_all()


PIPE_Y: Final = 0.6  # height of the pipe and of the packets in it


class Pipe(Narrated):
    """WebSocket: one TCP pipe, where one lost packet holds up all after it."""

    @override
    def construct(self) -> None:
        y = PIPE_Y
        br = browser(2.4, 1.7).move_to((-5.4, y, 0))
        br_l = T("browser", 24, GREY_B).next_to(br, UP, buff=0.15)
        srv = server().move_to((5.6, y, 0))
        srv_l = T("server", 24, GREY_B).next_to(srv, UP, buff=0.15)
        pipe = tube(-4.0, 4.8, y, 0.7)
        pipe_l = T("one TCP connection", 26, GREY_B).move_to((0.4, y + 0.7, 0))
        title = T("WebSocket", 44).move_to((0, 3.2, 0))

        self.voice("pipe_1")
        self.play(FadeIn(br), FadeIn(br_l), FadeIn(srv), FadeIn(srv_l), run_time=0.8)
        self.cue("WebSocket")
        self.play(Write(title), run_time=0.6)
        self.cue("ordinary web request")
        req = packet("GET /play  Upgrade: websocket", GREY_B).move_to((-1.6, y, 0))
        self.play(FadeIn(req), run_time=0.3)
        self.play(req.animate.move_to((2.4, y, 0)), run_time=0.9)
        self.cue("upgrades")
        ok = packet("101 Switching Protocols", GREEN).move_to((2.6, y, 0))
        self.play(ReplacementTransform(req, ok), run_time=0.4)
        self.play(ok.animate.move_to((-1.8, y, 0)), run_time=0.8)
        self.cue("long-lived")
        self.play(FadeOut(ok), Create(pipe), FadeIn(pipe_l), run_time=0.8)
        self.cue("single pipe")
        self.play(Indicate(pipe, color=YELLOW, scale_factor=1.03), run_time=0.8)
        self.finish()

        row, page_l = self._head_of_line(title)
        self._shared_pipe(row, page_l)
        self.fade_all()

    def _head_of_line(self, title: Text) -> tuple[list[VGroup], Text]:
        y = PIPE_Y
        self.voice("pipe_2")
        promise = T("TCP: every byte arrives, in order", 40, YELLOW).move_to(title)
        self.play(ReplacementTransform(title, promise), run_time=0.8)
        pk = [sq(str(i)).move_to((0.9 + 0.55 * (i - 1), y, 0)) for i in range(1, 7)]
        page = [np.array([-6.4 + 0.5 * k, -0.9, 0]) for k in range(6)]
        self.cue("Every byte")
        self.play(LaggedStart(*[FadeIn(p) for p in pk], lag_ratio=0.15), run_time=0.8)
        self.cue("packet three is lost")
        page_l = T("handed to the page", 22, GREY_B).move_to((-5.15, -1.45, 0))
        self.play(
            pk[0].animate.move_to(page[0]),
            pk[1].animate.move_to(page[1]),
            pk[2].animate.move_to((-0.5, y, 0)),
            *[pk[i].animate.shift(LEFT * 0.5) for i in (3, 4, 5)],
            FadeIn(page_l),
            run_time=1.0,
        )
        self.play(pk[2].animate.set_color(RED), run_time=0.2)
        self.play(pk[2].animate.shift(DOWN * 0.8).set_opacity(0), run_time=0.5)
        self.remove(pk[2])
        self.cue("four, five and six")
        buf = [np.array([-3.5 + 0.55 * k, y, 0]) for k in range(3)]
        self.play(*[pk[3 + k].animate.move_to(buf[k]) for k in range(3)], run_time=0.9)
        self.cue("cannot hand them")
        bar = Line((-3.95, y - 0.4, 0), (-3.95, y + 0.4, 0)).set_stroke(RED, 6)
        self.play(Create(bar), run_time=0.4)
        self.cue("wait in a buffer")
        box_ = DashedVMobject(
            SurroundingRectangle(VGroup(*pk[3:]), buff=0.1, color=GREY_B),
            num_dashes=30,
        )
        box_l = T("waiting in a buffer", 20, GREY_B).move_to((-2.75, -0.1, 0))
        self.play(Create(box_), FadeIn(box_l), run_time=0.5)
        self.finish()

        self.voice("pipe_3")
        self.cue("sends packet three again")
        p3 = sq("3").move_to((4.3, y, 0))
        again = T("sent again, one round trip later", 22, YELLOW).move_to(
            (1.9, -0.1, 0)
        )
        self.play(FadeIn(p3), FadeIn(again), run_time=0.4)
        self.play(p3.animate.move_to((-1.85, y, 0)), run_time=2.2, rate_func=linear)
        self.cue("at once")
        row = [pk[0], pk[1], p3, *pk[3:]]
        self.play(
            *[p.animate.move_to(page[k + 2]) for k, p in enumerate(row[2:])],
            FadeOut(bar),
            FadeOut(box_),
            FadeOut(box_l),
            FadeOut(again),
            run_time=0.9,
        )
        self.cue("head-of-line")
        hol = T("head-of-line blocking", 44, YELLOW).move_to(promise)
        self.play(ReplacementTransform(promise, hol), run_time=0.8)
        self.finish()
        return row, page_l

    def _shared_pipe(self, row: list[VGroup], page_l: Text) -> None:
        y = PIPE_Y
        self.voice("pipe_4")
        self.cue("already old")
        old_l = T("old", 22, GREY_B).move_to((-5.15, -1.45, 0))
        self.play(
            *[row[i][0].animate.set_fill(GREY_D).set_stroke(GREY_D) for i in (2, 3, 4)],
            ReplacementTransform(page_l, old_l),
            run_time=0.6,
        )
        self.cue("newest one")
        new_l = T("newest", 22, YELLOW).next_to(row[5], DOWN, buff=0.15)
        self.play(
            old_l.animate.next_to(VGroup(row[2], row[4]), DOWN, buff=0.15),
            row[5][0].animate.set_fill(YELLOW).set_stroke(YELLOW),
            FadeIn(new_l),
            run_time=0.6,
        )
        self.cue("chat messages")
        kinds = {"p": YELLOW, "c": GREEN, "d": BLUE_C}
        # The first buffer slot, where packet four waited.
        hole = Square(0.42).set_stroke(RED, 2).move_to((-3.5, y, 0))
        hole_l = T("?", 26, RED).move_to(hole)
        queue = VGroup(
            *[
                sq(k, kinds[k]).move_to((-2.95 + 0.55 * i, y, 0))
                for i, k in enumerate("pcdpcd")
            ]
        )
        legend = (
            VGroup(
                *[
                    VGroup(sq(k, c, 0.32), T(n, 22, GREY_B)).arrange(RIGHT, buff=0.15)
                    for (k, c), n in zip(
                        kinds.items(), ("position", "chat", "download"), strict=True
                    )
                ]
            )
            .arrange(RIGHT, buff=0.6)
            .move_to((0.4, -2.3, 0))
        )
        self.play(*[FadeOut(m) for m in [*row, old_l, new_l]], run_time=0.4)
        self.play(
            FadeIn(hole),
            FadeIn(hole_l),
            LaggedStart(*[FadeIn(q, shift=LEFT * 0.3) for q in queue], lag_ratio=0.1),
            FadeIn(legend),
            run_time=1.0,
        )
        self.cue("wait together")
        wait = T("all of them wait", 26, RED).move_to((-1.6, -0.1, 0))
        self.play(
            Indicate(queue, color=RED, scale_factor=1.05), FadeIn(wait), run_time=0.8
        )
        self.finish()


class Layers(Narrated):
    """The two stacks: WebSocket on TCP, WebTransport on HTTP/3, QUIC and UDP."""

    @override
    def construct(self) -> None:
        ys = [2.0, 1.1, 0.2, -0.7, -1.6]
        left = VGroup(
            *[
                box(n, 3.6, 0.75, GREY_B, 30).move_to((-3.4, y, 0))
                for n, y in zip(["WebSocket", "TLS", "TCP", "IP"], ys[1:], strict=True)
            ]
        )
        names = ["WebTransport", "HTTP/3", "QUIC", "UDP", "IP"]
        colors = [BLUE, TEAL, YELLOW, ORANGE, GREY_B]
        right = VGroup(
            *[
                box(n, 3.6, 0.75, c, 30).move_to((3.4, y, 0))
                for n, c, y in zip(names, colors, ys, strict=True)
            ]
        )

        self.voice("layers_1")
        self.play(
            LaggedStart(*[FadeIn(b) for b in left], lag_ratio=0.1),
            FadeIn(right[0]),
            run_time=0.8,
        )
        self.cue("changes what")
        self.play(Indicate(left[1:3], color=GREY_A, scale_factor=1.04), run_time=0.8)
        self.cue("H-T-T-P three")
        self.play(FadeIn(right[1], shift=DOWN * 0.3), run_time=0.5)
        self.cue("That runs on Quick")
        self.play(FadeIn(right[2], shift=DOWN * 0.3), run_time=0.5)
        self.cue("runs on U-D-P")
        self.play(
            FadeIn(right[3], shift=DOWN * 0.3),
            FadeIn(right[4], shift=DOWN * 0.3),
            run_time=0.5,
        )
        self.finish()

        self.voice("layers_2")
        self.play(FadeOut(left), run_time=0.4)
        self.play(right.animate.shift(LEFT * 7.0), run_time=0.6)
        self.play(Indicate(right[3], color=ORANGE), run_time=0.5)
        self.cue("can be lost")
        sent_l = T("sent", 26, GREY_B).move_to((0.0, 1.2, 0))
        got_l = T("arrived", 26, GREY_B).move_to((0.0, -0.4, 0))
        sent = VGroup(
            *[sq(str(i), ORANGE).move_to((1.2 + 0.7 * i, 1.2, 0)) for i in range(1, 5)]
        )
        self.play(FadeIn(sent_l), FadeIn(sent), FadeIn(got_l), run_time=0.4)
        got = sent.copy()
        slots = [np.array([1.9 + 0.7 * k, -0.4, 0]) for k in range(3)]
        self.play(
            got[1].animate.move_to(slots[0]),
            got[0].animate.move_to(slots[1]),
            got[3].animate.move_to(slots[2]),
            got[2].animate.shift(DOWN * 0.8).set_opacity(0),
            run_time=1.0,
        )
        self.cue("builds reliability")
        quic = right[2]
        rel = (
            T("reliable streams", 30, GREEN)
            .next_to(quic, RIGHT, buff=0.6)
            .shift(UP * 0.25)
        )
        self.play(
            FadeOut(VGroup(sent_l, sent, got_l, got)),
            FadeIn(rel, shift=LEFT * 0.2),
            run_time=0.6,
        )
        self.cue("encryption built in")
        tls = M("TLS 1.3", 20, YELLOW)
        tag = VGroup(
            SurroundingRectangle(
                tls, buff=0.08, corner_radius=0.06, color=YELLOW, stroke_width=2
            ),
            tls,
        )
        tag.move_to(quic[0].get_right() + LEFT * 0.75)
        self.play(
            quic[1].animate.shift(LEFT * 0.6), FadeIn(tag, scale=0.6), run_time=0.6
        )
        self.cue("only where you ask")
        dg = T("or unreliable datagrams", 30, YELLOW).next_to(
            rel, DOWN, buff=0.2, aligned_edge=LEFT
        )
        self.play(FadeIn(dg, shift=LEFT * 0.2), run_time=0.5)
        self.finish()
        self.fade_all()


TOP: Final = 2.3  # where both ladder lines and the first round trip start


def ladder(xs: tuple[float, float]) -> VGroup:
    """Return the browser and server lines of a sequence diagram, with their names."""
    cx, sx = xs
    lines = VGroup(
        Line((cx, TOP, 0), (cx, -2.9, 0)), Line((sx, TOP, 0), (sx, -2.9, 0))
    ).set_stroke(GREY_B, 2)
    heads = VGroup(
        T("browser", 22, GREY_B).next_to(lines[0], UP, buff=0.12),
        T("server", 22, GREY_B).next_to(lines[1], UP, buff=0.12),
    )
    return VGroup(lines, heads)


class RoundTrip(NamedTuple):
    """A message to the server and its answer, each with its name, and the trip name."""

    out: tuple[Arrow, Text]
    back: tuple[Arrow, Text]
    name: Text


def leg(
    start: tuple[float, float],
    end: tuple[float, float],
    msg: str,
    color: ParsableManimColor,
) -> tuple[Arrow, Text]:
    """Return an arrow from start to end with the message name along it."""
    (x0, y0), (x1, y1) = start, end
    a = Arrow(
        (x0, y0, 0),
        (x1, y1, 0),
        buff=0.02,
        stroke_width=3,
        color=color,
        max_tip_length_to_length_ratio=0.07,
    )
    ang = np.arctan((y1 - y0) / (x1 - x0))
    lab = (
        M(msg, 18, color).rotate(ang).move_to(a.get_center() + 0.2 * unit(ang + PI / 2))
    )
    return a, lab


def trip(
    xs: tuple[float, float],
    k: int,
    msgs: tuple[str, str],
    name: str,
    color: ParsableManimColor,
) -> RoundTrip:
    """Return round trip k between the ladder lines at xs: msgs out and back."""
    cx, sx = xs
    y = TOP - 1.6 * k
    return RoundTrip(
        leg((cx, y), (sx, y - 0.8), msgs[0], color),
        leg((sx, y - 0.8), (cx, y - 1.6), msgs[1], color),
        T(name, 22, color).next_to((cx, y - 0.8, 0), LEFT, buff=0.15),
    )


class Handshake(Narrated):
    """Round trips before the first message, then the CONNECT request."""

    @override
    def construct(self) -> None:
        tcp, quic = (-5.6, -1.8), (1.8, 5.6)
        head_l = T("WebSocket", 32).move_to((-3.7, 3.4, 0))
        head_r = T("WebTransport", 32, BLUE_B).move_to((3.7, 3.4, 0))
        lad_l, lad_r = ladder(tcp), ladder(quic)
        tl = [
            trip(tcp, 0, ("SYN", "SYN-ACK"), "TCP", GREY_A),
            trip(tcp, 1, ("ClientHello", "ServerHello"), "TLS", GREY_A),
            trip(tcp, 2, ("Upgrade: websocket", "101"), "upgrade", GREY_A),
        ]
        tr = [
            trip(
                quic,
                0,
                ("Initial + TLS hello", "Handshake + TLS"),
                "QUIC + TLS",
                YELLOW,
            ),
            trip(quic, 1, ("CONNECT", "200"), "session", GREEN),
        ]

        def grow(t: RoundTrip) -> None:
            (a, la), (b, lb), name = t
            self.play(GrowArrow(a), FadeIn(la), FadeIn(name), run_time=0.6)
            self.play(GrowArrow(b), FadeIn(lb), run_time=0.6)

        self.voice("hs_1")
        self.play(FadeIn(head_l), FadeIn(lad_l), run_time=0.7)
        self.cue("one round trip")
        grow(tl[0])
        self.cue("a second")
        grow(tl[1])
        self.cue("WebSocket upgrade")
        grow(tl[2])
        self.cue("takes a third")
        three = T("3 round trips", 30, GREY_A).move_to((-3.7, -3.35, 0))
        self.play(FadeIn(three), run_time=0.4)
        self.finish()

        self.voice("hs_2")
        self.play(FadeIn(head_r), FadeIn(lad_r), run_time=0.7)
        self.cue("single round trip")
        grow(tr[0])
        self.cue("One more request")
        grow(tr[1])
        self.cue("two round trips")
        ready = DashedLine(
            (0.4, -0.9, 0), (6.6, -0.9, 0), color=GREEN, dash_length=0.12
        )
        ready_l = T("WebTransport ready", 26, GREEN).move_to((3.7, -1.3, 0))
        two = T("2 round trips", 30, GREEN).move_to((3.7, -3.35, 0))
        self.play(Create(ready), FadeIn(ready_l), FadeIn(two), run_time=0.8)
        self.cue("instead of three")
        self.play(
            Indicate(three, color=RED), Indicate(tl[2].name, color=RED), run_time=0.8
        )
        self.finish()

        self._connect_request()
        self.fade_all()

    def _connect_request(self) -> None:
        self.voice("hs_3")
        self.fade_all(run_time=0.5)
        rows = [
            (":method", "CONNECT"),
            (":protocol", "webtransport-h3"),
            (":scheme", "https"),
            (":authority", "game.example"),
            (":path", "/play"),
        ]
        strs = [f"{k} = {v}" for k, v in rows]
        lines = VGroup(*[M(s, 26, GREY_C) for s in strs]).arrange(
            DOWN, buff=0.16, aligned_edge=LEFT
        )
        req = VGroup(
            SurroundingRectangle(lines, buff=0.25, corner_radius=0.1, color=GREY_D),
            lines,
        ).move_to((-2.9, 1.3, 0))
        req_l = T("request on stream 0", 22, GREY_B).next_to(req, UP, buff=0.15)
        self.play(FadeIn(req), FadeIn(req_l), run_time=0.7)
        self.cue("CONNECT")
        self.play(lit(lines[0], strs[0], "CONNECT"), run_time=0.4)
        self.cue("protocol set to")
        self.play(lit(lines[1], strs[1], "webtransport-h3"), run_time=0.4)
        self.cue("status two hundred")
        res_t = M(":status = 200", 26, GREEN)
        res = VGroup(
            SurroundingRectangle(res_t, buff=0.25, corner_radius=0.1, color=GREEN),
            res_t,
        ).move_to((3.9, 1.3, 0))
        res_l = T("response", 22, GREY_B).next_to(res, UP, buff=0.15)
        self.play(FadeIn(res, shift=LEFT * 0.3), FadeIn(res_l), run_time=0.7)
        self.cue("every stream and datagram")
        br = browser(1.6, 1.1).move_to((-5.8, -1.9, 0))
        srv = server(s=0.8).move_to((5.9, -1.9, 0))
        labels = [
            "stream 4 | session 0",
            "datagram | session 0",
            "stream 8 | session 0",
        ]
        msgs = [
            packet(labels[0], BLUE_B),
            packet(labels[1], YELLOW),
            packet(labels[2], BLUE_B),
        ]
        for i, m in enumerate(msgs):
            m.move_to((-3.0, -1.3 - 0.6 * i, 0))
        self.play(
            FadeIn(br),
            FadeIn(srv),
            LaggedStart(*[FadeIn(m, shift=RIGHT * 0.3) for m in msgs], lag_ratio=0.2),
            run_time=0.6,
        )
        # Manim types LaggedStart to take only Animations, not .animate builders.
        for m in msgs:
            m.generate_target().shift(RIGHT * 6.0)
        self.play(
            LaggedStart(*[MoveToTarget(m) for m in msgs], lag_ratio=0.15),
            run_time=1.3,
        )
        self.cue("I-D of that request")
        tags = [part(m[1], s, "session 0") for m, s in zip(msgs, labels, strict=True)]
        self.play(
            *[t.animate.set_color(GREEN) for t in tags],
            Indicate(req_l, color=GREEN),
            run_time=0.7,
        )
        self.cue("which session")
        self.play(*[Indicate(t, color=GREEN) for t in tags], run_time=0.8)
        self.finish()


LANES: Final = {
    "chat": (0.9, GREEN),
    "map download": (-0.3, BLUE_C),
    "scores": (-1.5, GOLD),
}


def session_frame() -> tuple[VGroup, VGroup, RoundedRectangle, Text]:
    """Return the browser, the server, and the session frame with its label."""
    br = browser().move_to((-5.75, -0.2, 0))
    srv = server().move_to((5.85, -0.2, 0))
    frame = (
        RoundedRectangle(corner_radius=0.2, width=8.8, height=3.8)
        .set_stroke(BLUE_B, 2)
        .move_to((0.1, -0.3, 0))
    )
    label = T("WebTransport session", 26, BLUE_B).next_to(frame, UP, buff=0.12)
    return br, srv, frame, label


class Lane(NamedTuple):
    """A stream between the server and the browser, drawn as a tube with a flow."""

    tube: VGroup
    label: Text
    phase: ValueTracker
    squares: VGroup


def lane(name: str, y: float, color: ParsableManimColor, n: int = 8) -> Lane:
    """Return a lane at height y whose n squares flow from the server to the browser."""
    t = tube(-4.0, 4.2, y, 0.44, GREY_D)
    lab = T(name, 22, color).move_to((-4.0, y + 0.42, 0), aligned_edge=LEFT)
    phase, sqs = flow((4.0, y, 0), (-3.8, y, 0), n, color, 0.24)
    return Lane(t, lab, phase, sqs)


class Streams(Flowing):
    """Streams in one session: each keeps its own order, in two kinds."""

    @override
    def construct(self) -> None:
        br, srv, frame, flabel = session_frame()
        lanes = [lane(n, y, c) for n, (y, c) in LANES.items()]
        chat, mapd, score = lanes
        phases = [ln.phase for ln in lanes]

        self.voice("streams_1")
        self.play(FadeIn(br), FadeIn(srv), Create(frame), FadeIn(flabel), run_time=0.8)
        self.cue("open streams")
        self.play(Create(chat.tube), run_time=0.6)
        self.cue("reliable, ordered")
        self.add(chat.squares)
        self.go([chat.phase], 2.0)
        self.cue("small WebSocket")
        self.go([chat.phase], 1.6)
        self.cue("one more")
        self.add(mapd.squares, score.squares)
        self.go(phases, 1.2, Create(mapd.tube), Create(score.tube))
        self.cue("no extra round trip")
        free = T("new stream: no extra round trip", 26, GREEN).move_to((0.1, -2.65, 0))
        self.go(phases, 1.2, FadeIn(free))
        self.finish()

        self.voice("streams_2")
        self.go(phases, 2.0, FadeOut(free), *[FadeIn(ln.label) for ln in lanes])
        self.cue("separately")
        self.go(phases, 1.6)
        self.cue("chat stream is lost")
        self.drop(middle(chat.phase, chat.squares))
        self.cue("only chat waits")
        waits = T("waits", 24, RED).next_to(chat.label, RIGHT, buff=0.3)
        self.go(
            [mapd.phase, score.phase],
            1.4,
            FadeIn(waits),
            Indicate(chat.label, color=RED),
        )
        self.go([mapd.phase, score.phase], 1.6)
        self.cue("keeps flowing")
        keeps = T("keeps flowing", 24, BLUE_C).next_to(mapd.label, RIGHT, buff=0.3)
        self.go([mapd.phase, score.phase], 1.2, FadeIn(keeps))
        self.finish()

        self._two_kinds(lanes, [waits, keeps], br, srv)
        self.fade_all()

    def _two_kinds(
        self, lanes: list[Lane], notes: list[Text], br: VGroup, srv: VGroup
    ) -> None:
        self.voice("streams_3")
        self.play(
            *[FadeOut(m) for ln in lanes for m in (ln.tube, ln.label, ln.squares)],
            *[FadeOut(m) for m in notes],
            run_time=0.6,
        )
        self.cue("bidirectional")
        bi = DoubleArrow(
            (-4.0, 0.6, 0), (4.2, 0.6, 0), buff=0, color=TEAL, stroke_width=3
        )
        bi_l = T("bidirectional", 26, TEAL).move_to((0.1, 1.05, 0))
        self.play(GrowFromCenter(bi), FadeIn(bi_l), run_time=0.7)
        self.cue("request and its reply")
        rq = packet("request", TEAL).move_to((-2.8, 0.6, 0))
        self.play(FadeIn(rq), run_time=0.2)
        self.play(rq.animate.move_to((3.0, 0.6, 0)), run_time=0.8)
        rp = packet("reply", TEAL).move_to((3.0, 0.6, 0))
        self.play(ReplacementTransform(rq, rp), run_time=0.2)
        self.play(rp.animate.move_to((-2.8, 0.6, 0)), run_time=0.8)
        self.play(FadeOut(rp), run_time=0.2)
        self.cue("unidirectional")
        uni = Arrow(
            (4.2, -1.1, 0), (-4.0, -1.1, 0), buff=0, color=PURPLE_B, stroke_width=3
        )
        uni_l = T("unidirectional", 26, PURPLE_B).move_to((0.1, -0.65, 0))
        self.play(GrowArrow(uni), FadeIn(uni_l), run_time=0.7)
        self.cue("file the server")
        f = packet("file", PURPLE_B).move_to((3.0, -1.1, 0))
        self.play(FadeIn(f), run_time=0.2)
        self.play(f.animate.move_to((-2.8, -1.1, 0)), run_time=1.0)
        self.play(FadeOut(f), run_time=0.2)
        self.cue("Either side")
        either = T("either side can open either kind", 28, YELLOW).move_to(
            (0.1, -2.65, 0)
        )
        self.play(
            FadeIn(either),
            Indicate(br, color=YELLOW),
            Indicate(srv, color=YELLOW),
            run_time=0.8,
        )
        self.finish()


class Datagrams(Flowing):
    """Datagrams: no resends and no order, why a game wants them, and two limits."""

    @override
    def construct(self) -> None:
        y = 0.9
        br = browser().move_to((-5.75, y, 0))
        srv = server().move_to((5.85, y, 0))
        slots = [np.array([-6.4 + 0.52 * k, -0.35, 0]) for k in range(4)]
        arrived = T("arrived", 22, GREY_B).move_to((-5.62, -0.85, 0))

        def fly(m: Mobject, x1: float, run_time: float) -> None:
            self.play(
                m.animate.move_to((x1, m.get_y(), 0)),
                run_time=run_time,
                rate_func=linear,
            )

        self.voice("dgram_1")
        self.play(FadeIn(br), FadeIn(srv), run_time=0.8)
        self.cue("datagrams")
        title = T("datagrams", 44, YELLOW).move_to((0, 3.0, 0))
        self.play(Write(title), run_time=0.6)
        self.cue("one small message")
        d = [sq(str(i), YELLOW, 0.4).move_to((4.6, y, 0)) for i in range(1, 6)]
        self.play(FadeIn(d[0]), FadeIn(arrived), run_time=0.2)
        fly(d[0], -4.3, 0.9)
        self.play(d[0].animate.move_to(slots[0]), FadeIn(d[1]), run_time=0.3)
        fly(d[1], -4.3, 0.8)
        self.play(d[1].animate.move_to(slots[1]), run_time=0.3)
        items = (
            VGroup(
                *[
                    T(s, 30, GREY_B)
                    for s in ("never sent again", "any order", "may not arrive")
                ]
            )
            .arrange(RIGHT, buff=1.2)
            .move_to((0, -2.4, 0))
        )
        self.cue("never sent again")
        self.play(FadeIn(items[0]), FadeIn(d[2]), run_time=0.3)
        fly(d[2], 0.4, 0.6)
        self.play(d[2].animate.set_color(RED), run_time=0.2)
        self.play(d[2].animate.shift(DOWN * 0.7).set_opacity(0), run_time=0.4)
        self.cue("arrive out of order")
        d[3].move_to((3.6, y + 0.18, 0))
        d[4].move_to((4.6, y - 0.18, 0))
        self.play(FadeIn(items[1]), FadeIn(d[3]), FadeIn(d[4]), run_time=0.2)
        self.play(
            d[3].animate.move_to((-1.0, y + 0.18, 0)),
            d[4].animate.move_to((-2.6, y - 0.18, 0)),
            run_time=0.8,
            rate_func=linear,
        )
        self.play(
            d[4].animate.move_to(slots[2]), d[3].animate.move_to(slots[3]), run_time=0.5
        )
        self.cue("not at all")
        miss = VGroup(
            DashedVMobject(Square(0.4).set_stroke(RED, 2), num_dashes=12),
            T("3", 20, RED),
        ).move_to(slots[3] + RIGHT * 0.52)
        self.play(FadeIn(items[2]), FadeIn(miss), run_time=0.5)
        self.finish()

        self._game_again()
        self._limits()
        self.fade_all()

    def _game_again(self) -> None:
        self.voice("dgram_2")
        self.fade_all(run_time=0.5)
        win = window(6.2, 3.6, "https://game.example").move_to((0, 1.3, 0))
        pts = [
            win[0].get_center()
            + np.array([-2.3 + 0.66 * k, -0.3 + 0.6 * np.sin(k * 0.9), 0])
            for k in range(8)
        ]
        player = Dot(pts[0], radius=0.15, color=RED)
        xs = [-4.55 + 1.3 * k for k in range(8)]
        axis = Arrow(
            (-5.4, -2.45, 0), (5.6, -2.45, 0), buff=0, stroke_width=3, color=GREY_B
        )
        axis_l = T("time", 22, GREY_B).next_to(axis.get_end(), DOWN, buff=0.12)
        upd = [
            sq(str(k + 1), YELLOW, 0.4).move_to((x, -1.95, 0)) for k, x in enumerate(xs)
        ]
        trail = VGroup()

        def arrive(k: int, t: float = 0.3) -> None:
            dot = Dot(pts[k], radius=0.05, color=GREY_B)
            trail.add(dot)
            self.play(
                FadeIn(upd[k], shift=DOWN * 0.3),
                player.animate.move_to(pts[k]),
                FadeIn(dot),
                run_time=t,
            )

        self.cue("look at the game")
        self.play(
            FadeIn(win), FadeIn(player), Create(axis), FadeIn(axis_l), run_time=0.6
        )
        for k in range(3):
            arrive(k)
        self.cue("Position four is lost")
        lost = cross(s=0.3).move_to((xs[3], -1.95, 0))
        self.play(Create(lost), run_time=0.4)
        self.cue("position five arrives")
        arrive(4, 0.5)
        self.cue("seventeen milliseconds")
        br_ = Brace(VGroup(lost, upd[4]), DOWN, buff=0.35, color=GREY_B)
        ms = T("17 ms later", 24, GREY_B).next_to(br_, DOWN, buff=0.1)
        self.play(GrowFromCenter(br_), FadeIn(ms), run_time=0.5)
        self.cue("replaces it")
        for k in range(5, 8):
            arrive(k, 0.35)
        self.cue("never freezes")
        ok = (
            VGroup(tick(), T("no freeze", 30, GREEN))
            .arrange(RIGHT, buff=0.25)
            .next_to(win, RIGHT, buff=0.3)
        )
        self.play(FadeIn(ok), run_time=0.5)
        self.finish()

    def _limits(self) -> None:
        self.voice("dgram_3")
        self.fade_all(run_time=0.5)
        title = T("two limits", 40).move_to((0, 3.2, 0))
        self.play(FadeIn(title), run_time=0.5)
        self.cue("single packet")
        pkt = (
            Rectangle(width=2.8, height=0.8)
            .set_stroke(GREY_B, 2)
            .move_to((-3.6, 1.5, 0))
        )
        pkt_l = T("one packet", 24, GREY_B).next_to(pkt, UP, buff=0.12)
        body = Rectangle(
            width=2.5, height=0.55, stroke_width=0, fill_color=YELLOW, fill_opacity=0.7
        ).move_to(pkt)
        self.play(Create(pkt), FadeIn(pkt_l), run_time=0.5)
        self.play(GrowFromEdge(body, LEFT), run_time=0.5)
        self.cue("about one kilobyte")
        kb = T("about 1 KB", 26, YELLOW).next_to(pkt, DOWN, buff=0.15)
        self.play(FadeIn(kb), run_time=0.4)
        self.cue("large data")
        big = VGroup(
            Rectangle(
                width=4.2,
                height=0.9,
                stroke_color=BLUE_C,
                fill_color=BLUE_C,
                fill_opacity=0.35,
            ),
            T("map: 5 MB", 26, BLUE_B),
        )
        big[1].move_to(big[0])
        big.move_to((-3.6, -0.6, 0))
        st = tube(-6.0, -1.2, -2.3, 0.44, GREY_B)
        st_l = T("stream", 24, BLUE_B).next_to(st, UP, buff=0.12).align_to(st, LEFT)
        chunks = (
            VGroup(
                *[
                    Square(0.28, stroke_width=0, fill_color=BLUE_C, fill_opacity=1)
                    for _ in range(10)
                ]
            )
            .arrange(RIGHT, buff=0.18)
            .move_to(st)
        )
        self.play(FadeIn(big, shift=DOWN * 0.2), Create(st), FadeIn(st_l), run_time=0.6)
        self.play(ReplacementTransform(big, chunks), run_time=0.8)
        self.cue("controls congestion")
        top = (
            VMobject()
            .set_points_as_corners([(0.8, 2.0, 0), (3.8, 1.3, 0), (6.6, 1.3, 0)])
            .set_stroke(GREY_B, 2)
        )
        bot = (
            VMobject()
            .set_points_as_corners([(0.8, -0.2, 0), (3.8, 0.5, 0), (6.6, 0.5, 0)])
            .set_stroke(GREY_B, 2)
        )
        net = T("what the network can carry", 22, GREY_B).move_to((4.95, 1.75, 0))
        self.play(Create(top), Create(bot), FadeIn(net), run_time=0.7)
        self.cue("too fast")
        burst = VGroup(
            *[
                Square(0.26, stroke_width=0, fill_color=YELLOW, fill_opacity=1).move_to(
                    (1.2 + 0.36 * (k % 4), 0.4 + 0.42 * (k // 4) + 0.2, 0)
                )
                for k in range(8)
            ]
        )
        self.play(
            LaggedStart(*[FadeIn(b, shift=RIGHT * 0.3) for b in burst], lag_ratio=0.08),
            run_time=0.6,
        )
        self.cue("drops datagrams")
        keep, gone = burst[::2], burst[1::2]
        self.play(
            *[b.animate.move_to((4.2 + 0.55 * i, 0.9, 0)) for i, b in enumerate(keep)],
            *[b.animate.set_fill(GREY_D).shift(DOWN * 1.4) for b in gone],
            run_time=0.9,
        )
        dropped = T("dropped", 24, RED).next_to(gone, DOWN, buff=0.15)
        self.play(
            FadeIn(dropped),
            *[Create(cross(s=0.18).move_to(b)) for b in gone],
            run_time=0.4,
        )
        self.cue("flooding")
        self.play(*[b.animate.shift(RIGHT * 0.6) for b in keep], run_time=0.6)
        self.finish()


CODE: Final = [
    ('const wt = new WebTransport("https://game.example/play");', 2.5),
    ("await wt.ready;", 2.0),
    ("const dg = wt.datagrams.writable.getWriter();", 1.1),
    ("dg.write(position);", 0.6),
    ("const chat = await wt.createBidirectionalStream();", -0.3),
    ("chat.writable.getWriter().write(message);", -0.8),
    ("const files = wt.incomingUnidirectionalStreams.getReader();", -1.7),
]


class Code(Narrated):
    """The JavaScript API line by line, then backpressure from the Streams API."""

    @override
    def construct(self) -> None:
        lines = VGroup(
            *[
                M(s, 24, GREY_D).move_to((-6.3, y, 0), aligned_edge=LEFT)
                for s, y in CODE
            ]
        )
        strs = [s for s, _ in CODE]
        js = T("JavaScript", 28, GREY_B).move_to((-6.3, 3.3, 0), aligned_edge=LEFT)

        def note(i: int, s: str, color: ParsableManimColor) -> Text:
            return M(s, 24, color).next_to(lines[i], RIGHT, buff=0.7)

        self.voice("code_1")
        self.play(
            FadeIn(js),
            LaggedStart(*[FadeIn(ln) for ln in lines], lag_ratio=0.08),
            run_time=0.8,
        )
        self.cue("WebTransport object")
        self.play(lit(lines[0], strs[0], "WebTransport"), run_time=0.5)
        self.cue("H-T-T-P-S address")
        line0 = lines[0].copy()
        part(line0, strs[0], '"https://game.example/play"').set_color(GREEN)
        self.play(Transform(lines[0], line0), run_time=0.5)
        self.cue("wait until")
        self.play(lit(lines[1], strs[1], "await wt.ready"), run_time=0.5)
        self.cue("whole handshake")
        self.play(
            FadeIn(note(1, "// QUIC + TLS + CONNECT", TEAL), shift=LEFT * 0.2),
            run_time=0.6,
        )
        self.finish()

        self.voice("code_2")
        self.cue("writer for the datagrams")
        self.play(lit(lines[2], strs[2], "datagrams", YELLOW), run_time=0.5)
        self.cue("a few bytes")
        self.play(
            lit(lines[3], strs[3], "write", YELLOW),
            FadeIn(note(3, "// may be lost", YELLOW), shift=LEFT * 0.2),
            run_time=0.6,
        )
        self.cue("For chat")
        self.play(
            lit(lines[4], strs[4], "createBidirectionalStream", GREEN), run_time=0.5
        )
        self.cue("write to it")
        self.play(
            lit(lines[5], strs[5], "write", GREEN),
            FadeIn(note(5, "// reliable, in order", GREEN), shift=LEFT * 0.2),
            run_time=0.6,
        )
        self.cue("server pushes")
        self.play(
            lit(lines[6], strs[6], "incomingUnidirectionalStreams", PURPLE_B),
            run_time=0.6,
        )
        self.finish()

        self._backpressure()
        self.fade_all()

    def _backpressure(self) -> None:
        self.voice("code_3")
        self.fade_all(run_time=0.5)
        self.cue("Streams A-P-I")
        title = T("Streams API", 40).move_to((0, 3.1, 0))
        sub_ = M("WritableStream   ReadableStream", 24, GREY_B).next_to(
            title, DOWN, buff=0.2
        )
        you = box("your code", 2.6, 1.0, BLUE, 28).move_to((-5.0, 0.2, 0))
        slots = (
            VGroup(*[Square(0.5).set_stroke(GREY_B, 2) for _ in range(4)])
            .arrange(RIGHT, buff=0.08)
            .move_to((-1.6, 0.2, 0))
        )
        q_l = T("queue", 22, GREY_B).next_to(slots, DOWN, buff=0.15)
        net = tube(0.3, 3.9, 0.2, 0.3)
        net_l = T("network", 22, GREY_B).next_to(net, DOWN, buff=0.15)
        srv = server().move_to((5.4, 0.2, 0))
        self.play(
            Write(title),
            FadeIn(sub_),
            FadeIn(you),
            FadeIn(slots),
            FadeIn(q_l),
            Create(net),
            FadeIn(net_l),
            FadeIn(srv),
            run_time=1.0,
        )
        self.cue("backpressure")
        bp = T("backpressure, built in", 30, YELLOW).move_to((0, 1.5, 0))
        self.play(FadeIn(bp), run_time=0.5)
        self.cue("cannot keep up")
        chunks = [
            Square(0.36, stroke_width=0, fill_color=BLUE_C, fill_opacity=1).move_to(you)
            for _ in range(5)
        ]
        for k in range(4):
            self.add(chunks[k])
            self.play(chunks[k].animate.move_to(slots[3 - k]), run_time=0.3)
        self.play(
            chunks[0].animate.move_to((2.1, 0.2, 0)), run_time=0.6, rate_func=linear
        )
        self.cue("told to pause")
        pause = VGroup(
            *[
                Rectangle(
                    width=0.12,
                    height=0.45,
                    stroke_width=0,
                    fill_color=YELLOW,
                    fill_opacity=1,
                )
                for _ in range(2)
            ]
        ).arrange(RIGHT, buff=0.12)
        pause.next_to(you, UP, buff=0.2)
        aw = M("await writer.ready", 22, YELLOW).next_to(you, DOWN, buff=0.25)
        self.play(FadeIn(pause), FadeIn(aw), run_time=0.5)
        self.cue("piling data")
        pile = VGroup(
            *[
                Square(0.3, stroke_width=0, fill_color=GREY_D, fill_opacity=1)
                for _ in range(6)
            ]
        )
        for i, (r, c) in enumerate(
            [(0, 0), (0, 1), (0, 2), (1, 0.5), (1, 1.5), (2, 1)]
        ):
            pile[i].move_to((-2.2 + 0.34 * c, -2.0 + 0.34 * r, 0))
        mem = T("memory", 22, GREY_B).next_to(pile, DOWN, buff=0.15)
        no = cross(s=0.6).move_to(pile)
        self.play(FadeIn(pile), FadeIn(mem), run_time=0.4)
        self.play(Create(no), run_time=0.4)
        self.finish()


def wall(y0: float, y1: float, x: float = 0.0, w: float = 0.7) -> VGroup:
    """Return a brick firewall of width w from y0 up to y1."""
    r = Rectangle(
        width=w, height=y1 - y0, stroke_color=RED_E, fill_color=RED_E, fill_opacity=0.8
    ).move_to((x, (y0 + y1) / 2, 0))
    rows = VGroup(
        *[
            Line((x - w / 2, y, 0), (x + w / 2, y, 0))
            for y in np.arange(y0 + 0.35, y1, 0.35)
        ]
    ).set_stroke(GREY_E, 2)
    return VGroup(r, rows)


class Tradeoffs(Narrated):
    """The costs: blocked UDP, servers that must support it, no browser to browser."""

    @override
    def construct(self) -> None:
        y = 0.6
        br = browser(2.2, 1.5).move_to((-5.6, y, 0))
        srv = server().move_to((5.6, y, 0))
        title = T("the costs", 40).move_to((0, 3.3, 0))

        self.voice("trade_1")
        self.play(FadeIn(title), FadeIn(br), FadeIn(srv), run_time=0.7)
        self.cue("block U-D-P")
        fw = VGroup(wall(-0.55, 2.3), wall(-2.5, -1.45))
        fw_l = T("company or hotel network", 24, GREY_B).move_to((0, 2.6, 0))
        self.play(FadeIn(fw), FadeIn(fw_l), run_time=0.6)
        self.cue("simply fails")
        u = packet("UDP", YELLOW).move_to((-4.0, y, 0))
        self.play(FadeIn(u), run_time=0.2)
        self.play(u.animate.move_to((-0.8, y, 0)), run_time=0.8, rate_func=rush_into)
        no = cross(s=0.4).next_to(u, UP, buff=0.15)
        self.play(u.animate.set_color(RED), Create(no), run_time=0.4)
        self.cue("WebSocket as a fallback")
        path = (
            VMobject()
            .set_points_as_corners(
                [(-5.0, y - 0.8, 0), (-5.0, -1.0, 0), (5.0, -1.0, 0), (5.0, y - 0.6, 0)]
            )
            .set_stroke(GREEN, 4)
        )
        path_l = T("WebSocket over TCP: the fallback", 22, GREEN).move_to(
            (-3.0, -1.4, 0)
        )
        self.play(Create(path), FadeIn(path_l), run_time=0.9)
        self.finish()

        self.voice("trade_2")
        self.play(
            *[FadeOut(m) for m in (fw, fw_l, u, no, path, path_l)],
            br.animate.move_to((-5.6, 1.4, 0)),
            srv.animate.move_to((5.6, 1.4, 0)),
            run_time=0.6,
        )
        self.cue("load balancer")
        lb = box("load balancer", 3.0, 0.9, GREY_B, 26).move_to((0, 1.4, 0))
        wires = VGroup(
            Line((-4.5, 1.4, 0), lb.get_left()), Line(lb.get_right(), (4.85, 1.4, 0))
        ).set_stroke(GREY_B, 2)
        self.play(FadeIn(lb), Create(wires), run_time=0.6)
        self.cue("must speak")

        def need() -> VGroup:
            t = M("HTTP/3 + WebTransport", 20, YELLOW)
            return VGroup(
                SurroundingRectangle(
                    t, buff=0.1, corner_radius=0.06, color=YELLOW, stroke_width=2
                ),
                t,
            )

        n1, n2 = (
            need().next_to(lb, DOWN, buff=0.25),
            need().next_to(srv, DOWN, buff=0.25),
        )
        n2.shift(LEFT * max(0, n2.get_right()[0] - 6.8))
        self.play(FadeIn(n1, shift=UP * 0.2), FadeIn(n2, shift=UP * 0.2), run_time=0.6)
        self.cue("always connects")
        self.play(Indicate(VGroup(br, srv), color=BLUE_B), run_time=0.8)
        self.cue("two browsers")
        a, b = (
            browser(2.0, 1.3).move_to((-3.4, -1.9, 0)),
            browser(2.0, 1.3).move_to((3.4, -1.9, 0)),
        )
        link = DashedLine(
            a.get_right() + RIGHT * 0.1, b.get_left() + LEFT * 0.1, color=GREY_B
        )
        wt_no = (
            VGroup(cross(s=0.3), T("WebTransport", 24, RED))
            .arrange(RIGHT, buff=0.2)
            .next_to(link, UP, buff=0.2)
        )
        self.play(FadeIn(a), FadeIn(b), Create(link), run_time=0.6)
        self.play(FadeIn(wt_no), run_time=0.4)
        self.cue("Web-R-T-C")
        rtc = (
            VGroup(tick(), T("WebRTC", 28, GREEN))
            .arrange(RIGHT, buff=0.2)
            .next_to(link, DOWN, buff=0.2)
        )
        self.play(FadeIn(rtc), link.animate.set_color(GREEN), run_time=0.5)
        self.finish()
        self.fade_all()


class Outro(Flowing):
    """The game again: datagrams and streams share one encrypted session."""

    @override
    def construct(self) -> None:
        br, srv, frame, flabel = session_frame()
        dg_phase, dg = flow((4.0, 0.9, 0), (-3.8, 0.9, 0), 7, YELLOW, 0.22)
        dg_l = T("positions: datagrams", 22, YELLOW).move_to(
            (-4.0, 1.32, 0), aligned_edge=LEFT
        )
        chat = lane("chat: a stream", -0.3, GREEN)
        mapd = lane("map download: a stream", -1.5, BLUE_C)
        all_ = [dg_phase, chat.phase, mapd.phase]

        self.voice("out_1")
        self.play(FadeIn(br), FadeIn(srv), Create(frame), FadeIn(flabel), run_time=0.8)
        self.cue("as datagrams")
        self.add(dg)
        self.go([dg_phase], 1.0, FadeIn(dg_l))
        self.cue("a lost one")
        self.drop(middle(dg_phase, dg))
        self.go([dg_phase], 3.4)
        self.cue("own streams")
        self.add(chat.squares, mapd.squares)
        self.go(
            all_,
            1.0,
            *[FadeIn(m) for ln in (chat, mapd) for m in (ln.tube, ln.label)],
        )
        self.cue("neither waits")
        self.go(all_, 1.4)
        self.finish()

        self.voice("out_2")
        self.go(all_, 1.6)
        self.cue("encrypted connection")
        lk = lock(s=0.7).next_to(flabel, LEFT, buff=0.25)
        self.go(all_, 0.6, FadeIn(lk), Indicate(frame, color=YELLOW, scale_factor=1.02))
        self.cue("fewer round trips")
        two = T("ready in 2 round trips, not 3", 26, GREEN).move_to((0.1, -2.65, 0))
        self.go(all_, 0.8, FadeIn(two))
        self.cue("That is WebTransport")
        self.fade_all(run_time=0.5)
        title = T("WebTransport", 80, BLUE_B).shift(UP * 0.5)
        self.play(Write(title), run_time=1.0)
        self.cue("message by message")
        last = T("you decide what is worth waiting for", 34, YELLOW).next_to(
            title, DOWN, buff=0.6
        )
        self.play(FadeIn(last, shift=UP * 0.2), run_time=0.8)
        self.finish(pad=1.0)
        self.fade_all(run_time=1.0)
