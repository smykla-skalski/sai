#!/usr/bin/env python3
"""Render the plugin directory icon for every plugin.

Each icon is a 1024x1024 PNG: a rounded tile with the plugin family's accent
gradient and a white line glyph for what the plugin does. The PNG goes to
plugins/<name>/.claude-plugin/icon.png, where `claude plugin validate` looks
for it (ICON_MISSING otherwise).

Usage:
    scripts/plugin_icons.py            render every plugin in GLYPHS
    scripts/plugin_icons.py humanize   render one plugin
    scripts/plugin_icons.py --check    exit 1 if a plugin has no glyph

Needs rsvg-convert (librsvg). Exit codes: 0 ok, 1 missing glyph, 2 usage or
render error.

Copyright 2026 Smykla Skalski, MIT License.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
SIZE: Final[int] = 1024
RENDER_TIMEOUT_SECONDS: Final[int] = 60

# Accent gradients per plugin family: (top-left, bottom-right).
REVIEW: Final[tuple[str, str]] = ("#4F7DF3", "#2747B8")
TEST: Final[tuple[str, str]] = ("#2FBF8F", "#13805E")
GIT: Final[tuple[str, str]] = ("#F59F45", "#C9661A")
WRITING: Final[tuple[str, str]] = ("#A46BF5", "#6B36C4")
COUNCIL: Final[tuple[str, str]] = ("#26B5C7", "#127A8C")
OPS: Final[tuple[str, str]] = ("#EF5F5F", "#B32F3C")
DIGEST: Final[tuple[str, str]] = ("#F2B83B", "#C98410")

DOC: Final[str] = '<path d="M340 250 H600 L700 350 V774 H340 Z M600 250 V350 H700"/>'
BUBBLE: Final[str] = (
    '<path d="M280 300 H744 Q784 300 784 340 V600 Q784 640 744 640 H480'
    ' L360 740 V640 H320 Q280 640 280 600 V340 Q280 300 320 300 Z"/>'
)

GLYPHS: Final[dict[str, tuple[tuple[str, str], str]]] = {
    "adversarial-review": (
        REVIEW,
        (
            '<circle cx="460" cy="460" r="170"/>'
            '<path d="M582 582 L740 740 M460 380 V470"/>'
            '<circle cx="460" cy="548" r="34" class="dot"/>'
        ),
    ),
    "adversarial-test": (
        TEST,
        (
            '<path d="M430 270 V450 L300 690 Q282 744 340 744 H684'
            ' Q742 744 724 690 L594 450 V270"/>'
            '<path d="M390 270 H634 M370 610 H654"/>'
        ),
    ),
    "agent-issues": (
        WRITING,
        (
            '<circle cx="430" cy="430" r="170"/>'
            '<circle cx="430" cy="430" r="52" class="dot"/>'
            '<path d="M600 720 L720 600 L780 660 L660 780 Z'
            ' M600 720 L570 810 L660 780"/>'
        ),
    ),
    "ai-daily-digest": (
        DIGEST,
        (
            '<rect x="290" y="300" width="444" height="424" rx="40"/>'
            '<path d="M360 400 H664 M360 490 H500 M360 570 H500 M360 650 H500"/>'
            '<rect x="560" y="490" width="104" height="160" rx="12"/>'
        ),
    ),
    "council": (
        COUNCIL,
        (
            '<circle cx="340" cy="400" r="54"/><circle cx="512" cy="360" r="54"/>'
            '<circle cx="684" cy="400" r="54"/>'
            '<path d="M260 600 Q340 500 420 600 M432 560 Q512 460 592 560'
            ' M604 600 Q684 500 764 600 M260 700 H764"/>'
        ),
    ),
    "explainer-video": (
        WRITING,
        (
            '<path d="M290 740 H750 M290 740 V280"/>'
            '<path d="M370 620 C440 360 510 360 560 500 S660 680 730 400"/>'
            '<circle cx="730" cy="400" r="46" class="dot"/>'
        ),
    ),
    "generate-agents-md": (WRITING, DOC + '<path d="M520 470 V650 M430 560 H610"/>'),
    "gh-review-comments": (
        REVIEW,
        (
            BUBBLE + '<circle cx="412" cy="470" r="40" class="dot"/>'
            '<circle cx="532" cy="470" r="40" class="dot"/>'
            '<circle cx="652" cy="470" r="40" class="dot"/>'
        ),
    ),
    "git-clean-gone": (
        GIT,
        (
            '<circle cx="380" cy="300" r="52"/><circle cx="380" cy="724" r="52"/>'
            '<path d="M380 352 V672 M380 560 Q380 460 560 430"/>'
            '<path d="M600 360 L720 480 M720 360 L600 480"/>'
        ),
    ),
    "git-stage-hunk": (
        GIT,
        (
            '<path d="M290 360 H734 M290 512 H500 M290 664 H734"/>'
            '<path d="M640 440 V584 M568 512 H712"/>'
        ),
    ),
    "go-code-review": (
        REVIEW,
        (
            '<text x="512" y="640" text-anchor="middle" font-weight="800"'
            ' font-family="Helvetica Neue, Helvetica, Arial, sans-serif"'
            ' font-size="380" class="txt">Go</text>'
        ),
    ),
    "humanize": (
        WRITING,
        BUBBLE + '<path d="M370 470 Q430 390 490 470 T610 470 T700 460"/>',
    ),
    "kubecon-cfp": (
        WRITING,
        (
            '<rect x="432" y="250" width="160" height="320" rx="80"/>'
            '<path d="M340 470 Q340 680 512 680 Q684 680 684 470"/>'
            '<path d="M512 680 V774 M410 774 H614"/>'
        ),
    ),
    "kup": (
        DIGEST,
        (
            '<rect x="290" y="310" width="444" height="424" rx="44"/>'
            '<path d="M290 420 H734 M400 250 V350 M624 250 V350"/>'
            '<path d="M410 590 L490 660 L630 510"/>'
        ),
    ),
    "plan-critic": (
        COUNCIL,
        (
            '<rect x="320" y="290" width="384" height="484" rx="40"/>'
            '<path d="M430 260 H594 V330 H430 Z"/>'
            '<path d="M400 450 L440 490 L500 420 M550 455 H640'
            ' M400 600 L500 680 M500 600 L400 680 M550 640 H640"/>'
        ),
    ),
    "promptgen": (
        WRITING,
        (
            '<rect x="250" y="300" width="524" height="424" rx="48"/>'
            '<path d="M340 440 L440 520 L340 600 M490 610 H640"/>'
        ),
    ),
    "refactor-council": (
        COUNCIL,
        (
            '<path d="M330 470 A190 190 0 0 1 670 400"/>'
            '<path d="M670 400 L690 320 M670 400 L590 390"/>'
            '<path d="M694 554 A190 190 0 0 1 354 624"/>'
            '<path d="M354 624 L334 704 M354 624 L434 634"/>'
        ),
    ),
    "review-agents-md": (REVIEW, DOC + '<path d="M420 560 L490 630 L620 480"/>'),
    "rightsize": (
        REVIEW,
        (
            '<path d="M260 400 C320 280 400 640 460 512 S560 400 600 512 H764"/>'
            '<path d="M690 440 L764 512 L690 584"/>'
        ),
    ),
    "service-mesh-debug": (
        OPS,
        (
            '<path d="M512 270 L722 391 V633 L512 754 L302 633 V391 Z"/>'
            '<path d="M512 270 V754 M302 391 L722 633 M722 391 L302 633"/>'
            '<circle cx="512" cy="512" r="56" class="dot"/>'
        ),
    ),
    "ship-it": (
        OPS,
        (
            '<path d="M512 240 C610 330 630 470 604 620 H420'
            ' C394 470 414 330 512 240 Z"/>'
            '<circle cx="512" cy="430" r="52"/>'
            '<path d="M420 560 L340 660 V700 L440 640 M604 560 L684 660 V700'
            ' L584 640 M470 700 L512 784 L554 700"/>'
        ),
    ),
    "smallsteps": (
        TEST,
        (
            '<path d="M260 760 H380 V640 H500 V520 H620 V400 H740"/>'
            '<circle cx="740" cy="286" r="46" class="dot"/>'
        ),
    ),
    "staff-code-review": (
        REVIEW,
        (
            '<path d="M400 360 L260 512 L400 664 M624 360 L764 512 L624 664'
            ' M560 300 L464 724"/>'
        ),
    ),
    "staff-resume": (
        WRITING,
        (
            '<rect x="320" y="250" width="384" height="524" rx="40"/>'
            '<circle cx="512" cy="410" r="72"/>'
            '<path d="M400 600 Q512 500 624 600 M400 680 H624"/>'
        ),
    ),
    "technical-debt-manager": (
        OPS,
        (
            '<path d="M512 270 V750 M400 750 H624 M290 360 H734"/>'
            '<circle cx="512" cy="300" r="30" class="dot"/>'
            '<path d="M330 360 L250 540 Q330 610 410 540 Z'
            ' M694 360 L614 540 Q694 610 774 540 Z"/>'
        ),
    ),
    "test-writer": (
        TEST,
        (
            '<path d="M290 360 L330 400 L400 320 M470 360 H734'
            " M290 520 L330 560 L400 480 M470 520 H734"
            ' M290 680 L330 720 L400 640 M470 680 H640"/>'
        ),
    ),
    "youtube-summary": (
        DIGEST,
        (
            '<rect x="260" y="270" width="504" height="330" rx="70"/>'
            '<path d="M470 360 L590 435 L470 510 Z M300 680 H724 M300 760 H600"/>'
        ),
    ),
}

STYLE: Final[str] = (
    ".g * { fill: none; stroke: #FFFFFF; stroke-width: 56;"
    " stroke-linecap: round; stroke-linejoin: round; }"
    " .g .dot, .g .txt { fill: #FFFFFF; stroke: none; }"
)


def svg(name: str) -> str:
    """Return the SVG source of one plugin's icon."""
    (start, end), glyph = GLYPHS[name]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}"'
        f' viewBox="0 0 {SIZE} {SIZE}">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{start}"/>'
        f'<stop offset="1" stop-color="{end}"/>'
        f"</linearGradient><style>{STYLE}</style></defs>"
        f'<rect width="{SIZE}" height="{SIZE}" rx="224" fill="url(#bg)"/>'
        f'<g class="g">{glyph}</g></svg>\n'
    )


