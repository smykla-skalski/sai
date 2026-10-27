"""OpenID Connect, 3b1b style. Narration is in script.py.

build.py renders the SCENES in order and stitches them. Read the scene you need as a
recipe.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import base64
import json
import sys
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Final

import numpy as np

# Manim does not put the project folder on sys.path.
sys.path.insert(0, str(Path(__file__).parent))
from explainer import (
    M,
    Narrated,
    T,
    box,
    cross,
    fade_to,
    lit,
    packet,
    page,
    part,
    person,
    sup,
    tick,
    window,
)
from manim import (
    BLACK,
    BLUE,
    BLUE_B,
    BLUE_D,
    BLUE_E,
    DL,
    DOWN,
    DR,
    GOLD,
    GREEN,
    GREY_A,
    GREY_B,
    GREY_C,
    GREY_D,
    LEFT,
    ORANGE,
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
    Arrow,
    Circle,
    Circumscribe,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    FadeOut,
    GrowArrow,
    Indicate,
    LaggedStart,
    Line,
    MoveToTarget,
    ParametricFunction,
    Polygon,
    Rectangle,
    ReplacementTransform,
    RoundedRectangle,
    Square,
    SurroundingRectangle,
    Transform,
    VGroup,
    Write,
)
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterable

    from manim import Animation, Mobject, ParsableManimColor, Text, VMobject
    from manim.typing import Point3DLike

SCENES: Final = [
    "Hook",
    "Trust",
    "OAuth",
    "Flow",
    "Token",
    "Signature",
    "Checks",
    "Pkce",
    "Outro",
]
APP_POS: Final = (-4.6, 2.6, 0)
IDP_POS: Final = (4.6, 2.6, 0)
BROWSER_POS: Final = (0, 0.5, 0)


def key_icon(color: ParsableManimColor = GOLD, s: float = 1.0) -> VGroup:
    """Return a key: a ring, a shaft and two teeth."""
    ring = Circle(0.17).set_stroke(color, 5)
    shaft = Line((0.17, 0, 0), (0.8, 0, 0)).set_stroke(color, 5)
    teeth = VGroup(*[Line((x, 0, 0), (x, -0.16, 0)) for x in (0.6, 0.76)])
    teeth.set_stroke(color, 5)
    return VGroup(ring, shaft, teeth).scale(s)


def signin_button(size: float = 30) -> VGroup:
    """Return the "Sign in with Google" button."""
    t = T("Sign in with Google", size)
    r = RoundedRectangle(
        corner_radius=0.2, width=t.width + 0.7, height=t.height + 0.45
    ).set_stroke(WHITE, 2)
    return VGroup(r, t.move_to(r))


def greeting(size: float = 48) -> VGroup:
    """Return an avatar and "Hello, Ada!"."""
    c = Circle(0.45).set_fill(BLUE_D, 1).set_stroke(BLUE_B, 2)
    avatar = VGroup(c, T("A", 36).move_to(c))
    return VGroup(avatar, T("Hello, Ada!", size, YELLOW)).arrange(RIGHT, buff=0.4)


def pointer() -> Polygon:
    """Return a mouse pointer: white with a black outline."""
    arrow = Polygon(
        (0, 0, 0),
        (0, -0.45, 0),
        (0.12, -0.34, 0),
        (0.21, -0.53, 0),
        (0.29, -0.49, 0),
        (0.2, -0.31, 0),
        (0.35, -0.31, 0),
    )
    return arrow.set_fill(WHITE, 1).set_stroke(BLACK, 1.5)


def card(
    label: str,
    color: ParsableManimColor,
    w: float = 1.9,
    h: float = 1.1,
    size: float = 24,
) -> VGroup:
    """Return a tinted card with its label in the upper part."""
    r = RoundedRectangle(
        corner_radius=0.12,
        width=w,
        height=h,
        stroke_color=color,
        fill_color=color,
        fill_opacity=0.2,
    )
    return VGroup(r, T(label, size, color).move_to(r).shift(UP * h * 0.15))


def keycard() -> VGroup:
    """Return the access token as a hotel key card with a magnetic strip."""
    c = card("access token", GOLD)
    strip = Rectangle(
        width=1.9, height=0.16, stroke_width=0, fill_color=GOLD, fill_opacity=0.7
    )
    c.add(strip.move_to(c[0]).shift(DOWN * 0.28))
    return c


def idtoken() -> VGroup:
    """Return the ID token as a card with a signature squiggle."""
    c = card("ID token", BLUE_B)
    squiggle = ParametricFunction(
        lambda t: (t, 0.07 * np.sin(14 * t) * (1 - abs(t)), 0), t_range=(-0.55, 0.55)
    )
    c.add(squiggle.set_stroke(BLUE_B, 2).move_to(c[0]).shift(DOWN * 0.27))
    return c


def small_token(text: str, color: ParsableManimColor = BLUE_B) -> VGroup:
    """Return a token as monospace text on an opaque plate."""
    t = M(text, 18, color)
    plate = SurroundingRectangle(
        t,
        buff=0.12,
        corner_radius=0.08,
        color=color,
        fill_color=BLACK,
        fill_opacity=1,
        stroke_width=2,
    )
    return VGroup(plate, t)


def passport() -> VGroup:
    """Return a passport: a navy booklet with a gold seal."""
    r = RoundedRectangle(
        corner_radius=0.06,
        width=0.8,
        height=1.1,
        stroke_color=GOLD,
        fill_color=BLUE_E,
        fill_opacity=1,
    )
    seal = Circle(0.17).set_stroke(GOLD, 2).move_to(r).shift(UP * 0.12)
    return VGroup(r, seal, T("PASSPORT", 11, GOLD).move_to(r).shift(DOWN * 0.3))


def officer_cap() -> Polygon:
    """Return the border officer's cap."""
    cap = Polygon((-0.3, 0, 0), (0.3, 0, 0), (0.22, 0.16, 0), (-0.22, 0.16, 0))
    return cap.set_fill(GREY_D, 1).set_stroke(GREY_B, 2)


def building(color: ParsableManimColor = GREY_B) -> VGroup:
    """Return a government building: a roof, five columns and a base."""
    roof = Polygon((-1.1, 0, 0), (1.1, 0, 0), (0, 0.55, 0)).set_stroke(color, 3)
    cols = VGroup(
        *[Line((x, -0.08, 0), (x, -0.8, 0)) for x in np.linspace(-0.8, 0.8, 5)]
    ).set_stroke(color, 5)
    base = Rectangle(width=2.2, height=0.14).set_stroke(color, 3).move_to((0, -0.88, 0))
    return VGroup(roof, cols, base)


