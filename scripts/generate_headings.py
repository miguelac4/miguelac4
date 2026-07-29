#!/usr/bin/env python3
"""Draw the README's section headings as SVGs.

Visual design (palette, typography, the hairline rule) follows
https://github.com/andriidrok1/andriidrok1 — see the credit in README.md.

Why the headings are images at all: GitHub strips <style> and style= from
rendered markdown, so a real markdown heading can only ever be GitHub's own
sans-serif. Drawing the label as an SVG is the only way to put this page's own
typeface on it.

These are static — they depend on no data, so this runs once and the output is
committed. Re-run it only after editing HEADINGS.

Standard library only, except fontTools when a heading needs a letter the
current subset lacks (see check_coverage below, which tells you).

Usage:
  python scripts/generate_headings.py [OUT_DIR]
"""
import base64
import functools
import os
import sys

# The words drawn as hd-*.svg, in page order.
HEADINGS = ("about", "stack", "tools", "a little bit more about me")

# The portrait's ink is the heading ink, so the page reads as one material.
LIGHT = dict(emph="#424a53", rule="#d8dee4")
DARK = dict(emph="#f0f6fc", rule="#30363d")
MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "&apos;Liberation Mono&apos;,monospace")

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
HEAD_FONT = "jbmono-head.woff2"

WIDTH = 620      # the column width every graphic on the page shares
FS = 16          # heading size
HEIGHT = 26
ADVANCE = 0.6    # JetBrains Mono is 600/1000 units per em


@functools.lru_cache(maxsize=None)
def face(filename, weight):
    """One @font-face rule with the subset inlined as a data URI.

    An external font URL cannot work here: these SVGs are loaded through <img>,
    and a browser refuses to fetch subresources for an image document. A base64
    data URI is the only mechanism, and it keeps the page free of third-party
    requests.
    """
    with open(os.path.join(FONT_DIR, filename), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def draw(word):
    """A heading in the mono face, with a hairline running to the right margin.

    The rule starts past the longest plausible advance, so a narrower fallback
    font on the viewer's machine widens the gap slightly rather than colliding
    with the text.
    """
    rule_x = len(word) * FS * ADVANCE + 18
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" '
        f'font-family="{MONO}">'
        f'<style>{face(HEAD_FONT, 600)}'
        f'.e-f{{fill:{LIGHT["emph"]}}}.u-s{{stroke:{LIGHT["rule"]}}}'
        f'@media(prefers-color-scheme:dark){{'
        f'.e-f{{fill:{DARK["emph"]}}}.u-s{{stroke:{DARK["rule"]}}}}}</style>'
        f'<text x="0" y="18" class="e-f" font-size="{FS}" '
        f'font-weight="600">{word}</text>'
        f'<line x1="{rule_x:.0f}" y1="12.5" x2="{WIDTH}" y2="12.5" '
        f'class="u-s" stroke-width="1"/>'
        f'</svg>')


def check_coverage():
    """Fail loudly if the subset is missing a letter, rather than drawing tofu.

    The embedded font is subset to exactly the letters HEADINGS spells. Adding a
    word with a new letter silently renders a blank box in browsers, so this
    checks up front. fontTools is optional — skip the check if it isn't there.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return
    have = {chr(c) for c in TTFont(os.path.join(FONT_DIR, HEAD_FONT))
            .getBestCmap()}
    missing = sorted(set("".join(HEADINGS)) - have)
    if missing:
        raise SystemExit(
            f"{HEAD_FONT} lacks {missing!r}. Re-subset it from "
            f"jbmono-600.woff2 with the letters HEADINGS now needs:\n"
            f"  python -c \"from fontTools import subset; "
            f"subset.main(['scripts/fonts/jbmono-600.woff2', "
            f"'--text={''.join(sorted(set(''.join(HEADINGS))))}', "
            f"'--flavor=woff2', "
            f"'--output-file=scripts/fonts/{HEAD_FONT}'])\"")


def write(path, svg):
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old == svg:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return True


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    check_coverage()
    changed = []
    for word in HEADINGS:
        name = f"hd-{word.replace(' ', '-')}.svg"
        if write(os.path.join(out_dir, name), draw(word)):
            changed.append(name)
    print("updated: " + (", ".join(changed) if changed else "nothing"))


if __name__ == "__main__":
    main()