def render(name: str) -> Path:
    """Render one plugin's icon to its .claude-plugin/icon.png."""
    result = subprocess.run(
        [
            "/usr/bin/env",
            "rsvg-convert",
            "--width",
            "1024",
            "--height",
            "1024",
            "--format",
            "png",
        ],
        input=svg(name).encode(),
        capture_output=True,
        check=True,
        timeout=RENDER_TIMEOUT_SECONDS,
    )
    target = REPO_ROOT / "plugins" / name / ".claude-plugin" / "icon.png"
    target.write_bytes(result.stdout)
    return target


def plugin_names() -> list[str]:
    """Return every plugin that has a Claude Code manifest."""
    manifests = (REPO_ROOT / "plugins").glob("*/.claude-plugin/plugin.json")
    return sorted(manifest.parent.parent.name for manifest in manifests)


def main(argv: list[str] | None = None) -> int:
    """Render the requested icons and return the exit code."""
    parser = argparse.ArgumentParser(description="Render plugin directory icons")
    parser.add_argument("names", nargs="*", help="plugins to render (default: all)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only report plugins without a glyph",
    )
    args = parser.parse_args(argv)
    missing = [name for name in plugin_names() if name not in GLYPHS]
    if missing:
        print(f"no glyph for: {', '.join(missing)}", file=sys.stderr)
        return 1
    if args.check:
        return 0
    if not shutil.which("rsvg-convert"):
        print("rsvg-convert not found; install librsvg", file=sys.stderr)
        return 2
    unknown = [name for name in args.names if name not in GLYPHS]
    if unknown:
        print(f"unknown plugin: {', '.join(unknown)}", file=sys.stderr)
        return 2
    try:
        for name in args.names or plugin_names():
            print(render(name).relative_to(REPO_ROOT))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"render failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