def door(name: str) -> VGroup:
    """Return a door with a knob and its name below."""
    r = Rectangle(width=1.1, height=1.8).set_stroke(GREY_B, 2)
    knob = Dot(r.get_right() + LEFT * 0.2, radius=0.05, color=GREY_B)
    return VGroup(r, knob, T(name, 24, GREY_B).next_to(r, DOWN, buff=0.15))


def phone(color: ParsableManimColor = GREY_B) -> VGroup:
    """Return a phone outline with a home bar."""
    body = RoundedRectangle(corner_radius=0.18, width=1.2, height=2.1)
    body.set_stroke(color, 3)
    bar = Line(LEFT * 0.15, RIGHT * 0.15).set_stroke(color, 3)
    return VGroup(body, bar.move_to(body.get_bottom() + UP * 0.17))


def slide(mob: Mobject, point: Point3DLike) -> MoveToTarget:
    """Return mob.animate.move_to(point) as an Animation, which LaggedStart needs."""
    mob.generate_target().move_to(point)
    return MoveToTarget(mob)


class Hook(Narrated):
    """Sign in with one click, then ask how the site knows it is you."""

    @override
    def construct(self) -> None:
        win = window(8.6, 5.2, "https://news.example").shift(DOWN * 0.1)
        mid = win[0].get_center() + DOWN * 0.2
        head = T("Daily News", 44).move_to(mid + UP * 1.2)
        btn = signin_button().move_to(mid + DOWN * 0.3)
        cursor = pointer().move_to(mid + RIGHT * 3 + DOWN * 1.6)

        self.voice("hook_1")
        self.play(FadeIn(win), FadeIn(head), FadeIn(btn), FadeIn(cursor), run_time=0.6)
        self.play(
            cursor.animate.move_to(
                btn.get_center() + RIGHT * 0.6 + DOWN * 0.1, aligned_edge=UL
            ),
            run_time=0.7,
        )
        self.play(Indicate(btn, color=BLUE_B, scale_factor=0.94), run_time=0.5)
        self.cue("A second later")
        greet = greeting().move_to(mid + UP * 0.3)
        self.play(
            FadeOut(head),
            FadeOut(btn),
            FadeOut(cursor),
            FadeIn(greet, shift=UP * 0.2),
            run_time=0.8,
        )
        self.cue("never typed")
        field = VGroup(
            T("password", 26, GREY_B),
            Rectangle(width=3.0, height=0.5).set_stroke(GREY_B, 2),
        ).arrange(RIGHT, buff=0.3)
        field.move_to(mid + DOWN * 1.2)
        no = cross(s=0.5).move_to(field[1])
        self.play(FadeIn(field), run_time=0.5)
        self.play(Create(no), run_time=0.4)
        self.finish()

        self.voice("hook_2")
        q = T("How does the site know it is really you?", 40, YELLOW)
        q.to_edge(UP, buff=0.35)
        site = VGroup(win, greet, field, no)
        self.play(site.animate.scale(0.62).shift(DOWN * 0.55), Write(q), run_time=1.2)
        self.cue("Open I-D Connect")
        s = "OpenID Connect"
        title = T(s, 80, BLUE_B).shift(UP * 0.4)
        self.play(FadeOut(site), FadeOut(q), Write(title), run_time=1.2)
        self.cue("O-I-D-C")
        oidc = T("OIDC", 64, YELLOW).next_to(title, DOWN, buff=0.8)
        letters = [part(title, s, c) for c in "OIDC"]
        self.play(
            *[
                ReplacementTransform(letter.copy(), oidc[i])
                for i, letter in enumerate(letters)
            ],
            *[letter.animate.set_color(YELLOW) for letter in letters],
            run_time=1.2,
        )
        self.finish()
        self.fade_all()


class Trust(Narrated):
    """The passport analogy: trust a document because you trust its issuer."""

    @override
    def construct(self) -> None:
        you = person(BLUE_B, 1.4).move_to((-4.6, -1.4, 0))
        you_l = T("you", 28, BLUE_B).next_to(you, DOWN, buff=0.2)
        off = person(GREY_B, 1.4).move_to((4.6, -1.4, 0))
        cap = officer_cap().move_to(off[0].get_top() + DOWN * 0.02)
        off_l = T("officer", 28).next_to(off, DOWN, buff=0.2)
        border = DashedLine((2.6, 0.0, 0), (2.6, -3.0, 0), color=GREY_C)
        border_l = T("border", 22, GREY_C).next_to(border, DOWN, buff=0.1)
        gov = building().move_to((0, 2.2, 0))
        gov_l = T("government", 28).next_to(gov, DOWN, buff=0.2)

        self.voice("trust_1")
        self.play(
            FadeIn(you),
            FadeIn(you_l),
            FadeIn(off),
            FadeIn(cap),
            FadeIn(off_l),
            run_time=1,
        )
        self.cue("border")
        self.play(Create(border), FadeIn(border_l), run_time=0.6)
        self.cue("never met")
        qm = T("?", 56, YELLOW).next_to(cap, UP, buff=0.2)
        self.play(FadeIn(qm, scale=0.5), run_time=0.5)
        self.cue("passport")
        pp = passport().next_to(you, RIGHT, buff=0.2)
        self.play(FadeIn(pp, shift=UP * 0.3), run_time=0.6)
        self.cue("issued by")
        issue = Arrow(
            gov_l.get_bottom() + LEFT * 0.3, pp.get_top(), buff=0.15, color=GOLD
        )
        issue_l = T("issues", 24, GOLD).next_to(issue.get_center(), UL, buff=0.1)
        self.play(FadeIn(gov), FadeIn(gov_l), run_time=0.6)
        self.play(GrowArrow(issue), FadeIn(issue_l), run_time=0.6)
        self.cue("already trust")
        trust = Arrow(
            cap.get_top() + UP * 0.05,
            gov_l.get_right() + RIGHT * 0.15,
            buff=0.1,
            color=GREEN,
        )
        trust_l = T("trusts", 24, GREEN).next_to(trust.get_center(), UR, buff=0.1)
        self.play(FadeOut(qm), GrowArrow(trust), FadeIn(trust_l), run_time=0.8)
        self.cue("genuine")
        self.play(
            pp.animate.next_to(off, LEFT, buff=0.2),
            FadeOut(issue),
            FadeOut(issue_l),
            run_time=0.8,
        )
        ok = tick().next_to(pp, UP, buff=0.15)
        self.play(Create(ok), run_time=0.4)
        self.finish()

        self.voice("trust_2")
        self.cue("the web")
        self.play(FadeOut(border), FadeOut(border_l), run_time=0.5)
        self.cue("site plays")
        site = window(1.6, 1.1).move_to(off)
        site_l = T("website", 28).move_to(off_l)
        self.play(
            ReplacementTransform(VGroup(off, cap), site),
            ReplacementTransform(off_l, site_l),
            run_time=0.8,
        )
        self.cue("identity provider")
        idp_l = T("identity provider", 28, BLUE_B).move_to(gov_l)
        self.play(
            gov.animate.set_color(BLUE_B),
            ReplacementTransform(gov_l, idp_l),
            run_time=0.8,
        )
        self.cue("signed message")
        tok = idtoken().scale(0.75).next_to(site, LEFT, buff=0.2)
        self.play(
            ReplacementTransform(pp, tok),
            ok.animate.next_to(tok, UP, buff=0.15),
            run_time=0.8,
        )
        self.cue("I-D token")
        self.play(Indicate(tok, color=BLUE_B), run_time=0.6)
        self.finish()
        self.fade_all()


