#!/usr/bin/env python3
"""Draw ocean swell as ASCII art, from maths rather than a photo.

Visual language (the 13-step ramp, the grid metrics, the embedded font, SMIL
motion) matches the rest of the page — see scripts/README.md.

Nothing is sampled from an image, so there is no third-party asset, no licence
and no attribution to carry.

The model is layered swell, seen side on, and it is deliberately stylised rather
than physical. An earlier attempt shaded the slope of a height field in
perspective; at one character per cell that reads as an interference pattern,
not as water, because the crest bands come out longer than the whole frame. What
does read, at this size, is overlap and occlusion:

  * Each layer is a crest line — a sum of three sines across the width — with
    everything below it filled solid.
  * Layers are painted far to near, so a nearer crest paints over the one behind
    it. Each layer therefore shows only the band between its own crest and the
    next one forward, which is what gives clean, obviously-water shapes.
  * Density, amplitude and spacing all grow toward the viewer, so the front of
    the frame is heavy and the back is open.

There is no separate foam line. One was tried and removed: a denser character on
the crest is *darker* on a light background, which is backwards — foam is the
bright part of a wave. The density step between one band and the next already
draws the crest, and adding a line on top of it only muddied the edge.

Animation, when frames > 1: every frame is drawn as its own <g> and SMIL cycles
their opacity. Layers drift at different speeds, which gives parallax. The loop
is seamless only because those speeds are whole numbers — phase runs 0..2*pi
across the cycle, so an integer speed lands back exactly where it started. A
fractional speed visibly jumps on every repeat.

Usage:
  python scripts/generate_waves.py --preview
  python scripts/generate_waves.py -o waves.svg --frames 12
"""
import argparse
import base64
import math
import os
import sys

# The same thirteen steps the rest of the page uses, lightest to darkest.
# jbmono-ramp.woff2 is subset to exactly these; a new character needs a new cut.
RAMP = [" ", ".", "`", ":", "-", "=", "+", "*", "c", "s", "#", "%", "@"]

# Grid. CHAR_W must stay FS * 0.600 — JetBrains Mono is 600/1000 units per em
# and the geometry assumes that advance.
FS = 12.9
CHAR_W = 7.74
LH = 15
PAD = 14

LIGHT_INK = "#6e7681"
DARK_INK = "#c9d1d9"
MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "&apos;Liberation Mono&apos;,monospace")

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
RAMP_FONT = "jbmono-ramp.woff2"

# One entry per layer, back to front:
#   fill   index into RAMP for the body of the layer
#   waves  (cycles across the width, amplitude in rows, phase offset, speed)
#          SPEEDS MUST BE WHOLE NUMBERS — see the note on looping above.
LAYERS = (
    dict(fill=1,  waves=((1.0, 0.7, 0.0, 1), (2.0, 0.35, 1.9, 2),
                         (3.0, 0.18, 4.1, 1))),
    dict(fill=3,  waves=((1.0, 0.9, 2.3, 1), (2.0, 0.45, 0.4, 2),
                         (3.5, 0.22, 3.3, 2))),
    dict(fill=5,  waves=((1.0, 1.2, 4.6, 2), (2.0, 0.55, 2.7, 1),
                         (4.0, 0.26, 1.1, 3))),
    dict(fill=7,  waves=((1.0, 1.5, 0.9, 2), (2.5, 0.65, 5.0, 3),
                         (4.0, 0.30, 2.4, 2))),
    dict(fill=9,  waves=((1.0, 1.9, 3.7, 3), (2.0, 0.80, 1.3, 2),
                         (4.5, 0.34, 5.6, 3))),
    dict(fill=11, waves=((1.0, 2.3, 5.8, 3), (2.5, 0.95, 3.9, 4),
                         (5.0, 0.38, 0.7, 2))),
)

TOP = 0.10      # where the farthest crest sits, as a fraction of height
SPAN = 0.88     # how much of the height the layers spread over
                # TOP + SPAN must stay <= 1.0, or the front layer
                # falls off the bottom of the grid and never paints
BUNCH = 1.45    # >1 bunches the far layers together, like distance would


def crest(layer, i, n, xn, phase, rows):
    """Screen row of this layer's crest at horizontal position xn (0..1)."""
    # far layers crowd toward the top, near ones spread out
    base = (TOP + SPAN * (((i + 1) / n) ** BUNCH)) * rows
    off = 0.0
    for cycles, amp, ph, spd in layer["waves"]:
        off += amp * math.sin(2 * math.pi * cycles * xn + ph + spd * phase)
    return base - off


