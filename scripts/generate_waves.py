#!/usr/bin/env python3
"""Draw a barrelling wave — a tube — as ASCII art, from maths rather than a photo.

Visual language (the 13-step ramp, the grid metrics, the embedded font, SMIL
motion) matches the rest of the page — see scripts/README.md.

Nothing is sampled from an image, so there is no third-party asset, no licence
and no attribution to carry.

The view is from inside the barrel looking out, which is both the iconic image
and by far the easier one to draw. Seen from outside, a tube is a wave with a
hole in it, and at one character per cell that reads as a hook or a blob — two
attempts at it are in this file's history. From inside it is a vignette:

  * The exit is an ellipse, off centre and leaning, so it reads as an almond
    slot rather than a porthole.
  * Ink rises with distance out from that ellipse: almost none at the lip,
    saturating deep in the throat. That gradient is the whole illusion of being
    inside something.
  * Striations wind around the throat, their phase sheared by the bearing angle.
    Shearing is what turns concentric rings into a curl.
  * Along the floor, speckled foam tearing past.

All of this happens in pixel space, not cell space. A cell is 7.74 by 15, so a
shape laid out in rows and columns comes out half as tall as intended and the
exit ends up an oval lying on its side.

Animation, when frames > 1: every frame is drawn as its own <g> and SMIL cycles
their opacity. Two things have to be whole numbers or the loop breaks, and both
are marked at their definitions:

  * SWIRL, the angular shear. atan2 jumps from +pi to -pi along the negative x
    axis, and a fractional coefficient turns that branch cut into a seam running
    visibly out of the frame.
  * SPEED. Phase runs 0..2*pi across the cycle, so an integer returns exactly to
    its start; a fraction jumps on every repeat.

The foam has the same constraint and solves it differently: it is one fixed
speckle pattern scrolled sideways, wrapping at the frame width. Reseeding a hash
per frame does not close the loop.

Check with field(c, r, 0) == field(c, r, 2*math.pi) after editing anything here.

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

# --- the tube, seen from inside looking out. Fractions of the canvas width. ---
# The exit sits off centre and high, the way it does when you are still deep in
# the barrel: water wraps most of the frame and the way out is a slot to one side.
EXIT_X, EXIT_Y = 0.640, 0.430   # centre of the opening
EXIT_RX = 0.140                 # opening half-width
EXIT_RY = 0.094                 # opening half-height
EXIT_TILT = -0.42               # radians; the almond leans with the curl

WALL = 0.62                     # distance, past the opening, at which the water
                                # reaches full darkness. Too small and the frame
                                # saturates solid with no water visible; too
                                # large and the back of the tube never gets dark,
                                # which is what sells the depth.
RIM = 0.10                      # width of the bright lip right at the opening

SPIN = 2.05                     # how tightly the striations wind
# SWIRL MUST BE A WHOLE NUMBER. atan2 jumps from +pi to -pi along the negative x
# axis; a fractional coefficient turns that branch cut into a visible seam
# running out of the frame. An integer makes the jump a whole number of cycles.
SWIRL = 2
SPEED = 2                       # whole number, or the loop will not close

FOAM_Y = 0.86                   # water rushing past along the bottom
FOAM_SOFT = 0.16


def hash01(a, b, c=0):
    """Deterministic pseudo-random in 0..1. Same output on every machine."""
    h = (a * 73856093) ^ (b * 19349663) ^ (c * 83492791)
    h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 0xFFFFFFFF


def field(cols, rows, phase):
    """One frame, as a list of strings."""
    W = cols * CHAR_W
    H = rows * LH
    cx, cy = EXIT_X * W, EXIT_Y * H
    scale = W                      # every radius is a fraction of the width
    last = len(RAMP) - 1
    ct, st = math.cos(EXIT_TILT), math.sin(EXIT_TILT)
    # how far the foam speckle has scrolled; wraps to 0 after a full cycle
    shift = int(phase / (2 * math.pi) * cols) % cols

    grid = [[0] * cols for _ in range(rows)]
    for j in range(rows):
        py = (j + 0.5) * LH
        for x in range(cols):
            px = (x + 0.5) * CHAR_W
            # Pixel space, not cell space: a cell is 7.74 by 15, so a shape laid
            # out in rows and columns comes out half as tall as intended.
            dx, dy = (px - cx) / scale, (py - cy) / scale
            # rotate into the opening's own frame, so the almond can lean
            ex = (dx * ct + dy * st) / EXIT_RX
            ey = (-dx * st + dy * ct) / EXIT_RY
            d = math.hypot(ex, ey)          # 1.0 exactly on the opening's edge

            if d <= 1.0:
                grid[j][x] = 0              # daylight
                continue

            # How far into the barrel this cell is. Ink rises from nothing at the
            # lip to full dark deep inside, which is the vignette that makes the
            # frame read as being *inside* something.
            out = (d - 1.0) * EXIT_RX / max(WALL, 1e-6)
            if out < RIM:
                v = 0.10 + 0.35 * (out / RIM)
            else:
                v = 0.45 + 0.55 * min(1.0, (out - RIM) / max(1e-6, 1.0 - RIM))

            # Striations winding around the throat. Shearing them with the angle
            # is what turns concentric rings into a curl.
            th = math.atan2(dy, dx)
            wind = SPIN * math.log(max(d, 1e-6)) * 6.0 - SWIRL * th
            v *= 0.80 + 0.20 * math.sin(wind - SPEED * phase)

            # Water tearing past along the floor of the tube. The speckle is a
            # fixed pattern scrolled sideways, wrapping at the frame width, so it
            # returns to its start after one cycle. Reseeding the hash per frame
            # instead does not close the loop, and the foam visibly resets.
            fy = (py / H - FOAM_Y) / FOAM_SOFT
            if fy > 0 and out > 0.25:
                n = hash01((x + shift) % cols, j)
                v = max(v, min(1.0, fy) * (0.42 + 0.5 * n))

            grid[j][x] = int(max(0.0, min(1.0, v)) * last + 0.5)

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
    ap = argparse.ArgumentParser(description="Draw a barrelling wave in ASCII.")
    ap.add_argument("-o", "--out", default="waves.svg")
    ap.add_argument("--cols", type=int, default=76,
                    help="76 lands the SVG on the 620px page width")
    ap.add_argument("--rows", type=int, default=24)
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