class OAuth(Narrated):
    """OAuth 2.0 grants access but not identity, so OpenID Connect adds a layer."""

    @override
    def construct(self) -> None:
        header = T("OpenID Connect", 40, BLUE_B).move_to((0, 3.1, 0))
        base = box("OAuth 2.0", 7.0, 1.0, GREY_B, 36).move_to((0, -2.7, 0))
        q1 = T("Who are you?", 40, GREY_B).move_to((0, 1.7, 0))
        q2 = T("What may this app do for you?", 40, YELLOW).move_to((0, 0.5, 0))

        self.voice("oauth_1")
        self.play(FadeIn(header), run_time=0.6)
        self.cue("older protocol")
        self.play(FadeIn(base, shift=UP * 0.3), run_time=0.8)
        self.cue("Not who")
        self.play(FadeIn(q1), run_time=0.5)
        strike = Line(
            q1.get_left() + LEFT * 0.1,
            q1.get_right() + RIGHT * 0.1,
            color=RED,
            stroke_width=4,
        )
        self.play(Create(strike), run_time=0.4)
        self.cue("what an app")
        self.play(Write(q2), run_time=1.0)
        link = Arrow(base.get_top(), q2.get_bottom(), buff=0.2, color=GREY_B)
        self.play(GrowArrow(link), run_time=0.5)
        self.finish()

        self.voice("oauth_2")
        self.play(
            FadeOut(q1),
            FadeOut(strike),
            FadeOut(link),
            q2.animate.scale(0.6).move_to((0, 2.3, 0)),
            run_time=0.6,
        )
        self.cue("hotel key card")
        kc = keycard().move_to((-4.2, 0.2, 0))
        self.play(FadeIn(kc, shift=RIGHT * 0.3), run_time=0.6)
        self.cue("opens certain doors")
        doors = VGroup(*[door(n) for n in ("photos", "calendar", "files")])
        doors.arrange(RIGHT, buff=0.6).move_to((2.4, 0.0, 0))
        self.play(LaggedStart(*[FadeIn(d) for d in doors], lag_ratio=0.2), run_time=0.7)
        self.play(
            *[d[0].animate.set_fill(GREEN, 0.35).set_stroke(GREEN) for d in doors[:2]],
            run_time=0.5,
        )
        self.cue("nothing about")
        who = T("held by: ?", 30, YELLOW).next_to(kc, UP, buff=0.3)
        self.play(FadeIn(who), run_time=0.5)
        self.cue("security holes")
        bad = T("not proof of identity", 28, RED).next_to(kc, DOWN, buff=0.3)
        self.play(FadeIn(bad), run_time=0.5)
        self.finish()

        self._thin_layer(header, base, kc, (doors, who, bad, q2))
        self.fade_all()

    def _thin_layer(
        self, header: Text, base: VGroup, kc: VGroup, old: Iterable[Mobject]
    ) -> None:
        self.voice("oauth_3")
        self.play(*[FadeOut(m) for m in old], run_time=0.6)
        self.cue("thin layer")
        layer = box("OpenID Connect", 7.0, 0.7, BLUE, 30).next_to(base, UP, buff=0.08)
        self.play(
            ReplacementTransform(header, layer[1]),
            FadeIn(layer[0], shift=DOWN * 0.3),
            run_time=0.9,
        )
        self.cue("scope called")
        scope = M("scope=openid", 36, YELLOW).move_to((0, 2.6, 0))
        self.play(Write(scope), run_time=0.8)
        self.cue("next to the access")
        self.play(kc.animate.move_to((-2.0, 0.4, 0)), run_time=0.6)
        self.cue("I-D token")
        idt = idtoken().move_to((2.0, 0.4, 0))
        self.play(FadeIn(idt, shift=UP * 0.3), run_time=0.6)
        self.cue("who just logged in")
        who = T("who logged in: Ada", 28, BLUE_B).next_to(idt, DOWN, buff=0.3)
        self.play(FadeIn(who), run_time=0.5)
        self.finish()


AUTH_PARAMS: Final = [
    ("client_id", "news-app"),
    ("redirect_uri", "https://news.example/callback"),
    ("scope", "openid profile email"),
    ("response_type", "code"),
    ("state", "af0ifjsldkj"),
    ("nonce", "n-0S6_WzA2Mj"),
]