def field(cols, rows, phase):
    """One frame, as a list of strings."""
    grid = [[0] * cols for _ in range(rows)]
    n = len(LAYERS)
    for i, layer in enumerate(LAYERS):          # back to front; near overpaints
        for x in range(cols):
            yc = crest(layer, i, n, (x + 0.5) / cols, phase, rows)
            j0 = int(math.ceil(yc))
            for j in range(max(j0, 0), rows):
                grid[j][x] = layer["fill"]
    return ["".join(RAMP[v] for v in row).rstrip() for row in grid]


# ---------------------------------------------------------------- svg

def font_face():
    with open(os.path.join(FONT_DIR, RAMP_FONT), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:400;font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def check_font():
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return
    have = {chr(c) for c in TTFont(os.path.join(FONT_DIR, RAMP_FONT))
            .getBestCmap()}
    missing = [c for c in RAMP if c != " " and c not in have]
    if missing:
        raise SystemExit(f"{RAMP_FONT} lacks {missing!r} — re-subset it, or "
                         f"pick ramp characters it already covers")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def text_rows(lines):
    out = []
    for i, line in enumerate(lines):
        if not line:
            continue
        y = PAD + i * LH + 11.2
        out.append(f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" '
                   f'class="a" font-size="{FS}">{esc(line)}</text>')
    return "".join(out)


def build(cols, rows, frames, period):
    width = int(PAD * 2 + cols * CHAR_W + 0.5)
    height = PAD * 2 + rows * LH
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
         f'height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{MONO}">'
         f'<style>{font_face()}.a{{fill:{LIGHT_INK}}}'
         f'@media(prefers-color-scheme:dark){{.a{{fill:{DARK_INK}}}}}'
         f'</style>']

    if frames <= 1:
        # still: reveal line by line, the cadence the rest of the page uses
        lines = field(cols, rows, 0.0)
        for i, line in enumerate(lines):
            if not line:
                continue
            y = PAD + i * LH
            w = len(line) * CHAR_W
            begin = i * 0.09
            p.append(f'<clipPath id="w{i}"><rect x="{PAD}" y="{y}" '
                     f'height="{LH}" width="0"><animate attributeName="width" '
                     f'from="0" to="{w:.1f}" begin="{begin:.2f}s" dur="0.09s" '
                     f'fill="freeze"/></rect></clipPath>')
            p.append(f'<g clip-path="url(#w{i})">'
                     + text_rows([""] * i + [line]) + '</g>')
        p.append("</svg>")
        return "".join(p)

    # animated: one <g> per frame, shown for its own slice of the cycle
    slice_ = 1.0 / frames
    for f in range(frames):
        lines = field(cols, rows, 2 * math.pi * f / frames)
        # Opaque for its own slice of the cycle, then hidden. keyTimes runs all
        # the way to 1 on purpose: a discrete list that stops short is left to
        # the renderer to interpret, and browsers do not agree on it.
        p.append(
            f'<g opacity="0"><animate attributeName="opacity" '
            f'values="1;0;0" keyTimes="0;{slice_:.5f};1" calcMode="discrete" '
            f'dur="{period:.3f}s" begin="{f * period * slice_:.3f}s" '
            f'repeatCount="indefinite"/>'
            + text_rows(lines) + '</g>')
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Draw ASCII ocean swell.")
    ap.add_argument("-o", "--out", default="waves.svg")
    ap.add_argument("--cols", type=int, default=76,
                    help="76 lands the SVG on the 620px page width")
    ap.add_argument("--rows", type=int, default=22)
    ap.add_argument("--frames", type=int, default=12,
                    help="1 draws a still with a line-by-line reveal")
    ap.add_argument("--period", type=float, default=6.0,
                    help="seconds for one full loop")
    ap.add_argument("--preview", action="store_true",
                    help="print frame 0 as text and write nothing")
    args = ap.parse_args()

    check_font()
    if args.preview:
        print("\n".join(field(args.cols, args.rows, 0.0)))
        print(f"\n[{args.cols} x {args.rows} cells]", file=sys.stderr)
        return

    svg = build(args.cols, args.rows, args.frames, args.period)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{args.out}: {args.cols}x{args.rows} cells, "
          f"{args.frames} frames, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