class Flow(Narrated):
    """The authorization code flow between browser, app and identity provider."""

    @override
    def construct(self) -> None:
        app = box("news app", 2.8, 1.0, GREEN, 32).move_to(APP_POS)
        app_s = T("relying party", 24, GREY_B).next_to(app, DOWN, buff=0.12)
        idp = box("identity provider", 3.4, 1.0, BLUE, 32).move_to(IDP_POS)
        idp_s = T("knows your password", 24, GREY_B).next_to(idp, DOWN, buff=0.12)
        br = window(2.6, 1.4).move_to(BROWSER_POS)
        you = person(BLUE_B, 0.7).move_to(br[0].get_center() + DOWN * 0.2)
        br_s = T("your browser", 24, GREY_B).next_to(br, DOWN, buff=0.12)
        edge_a = Line(app.get_corner(DR), br.get_corner(UL)).set_stroke(GREY_B, 3)
        edge_b = Line(br.get_corner(UR), idp.get_corner(DL)).set_stroke(GREY_B, 3)
        three = T("three parties", 36, GREY_B).move_to((0, -2.4, 0))

        self.voice("flow_1")
        self.play(FadeIn(three), run_time=0.5)
        self.cue("You, in")
        self.play(FadeIn(br), FadeIn(you), FadeIn(br_s), run_time=0.7)
        self.cue("The app")
        self.play(FadeIn(app), run_time=0.6)
        self.cue("relying party")
        self.play(FadeIn(app_s), run_time=0.5)
        self.cue("identity provider")
        self.play(FadeIn(idp), run_time=0.6)
        self.cue("knows your password")
        self.play(FadeIn(idp_s), run_time=0.5)
        self.finish()

        panel = self._request(three, idp, edge_a, edge_b)
        dialog = self._login(panel)
        code, front, clutter = self._front_channel(dialog, br, edge_a, edge_b)
        self._back_channel(
            app, idp, code, clutter, VGroup(br, you, br_s, front, edge_a, edge_b)
        )
        self.fade_all()

    def _request(self, three: Text, idp: VGroup, edge_a: Line, edge_b: Line) -> VGroup:
        self.voice("flow_2")
        self.play(FadeOut(three), run_time=0.4)
        self.cue("sends your browser")
        p = packet("redirect").move_to(edge_a.get_start())
        self.play(Create(edge_a), FadeIn(p), run_time=0.5)
        self.play(p.animate.move_to(edge_a.get_end()), run_time=0.6)
        self.play(Create(edge_b), p.animate.move_to(edge_b.get_end()), run_time=0.8)
        self.play(FadeOut(p), Indicate(idp, color=BLUE_B), run_time=0.4)
        strings = [f"{k}={v}" for k, v in AUTH_PARAMS]
        lines = VGroup(*[M(s, 22, GREY_C) for s in strings])
        lines.arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        url = VGroup(M("login.provider.example/authorize?", 22, GREY_B), lines)
        url.arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        lines.shift(RIGHT * 0.5)
        url.move_to((0, -2.4, 0))
        frame = SurroundingRectangle(url, buff=0.2, corner_radius=0.1, color=GREY_D)
        panel = VGroup(frame, url)
        self.cue("packed into")
        self.play(FadeIn(panel, shift=UP * 0.2), run_time=0.7)
        for word, idx in (
            ("names the app", [0]),
            ("where to return", [1]),
            ("scopes", [2]),
            ("state and nonce", [4, 5]),
        ):
            self.cue(word)
            self.play(
                *[lit(lines[i], strings[i], AUTH_PARAMS[i][0]) for i in idx],
                run_time=0.4,
            )
        self.finish()
        return panel

    def _login(self, panel: VGroup) -> tuple[VGroup, Text, VGroup]:
        self.voice("flow_3")
        dlg = window(7.0, 2.5, "login.provider.example").move_to((0, -2.45, 0))
        body = dlg[0].get_center() + DOWN * 0.2
        pw = VGroup(T("password", 26, GREY_B), M("••••••••", 26))
        pw.arrange(RIGHT, buff=0.4)
        code = VGroup(T("second factor", 26, GREY_B), M("482 913", 26))
        code.arrange(RIGHT, buff=0.4)
        VGroup(pw, code).arrange(DOWN, buff=0.3, aligned_edge=LEFT).move_to(body)
        self.play(FadeOut(panel), FadeIn(dlg), run_time=0.6)
        self.play(FadeIn(pw), run_time=0.4)
        self.cue("second factor")
        self.play(FadeIn(code), run_time=0.4)
        self.cue("asks if you agree")
        ask = T("Share your name and email with news app?", 26)
        ask.move_to(body + UP * 0.3)
        allow_t = T("Allow", 26, GREEN)
        button = RoundedRectangle(corner_radius=0.12, width=1.6, height=0.5)
        allow = VGroup(button.set_stroke(GREEN, 2), allow_t)
        allow_t.move_to(allow[0])
        allow.next_to(ask, DOWN, buff=0.3)
        self.play(FadeOut(pw), FadeOut(code), FadeIn(ask), FadeIn(allow), run_time=0.6)
        self.play(Indicate(allow, color=GREEN), run_time=0.5)
        self.finish()
        return dlg, ask, allow

    def _front_channel(
        self, dialog: Iterable[Mobject], br: VGroup, edge_a: Line, edge_b: Line
    ) -> tuple[VGroup, Text, tuple[Mobject, ...]]:
        self.voice("flow_4")
        self.play(*[FadeOut(m) for m in dialog], run_time=0.4)
        c = packet("code=SplxlOBeZQ").move_to(edge_b.get_end())
        self.play(
            FadeIn(c),
            edge_a.animate.set_stroke(ORANGE),
            edge_b.animate.set_stroke(ORANGE),
            run_time=0.4,
        )
        self.play(c.animate.move_to(edge_b.get_start()), run_time=0.7)
        self.play(c.animate.move_to((-1.6, 1.8, 0)), run_time=0.7)
        self.cue("risky place")
        front = T("front channel", 26, ORANGE).next_to(br, LEFT, buff=0.3)
        self.play(FadeIn(front), run_time=0.5)
        self.cue("history")
        hist = VGroup(page(), T("history", 24, GREY_B)).arrange(DOWN, buff=0.12)
        hist.move_to((-2.6, -2.0, 0))
        logs = VGroup(page(), T("logs", 24, GREY_B)).arrange(DOWN, buff=0.12)
        logs.move_to((2.6, -2.0, 0))
        leak1 = M("code=SplxlOBeZQ", 18, ORANGE).move_to(br)
        leak2 = leak1.copy()
        self.play(FadeIn(hist), FadeIn(logs), run_time=0.4)
        self.play(
            leak1.animate.next_to(hist, DOWN, buff=0.15),
            leak2.animate.next_to(logs, DOWN, buff=0.15),
            run_time=0.8,
        )
        self.cue("worth very little")
        little = T("useless on its own", 24, GREY_B).next_to(c, UP, buff=0.12)
        self.play(FadeIn(little), run_time=0.5)
        self.finish()
        return c, front, (little, hist, logs, leak1, leak2)

    def _back_channel(
        self,
        app: VGroup,
        idp: VGroup,
        code: VGroup,
        clutter: Iterable[Mobject],
        front_side: VGroup,
    ) -> None:
        self.voice("flow_5")
        back = Line(app.get_right(), idp.get_left()).set_stroke(GREEN, 4)
        self.play(*[FadeOut(m) for m in clutter], Create(back), run_time=0.6)
        sec = packet("code + secret", GREEN).move_to(app.get_right() + RIGHT * 1.4)
        self.play(ReplacementTransform(code, sec), run_time=0.5)
        self.play(sec.animate.move_to(idp.get_left() + LEFT * 1.4), run_time=1.0)
        self.cue("for the tokens")
        tk = packet("ID token + access token", BLUE_B)
        tk.move_to(idp.get_left() + LEFT * 2.0)
        self.play(ReplacementTransform(sec, tk), run_time=0.4)
        self.play(tk.animate.move_to(app.get_right() + RIGHT * 2.0), run_time=1.0)
        self.cue("back channel")
        bc = T("back channel", 26, GREEN).move_to((1.4, 2.25, 0))
        self.play(FadeIn(bc), fade_to(front_side), run_time=0.6)
        self.finish()


def b64(data: object) -> str:
    """Return data as compact JSON in unpadded base64url, as a JWT encodes it."""
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


CLAIMS: Final = [
    ("iss", '"https://login.provider.example"', "issuer: who made it"),
    ("sub", '"248289761001"', "subject: a stable ID for you"),
    ("aud", '"news-app"', "audience: the app it is for"),
    ("exp", "1767225600", "expiry: 1 Jan 2026"),
    ("nonce", '"n-0S6_WzA2Mj"', "nonce: from the request"),
    ("name", '"Ada Lovelace"', ""),
    ("email", '"ada@example.com"', ""),
]
# Made up: only the start of the signature is shown.
SIGNATURE: Final = "RIgP_58waM-Dx3"


def payload_json() -> VGroup:
    """Return the decoded payload: one indented code line per claim, in braces."""
    lines = [
        f'"{k}": {v}' + ("," if i < len(CLAIMS) - 1 else "")
        for i, (k, v, _) in enumerate(CLAIMS)
    ]
    body = VGroup(
        M("{", 26, GREY_B), *[M(line, 26, GREY_A) for line in lines], M("}", 26, GREY_B)
    )
    body.arrange(DOWN, aligned_edge=LEFT, buff=0.16)
    for line in body[1:-1]:
        line.shift(RIGHT * 0.5)
    return body.move_to((-2.3, -0.7, 0))


class Token(Narrated):
    """The ID token as a JWT: header, payload and signature, then each claim."""

    @override
    def construct(self) -> None:
        h = b64({"alg": "RS256", "kid": "1e9gdk7"})[:18] + "…"
        p = b64({k: json.loads(v) for k, v, _ in CLAIMS})[:22] + "…"
        s = SIGNATURE + "…"
        jwt = M(f"{h}.{p}.{s}", 26).move_to((0, 0.6, 0))
        segs = [
            jwt[: len(h)],
            jwt[len(h) + 1 : len(h) + 1 + len(p)],
            jwt[len(h) + len(p) + 2 :],
        ]
        dots = [jwt[len(h)], jwt[len(h) + len(p) + 1]]
        title = T("ID token", 48, BLUE_B).move_to((0, 2.6, 0))
        jwt_l = T("a JWT, a JSON Web Token", 28, GREY_B).next_to(title, DOWN, buff=0.2)
        names = [("header", RED_B), ("payload", PURPLE_B), ("signature", TEAL)]
        labels = VGroup(
            *[
                T(n, 28, c).next_to(seg, DOWN, buff=0.35)
                for (n, c), seg in zip(names, segs, strict=True)
            ]
        )

        self.voice("token_1")
        self.play(FadeIn(title), run_time=0.6)
        self.play(Write(jwt), run_time=1.5)
        self.cue("J-W-T")
        self.play(FadeIn(jwt_l), run_time=0.5)
        self.cue("joined by dots")
        self.play(
            *[Indicate(d, color=YELLOW, scale_factor=2.5) for d in dots], run_time=0.8
        )
        for (n, c), seg, lab in zip(names, segs, labels, strict=True):
            self.cue(n)
            self.play(seg.animate.set_color(c), FadeIn(lab), run_time=0.5)
        self.finish()

        self.voice("token_2")
        self.play(
            FadeOut(title),
            FadeOut(jwt_l),
            VGroup(jwt, labels).animate.scale(0.75).move_to((0, 3.0, 0)),
            run_time=0.8,
        )
        self.play(Indicate(segs[1], color=PURPLE_B), run_time=0.6)
        body = payload_json()
        self.play(FadeIn(body, shift=DOWN * 0.3), run_time=0.8)
        shown = self._claim(body, [], "issuer", [0], CLAIMS[0][2])
        shown = self._claim(body, shown, "subject", [1], CLAIMS[1][2])
        shown = self._claim(body, shown, "audience", [2], CLAIMS[2][2])
        self.finish()

        self.voice("token_3")
        shown = self._claim(body, shown, "expiry", [3], CLAIMS[3][2])
        shown = self._claim(body, shown, "nonce", [4], CLAIMS[4][2])
        who = self._claim(body, shown, "name and email", [5, 6], "who you are")[-1]
        self.cue("anyone can type")
        fake = M('"name": "Eve Lovelace",', 26, YELLOW, t2c={"Eve": RED})
        fake.move_to(body[6], aligned_edge=LEFT)
        forged = T("anyone can write this", 26, RED).move_to(who, aligned_edge=LEFT)
        self.play(
            Transform(body[6], fake), ReplacementTransform(who, forged), run_time=0.7
        )
        self.cue("signature")
        self.play(
            Circumscribe(segs[2], color=TEAL),
            Indicate(labels[2], color=TEAL),
            run_time=1.0,
        )
        self.finish()
        self.fade_all()

    def _claim(
        self,
        body: VGroup,
        shown: list[VMobject],
        word: str,
        rows: list[int],
        note: str,
    ) -> list[VMobject]:
        """Light rows and a note at word, dim earlier ones, return what is lit."""
        self.cue(word)
        ys = [body[i + 1].get_y() for i in rows]
        lab = T(note, 26, YELLOW).move_to(
            (2.0, sum(ys) / len(ys), 0), aligned_edge=LEFT
        )
        self.play(
            *[body[i + 1].animate.set_color(YELLOW) for i in rows],
            *[m.animate.set_color(WHITE if m in body else GREY_B) for m in shown],
            FadeIn(lab, shift=LEFT * 0.2),
            run_time=0.5,
        )
        return [*(body[i + 1] for i in rows), lab]


# 617 made-up digits, as many as a 2048-bit RSA modulus has, in rows of 62.
KEY_ROWS: Final = [
    "62601815908301661318609139099603082462819482199351819093786579",
    "75432319487574911862527601895559797114710497465075291703423667",
    "12768426846563212233079244026859952890786666176031372159010928",
    "15901396245957117777412154728038528084148525388853933633875004",
    "74395755131373537990751163726516761222029729975288200182633043",
    "48395486205798682828807290222791805888718033401878017598983478",
    "87838483726167513613412524273167232686563551505877065894811311",
    "44024264628897514026140141931417058649208312402344834782450400",
    "08838737167868433532650201462016849340722470455853043520561748",
    "33801412690604431982965724920868288909310025167800837407188",
]


class Signature(Narrated):
    """Sign and verify with toy RSA numbers, then show why forging is hard."""

    @override
    def construct(self) -> None:
        idp = box("identity provider", 3.4, 1.0, BLUE, 32).move_to((-4.6, 2.8, 0))
        app = box("news app", 2.8, 1.0, GREEN, 32).move_to((4.6, 2.8, 0))
        priv = VGroup(key_icon(RED), T("private key", 24, RED))
        priv.arrange(RIGHT, buff=0.2).next_to(idp, DOWN, buff=0.35)
        pub = VGroup(key_icon(GREEN), T("public key", 24, GREEN))
        pub.arrange(RIGHT, buff=0.2)
        conf = [
            ("issuer", "https://login.provider.example"),
            ("authorization_endpoint", ".../authorize"),
            ("token_endpoint", ".../token"),
            ("jwks_uri", ".../keys"),
        ]
        doc = VGroup(
            M("/.well-known/openid-configuration", 24, YELLOW),
            *[M(f'"{k}": "{v}"', 22, GREY_A) for k, v in conf],
        )
        doc.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        for line in doc[1:]:
            line.shift(RIGHT * 0.4)
        doc.move_to((-0.8, -0.4, 0))

        self.voice("sig_1")
        self.play(FadeIn(idp), run_time=0.5)
        self.cue("private key")
        self.play(FadeIn(priv, shift=UP * 0.2), run_time=0.6)
        self.cue("matching public key")
        pub.next_to(priv, DOWN, buff=0.3)
        self.play(FadeIn(pub), run_time=0.5)
        self.cue("well-known")
        self.play(
            FadeIn(doc, shift=UP * 0.2),
            pub.animate.next_to(doc[-1], RIGHT, buff=0.3),
            run_time=0.9,
        )
        self.cue("downloads")
        self.play(FadeIn(app), run_time=0.5)
        pub2 = pub.copy()
        self.play(pub2.animate.next_to(app, DOWN, buff=0.35), run_time=0.8)
        self.finish()

        pubn, privn, hsh, sign, res = self._sign(doc, pub, pub2, priv)
        chk, ok = self._verify(pubn, privn, hsh)
        hsh2, no, rej = self._tamper(hsh, chk, ok)
        self._forge((hsh2, sign, res, chk, no, rej))
        self.fade_all()

    def _sign(
        self, doc: VGroup, pub: VGroup, pub2: VGroup, priv: VGroup
    ) -> tuple[Text, Text, VGroup, VGroup, VGroup]:
        self.voice("sig_2")
        self.play(FadeOut(doc), FadeOut(pub), run_time=0.5)
        self.cue("thirty-three and three")
        pubn = T("(33, 3)", 40, GREEN).next_to(pub2, DOWN, buff=0.25)
        self.play(FadeIn(pubn), run_time=0.5)
        self.cue("seven")
        privn = T("7", 44, RED).next_to(priv, DOWN, buff=0.25)
        self.play(FadeIn(privn), run_time=0.5)
        self.cue("hashes to four")
        hsh = VGroup(T("hash(payload) =", 38), T("4", 38, YELLOW))
        hsh.arrange(RIGHT, buff=0.2).move_to((0, 0.4, 0))
        self.play(FadeIn(hsh), run_time=0.6)
        self.cue("four to the power")
        sign = VGroup(T("signature =", 38), sup("4", "7", 38), T("mod 33", 38))
        sign.arrange(RIGHT, buff=0.2)
        sign[1][1].set_color(RED)
        res = VGroup(T("= 16384 mod 33 =", 38), T("16", 38, TEAL))
        res.arrange(RIGHT, buff=0.2)
        VGroup(sign, res).arrange(RIGHT, buff=0.2).move_to((0, -0.8, 0))
        self.play(Write(sign), run_time=1.0)
        self.cue("which is sixteen")
        self.play(Write(res), run_time=0.8)
        self.finish()
        return pubn, privn, hsh, sign, res

    def _verify(self, pubn: Text, privn: Text, hsh: VGroup) -> tuple[VGroup, VMobject]:
        self.voice("sig_3")
        self.play(Indicate(pubn, color=GREEN), run_time=0.8)
        self.cue("Sixteen cubed")
        chk = VGroup(
            T("check:", 38, GREY_B),
            T("16³ mod 33 = 4096 mod 33 =", 38, t2c={"16³": TEAL}),
            T("4", 38, YELLOW),
        )
        chk.arrange(RIGHT, buff=0.2).move_to((0, -2.1, 0))
        self.play(Write(chk), run_time=1.2)
        self.cue("equals the hash")
        ok = tick().next_to(chk, RIGHT, buff=0.3)
        self.play(Indicate(hsh[1]), Indicate(chk[2]), Create(ok), run_time=0.8)
        self.cue("holds the seven")
        self.play(Indicate(privn, color=RED, scale_factor=1.5), run_time=0.8)
        self.finish()
        return chk, ok

    def _tamper(
        self, hsh: VGroup, chk: VGroup, ok: VMobject
    ) -> tuple[VGroup, VGroup, Text]:
        self.voice("sig_4")
        self.cue("change one letter")
        hsh2 = VGroup(
            T("hash(edited payload) =", 38, t2c={"edited": RED}), T("5", 38, RED)
        )
        hsh2.arrange(RIGHT, buff=0.2).move_to(hsh)
        self.play(
            ReplacementTransform(hsh[0], hsh2[0]),
            hsh[1].animate.next_to(hsh2[0], RIGHT, buff=0.2),
            run_time=0.7,
        )
        self.cue("say to five")
        self.play(ReplacementTransform(hsh[1], hsh2[1]), run_time=0.5)
        self.cue("still four")
        self.play(Indicate(chk[2], color=YELLOW), run_time=0.6)
        self.cue("check fails")
        no = cross().move_to(ok)
        self.play(ReplacementTransform(ok, no), run_time=0.5)
        self.cue("rejects")
        rej = T("rejected", 32, RED).next_to(no, DOWN, buff=0.2)
        self.play(FadeIn(rej), run_time=0.5)
        self.finish()
        return hsh2, no, rej

    def _forge(self, old: Iterable[Mobject]) -> None:
        self.voice("sig_5")
        self.play(*[FadeOut(m) for m in old], run_time=0.6)
        self.cue("splitting")
        fac = T("33 = 3 \N{MULTIPLICATION SIGN} 11", 48).move_to((0, 0.2, 0))
        self.play(Write(fac), run_time=0.8)
        found = VGroup(T("so the private key is", 34, GREY_B), T("7", 44, RED))
        found.arrange(RIGHT, buff=0.25).next_to(fac, DOWN, buff=0.5)
        self.play(FadeIn(found), run_time=0.6)
        self.cue("Real keys")
        self.fade_all(run_time=0.4)
        wall = VGroup(*[M(row, 20, GREY_B) for row in KEY_ROWS])
        wall.arrange(DOWN, buff=0.1, aligned_edge=LEFT).move_to(DOWN * 0.4)
        cap = T("a real public key: 617 digits", 34, YELLOW)
        cap.next_to(wall, UP, buff=0.4)
        self.play(
            LaggedStart(*[FadeIn(r) for r in wall], lag_ratio=0.15),
            FadeIn(cap),
            run_time=1.5,
        )
        self.finish()


class Checks(Narrated):
    """The checks before an app believes a token, and the attacks they stop."""

    @override
    def construct(self) -> None:
        items = [
            "signature is valid",
            "issuer = the expected provider",
            "expiry is in the future",
            "audience = my client ID",
            "nonce = the one I sent",
        ]
        title = T("Before the app believes the token", 40).to_edge(UP, buff=0.5)
        rows = VGroup(
            *[
                VGroup(Square(0.42).set_stroke(GREY_B, 2), T(s, 32, GREY_B))
                for s in items
            ]
        )
        for row in rows:
            row.arrange(RIGHT, buff=0.35)
        rows.arrange(DOWN, buff=0.4, aligned_edge=LEFT).move_to((0, -0.4, 0))
        ticks = VGroup()

        self.voice("check_1")
        self.play(
            FadeIn(title),
            LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=0.15),
            run_time=1.2,
        )
        for i, word in enumerate(("first check", "issuer", "not expired", "audience")):
            self.cue(word)
            self._tick(rows[i], ticks, run_time=0.5)
        self.finish()

        old = self._audience(title, rows, ticks)
        self._nonce(rows, ticks, old)
        self.fade_all()

    def _tick(
        self, row: VMobject, ticks: VGroup, *also: Animation, run_time: float
    ) -> None:
        t = tick().move_to(row[0])
        ticks.add(t)
        self.play(*also, Create(t), row[1].animate.set_color(WHITE), run_time=run_time)

    def _audience(
        self, title: Text, rows: VGroup, ticks: VGroup
    ) -> tuple[Mobject, ...]:
        self.voice("check_2")
        self.add(ticks)
        checklist = VGroup(rows, ticks)
        self.play(
            FadeOut(title),
            checklist.animate.scale(0.6).to_corner(UL, buff=0.5),
            run_time=0.8,
        )
        self.play(Indicate(rows[3], color=YELLOW), run_time=0.6)
        self.cue("quiz app")
        quiz = box("quiz app", 2.6, 1.0, RED, 32).move_to((-3.4, -0.3, 0))
        users = VGroup(*[person(GREY_B, 0.7) for _ in range(3)])
        users.arrange(RIGHT, buff=0.7).move_to((-3.4, -2.8, 0))
        self.play(FadeIn(quiz), FadeIn(users), run_time=0.7)
        self.cue("collects real")
        toks = VGroup(*[small_token("aud: quiz-app").move_to(u) for u in users])
        pile = quiz.get_right() + RIGHT * 1.4
        self.play(
            LaggedStart(
                *[slide(t, pile + i * (UP + RIGHT) * 0.12) for i, t in enumerate(toks)],
                lag_ratio=0.25,
            ),
            run_time=1.2,
        )
        self.cue("Without the audience")
        bank = box("your bank", 2.6, 1.0, BLUE, 32).move_to((4.6, -0.3, 0))
        expects = M("expects aud: bank-app", 20, BLUE_B).next_to(bank, DOWN, buff=0.2)
        self.play(FadeIn(bank), FadeIn(expects), run_time=0.5)
        self.cue("replay one")
        replay = toks[-1]
        self.play(replay.animate.next_to(bank, LEFT, buff=0.3), run_time=0.7)
        no = cross().next_to(replay, UP, buff=0.15)
        self.play(Create(no), replay[1].animate.set_color(RED), run_time=0.4)
        self.finish()
        return quiz, users, toks, bank, expects, no

    def _nonce(self, rows: VGroup, ticks: VGroup, old: Iterable[Mobject]) -> None:
        self.voice("check_3")
        self.play(*[FadeOut(m) for m in old], run_time=0.5)
        axis = Arrow(
            (-5.8, -1.6, 0), (6.4, -1.6, 0), buff=0, stroke_width=3, color=GREY_B
        )
        axis_l = T("time", 24, GREY_B).next_to(axis.get_end(), DOWN, buff=0.15)
        earlier = Line((-4.6, -1.6, 0), (-1.2, -1.6, 0)).set_stroke(BLUE, 8)
        now = Line((1.6, -1.6, 0), (5.0, -1.6, 0)).set_stroke(YELLOW, 8)
        earlier_l = T("earlier login", 26, BLUE_B).next_to(earlier, DOWN, buff=0.2)
        now_l = T("this login", 26, YELLOW).next_to(now, DOWN, buff=0.2)
        self.play(
            Indicate(rows[4], color=YELLOW),
            FadeIn(VGroup(axis, axis_l, earlier, now, earlier_l, now_l)),
            run_time=0.8,
        )
        self.cue("made it up")
        expected = M("expected nonce: n-0S6", 22, YELLOW).next_to(now, UP, buff=0.35)
        self.play(FadeIn(expected, shift=DOWN * 0.2), run_time=0.5)
        self.cue("copied from")
        old_tok = small_token("nonce: n-71QX").next_to(earlier, UP, buff=0.35)
        self.play(FadeIn(old_tok), run_time=0.4)
        self.play(old_tok.animate.next_to(expected, UP, buff=0.3), run_time=0.8)
        self.cue("wrong nonce")
        no = cross().next_to(old_tok, LEFT, buff=0.3)
        self.play(old_tok[1].animate.set_color(RED), Create(no), run_time=0.5)
        self.cue("rejected")
        rejected = T("rejected", 30, RED).next_to(old_tok, UP, buff=0.25)
        self.play(FadeIn(rejected), run_time=0.4)
        self.cue("state value")
        state = T("state: the same idea for the return trip", 28, GREY_B)
        state.move_to((0, -3.1, 0))
        self._tick(rows[4], ticks, FadeIn(state), run_time=0.6)
        self.finish()


class Pkce(Narrated):
    """PKCE: a hashed verifier makes a stolen code useless to an attacker."""

    @override
    def construct(self) -> None:
        ph = phone().move_to((-3.6, 0.3, 0))
        ph_l = T("phone app", 26, GREY_B).next_to(ph, DOWN, buff=0.2)
        spa = window(2.8, 2.0).move_to((0.0, 0.3, 0))
        spa_l = T("single page app", 26, GREY_B).next_to(spa, DOWN, buff=0.2)
        secrets = VGroup(
            M("secret", 22, GOLD).move_to(ph[0]),
            M("secret", 22, GOLD).move_to(spa[0]).shift(DOWN * 0.2),
        )

        self.voice("pkce_1")
        self.play(FadeIn(ph), FadeIn(ph_l), run_time=0.5)
        self.cue("single page")
        self.play(FadeIn(spa), FadeIn(spa_l), run_time=0.5)
        self.cue("keep a secret")
        self.play(FadeIn(secrets), run_time=0.4)
        read = T("anyone can read it", 28, RED).move_to((4.0, 0.3, 0))
        self.play(secrets.animate.set_color(RED), FadeIn(read), run_time=0.5)
        self.cue("stolen code")
        stolen = VGroup(packet("code", RED), T("stolen", 26, RED))
        stolen.arrange(RIGHT, buff=0.25).move_to((0, -2.4, 0))
        self.play(FadeIn(stolen, shift=UP * 0.2), run_time=0.5)
        self.cue("P-K-C-E")
        self.fade_all(run_time=0.4)
        title = T("PKCE", 64, YELLOW).move_to((0, 3.1, 0))
        long = T("Proof Key for Code Exchange", 28, GREY_B)
        long.next_to(title, DOWN, buff=0.15)
        app = box("news app", 2.8, 1.0, GREEN, 32).move_to((-4.6, 1.1, 0))
        idp = box("identity provider", 3.4, 1.0, BLUE, 32).move_to((4.6, 1.1, 0))
        self.play(Write(title), FadeIn(long), run_time=0.8)
        self.play(FadeIn(app), FadeIn(idp), run_time=0.5)
        self.cue("random verifier")
        ver = M("verifier = dBjftJeZ4CVP…", 24, GOLD).next_to(app, DOWN, buff=0.5)
        self.play(FadeIn(ver, shift=DOWN * 0.2), run_time=0.5)
        self.cue("sends only")
        down = Arrow(
            ver.get_bottom(), ver.get_bottom() + DOWN * 0.9, buff=0.1, color=GREY_B
        )
        down_l = M("SHA-256", 20, GREY_B).next_to(down, RIGHT, buff=0.15)
        chal = M("challenge = E9Melhoa2Ow…", 24, TEAL).next_to(down, DOWN, buff=0.1)
        self.play(GrowArrow(down), FadeIn(down_l), FadeIn(chal), run_time=0.6)
        stored = chal.copy()
        self.play(stored.animate.next_to(idp, DOWN, buff=0.5), run_time=0.8)
        self.finish()

        self._exchange(app, idp, stored)
        self.fade_all()

    def _exchange(self, app: VGroup, idp: VGroup, stored: Text) -> None:
        self.voice("pkce_2")
        pk = packet("code + verifier", GOLD).move_to(app.get_right() + RIGHT * 1.6)
        self.play(FadeIn(pk), run_time=0.4)
        self.play(pk.animate.move_to(idp.get_left() + LEFT * 1.6), run_time=1.0)
        self.cue("hashes it")
        h2 = M("hash(verifier) = E9Melhoa2Ow…", 20, TEAL)
        h2.next_to(stored, DOWN, buff=0.4)
        self.play(FadeIn(h2), run_time=0.6)
        self.cue("compares")
        ok = tick().next_to(h2, DOWN, buff=0.2)
        self.play(Create(ok), run_time=0.4)
        self.cue("An attacker")
        atk = VGroup(person(RED, 0.9), T("attacker", 24, RED))
        atk.arrange(DOWN, buff=0.15).move_to((-2.6, -2.6, 0))
        apk = packet("code", RED).next_to(atk, RIGHT, buff=0.4)
        self.play(FadeIn(atk), FadeIn(apk), run_time=0.5)
        self.cue("never saw")
        self.play(apk.animate.move_to((1.6, -2.6, 0)), run_time=0.7)
        self.cue("useless")
        no = cross().next_to(apk, RIGHT, buff=0.3)
        no_tokens = T("no tokens", 28, RED).next_to(no, RIGHT, buff=0.2)
        self.play(Create(no), FadeIn(no_tokens), run_time=0.5)
        self.finish()


class Outro(Narrated):
    """Identify users by issuer and subject, then recap the whole flow."""

    @override
    def construct(self) -> None:
        self.voice("out_1")
        title = T("Who is this user?", 44).to_edge(UP, buff=0.6)
        self.play(FadeIn(title), run_time=0.6)
        self.cue("issuer and the subject")
        good = M(
            '(iss, sub) = ("https://login.provider.example", "248289761001")',
            22,
            GREEN,
        ).move_to((0.4, 1.4, 0))
        self.play(
            FadeIn(good), Create(tick().next_to(good, LEFT, buff=0.3)), run_time=0.8
        )
        self.cue("never by email")
        bad = M('email = "ada@example.com"', 26, RED).move_to((0.4, 0.1, 0))
        ada = VGroup(person(BLUE_B), T("Ada", 26, BLUE_B))
        ada.arrange(DOWN, buff=0.15).move_to((-2.5, -2.4, 0))
        other = VGroup(person(GREY_B), T("someone else", 26, GREY_B))
        other.arrange(DOWN, buff=0.15).move_to((2.5, -2.4, 0))
        link = Arrow(bad.get_bottom(), ada.get_top(), buff=0.2, color=GREY_B)
        self.play(
            FadeIn(bad),
            Create(cross().next_to(bad, LEFT, buff=0.3)),
            FadeIn(ada),
            FadeIn(other),
            GrowArrow(link),
            run_time=0.8,
        )
        self.cue("move to someone")
        moved = Arrow(bad.get_bottom(), other.get_top(), buff=0.2, color=RED)
        self.play(Transform(link, moved), run_time=0.6)
        self.finish()

        self.voice("out_2")
        self.fade_all(run_time=0.5)
        btn = signin_button().move_to((0, 2.6, 0))
        self.play(FadeIn(btn), run_time=0.5)
        steps = [
            ("redirect", "redirect to\nthe provider", YELLOW),
            ("one-time code", "one-time\ncode", ORANGE),
            ("swap", "back-channel\nswap", GREEN),
            ("signed token", "signed\nID token", BLUE),
        ]
        boxes = VGroup(*[box(label, 2.7, 1.3, color, 26) for _, label, color in steps])
        boxes.arrange(RIGHT, buff=0.55).move_to((0, 0.2, 0))
        arrows = [
            Arrow(a.get_right(), b.get_left(), buff=0.08, color=GREY_B)
            for a, b in pairwise(boxes)
        ]
        for i, (word, _, _) in enumerate(steps):
            self.cue(word)
            self.play(
                FadeIn(boxes[i], shift=RIGHT * 0.2),
                *([GrowArrow(arrows[i - 1])] if i else []),
                run_time=0.5,
            )
        self.cue("checks before")
        self.play(Create(tick(s=0.5).next_to(boxes[3], DOWN, buff=0.3)), run_time=0.4)
        self.cue("That is how")
        self.play(
            FadeIn(greeting().move_to((0, -2.4, 0)), shift=UP * 0.2), run_time=0.7
        )
        self.finish(pad=1.0)
        self.fade_all(run_time=1.0)
