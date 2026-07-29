#!/usr/bin/env python3
"""Turn a photo into the README's ASCII portrait.

Visual design (the character ramp, the grid metrics, the line-by-line reveal
with a cursor riding the edge) follows
https://github.com/andriidrok1/andriidrok1 — see the credit in README.md. That
repository ships the finished ascii.svg but not the generator, so this is a
fresh implementation of the same idea.

The output is a one-off artifact, not something a schedule regenerates: run it
when the photo changes, commit the result.

Requires Pillow, which is a *build* dependency only — nothing at render time,
since the SVG carries its own font and needs no network.

Usage:
  python scripts/generate_portrait.py PHOTO [-o ascii.svg] [options]
  python scripts/generate_portrait.py PHOTO --preview      # text, no file

The knobs exist because a photo taken in a dark room is the hard case: a global
contrast stretch just turns the whole frame into '@'. --flatten divides out the
lighting gradient first (see prepare), which is what makes such a photo legible
at all. Start with --preview and tune before writing the SVG.
"""
import argparse
import base64
import os
import re
import sys

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
except ImportError:
    sys.exit("Pillow is required: python -m pip install Pillow")

# Thirteen steps, lightest to darkest. This exact set is what jbmono-ramp.woff2
# is subset to — adding a character to the ramp means re-subsetting the font,
# and an absent glyph renders as a blank box.
RAMP = [" ", ".", "`", ":", "-", "=", "+", "*", "c", "s", "#", "%", "@"]

# The grid. CHAR_W must equal FS * 0.600: JetBrains Mono is 600/1000 units per
# em, and the whole geometry assumes that advance. The embedded font is what
# lets this hold on a machine whose default monospace is narrower.
FS = 12.9
CHAR_W = 7.74
LH = 15
PAD = 14
BASELINE = 11.2          # text baseline offset within the line box
CELL_ASPECT = CHAR_W / LH

# Ink, matching the section headings and the rest of the page.
LIGHT_INK = "#6e7681"
DARK_INK = "#c9d1d9"
MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "&apos;Liberation Mono&apos;,monospace")

# Reveal cadence: one line every STEP seconds, each line wiped open in STEP.
STEP = 0.09
CURSOR_W = 6
CURSOR_H = 12

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
RAMP_FONT = "jbmono-ramp.woff2"


# ---------------------------------------------------------------- image

def crop_box(im, spec):
    """Parse --crop L,T,R,B given as fractions of width/height."""
    try:
        l, t, r, b = (float(x) for x in spec.split(","))
    except ValueError:
        raise SystemExit("--crop wants four numbers: left,top,right,bottom "
                         "as fractions, e.g. 0.17,0.31,0.77,0.91")
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        raise SystemExit("--crop fractions must satisfy 0<=l<r<=1 and 0<=t<b<=1")
    w, h = im.size
    return (int(l * w), int(t * h), int(r * w), int(b * h))


def prepare(im, flatten, denoise, gamma, equalize, autocontrast):
    """Grey, denoise, kill the lighting gradient, then stretch what's left.

    --flatten is the important one for an underexposed photo. Subtracting a
    heavily blurred copy removes the low-frequency lighting — the dark room, the
    bright lamp in the corner — and keeps the local detail that actually carries
    a face. Without it, a global stretch spends the whole ramp separating
    "lamp" from "everything else" and the subject stays a single flat tone.
    """
    im = im.convert("L")

    if denoise > 1:
        # Photos off a phone screenshot or a messaging app are grainy, and grain
        # at one character per cell reads as noise, not texture.
        im = im.filter(ImageFilter.MedianFilter(size=denoise))

    if flatten > 0:
        blur = im.filter(ImageFilter.GaussianBlur(radius=flatten))
        # (im - blur) + 128, clipped: the high-frequency detail on mid grey.
        high = ImageChops.subtract(im, blur, 1.0, 128)
        # Blend rather than replace, so the large-scale form of the head survives.
        im = ImageChops.blend(im, high, 0.72)

    if autocontrast > 0:
        im = ImageOps.autocontrast(im, cutoff=autocontrast)
    if equalize:
        im = ImageOps.equalize(im)
    if gamma != 1.0:
        lut = [min(255, int(255 * ((i / 255) ** (1.0 / gamma)) + 0.5))
               for i in range(256)]
        im = im.point(lut)
    return im


def to_rows(im, rows, cols=None, invert=False):
    """Sample the image onto the character grid and map luminance to the ramp."""
    w, h = im.size
    if cols is None:
        # Cells are much taller than wide, so the column count has to be scaled
        # by the cell aspect or the portrait comes out stretched.
        cols = max(1, round(rows * (w / h) / CELL_ASPECT))
    small = im.resize((cols, rows), Image.LANCZOS)
    px = small.load()
    last = len(RAMP) - 1
    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            v = px[x, y]
            if not invert:
                v = 255 - v          # dark pixel -> dense character
            line.append(RAMP[round(v / 255 * last)])
        out.append("".join(line).rstrip())
    return out, cols


# ---------------------------------------------------------------- svg

def font_face():
    with open(os.path.join(FONT_DIR, RAMP_FONT), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:400;font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def check_ramp_font():
    """The ramp font is subset to RAMP exactly; a missing glyph draws tofu."""
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


def build_svg(rows, cols):
    """One clipPath per line, opened left to right, with a cursor on the edge.

    Motion is SMIL: GitHub strips <script> from README markdown, and these
    files are loaded through <img> anyway, where scripts never run.
    """
    width = int(PAD * 2 + cols * CHAR_W + 0.5)
    height = PAD * 2 + len(rows) * LH

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
         f'height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{MONO}">'
         f'<style>{font_face()}.a{{fill:{LIGHT_INK}}}'
         f'@media(prefers-color-scheme:dark){{.a{{fill:{DARK_INK}}}}}</style>']

    for i, line in enumerate(rows):
        if not line:
            continue
        y = PAD + i * LH
        w_px = len(line) * CHAR_W
        begin = i * STEP
        cid = f"c{i}"
        # The rect's own width is the FULL width, and the animation runs 0 -> full
        # on top of it. That ordering matters: if SMIL does not run, the picture
        # is simply there, un-animated, instead of being invisible. Starting the
        # attribute at 0 and relying on the animation to open it means anything
        # that stalls SMIL leaves a blank frame — which is exactly what GitHub's
        # rendered README did, while the same file animated fine standalone.
        p.append(f'<clipPath id="{cid}"><rect x="{PAD}" y="{y}" '
                 f'height="{LH}" width="{w_px:.1f}">'
                 f'<animate attributeName="width" from="0" to="{w_px:.1f}" '
                 f'begin="{begin:.2f}s" dur="{STEP}s" fill="freeze"/>'
                 f'</rect></clipPath>')
        safe = line.replace("&", "&amp;").replace("<", "&lt;")
        p.append(f'<g clip-path="url(#{cid})"><text xml:space="preserve" '
                 f'x="{PAD}" y="{y + BASELINE:.1f}" class="a" '
                 f'font-size="{FS}">{safe}</text></g>')
        p.append(f'<rect y="{y + 1}" width="{CURSOR_W}" height="{CURSOR_H}" '
                 f'class="a" opacity="0">'
                 f'<animate attributeName="x" from="{PAD}" '
                 f'to="{PAD + w_px:.1f}" begin="{begin:.2f}s" dur="{STEP}s" '
                 f'fill="freeze"/>'
                 f'<set attributeName="opacity" to="0.8" begin="{begin:.2f}s"/>'
                 f'<set attributeName="opacity" to="0" '
                 f'begin="{begin + STEP:.2f}s"/></rect>')

    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        description="Render a photo as the README's ASCII portrait.")
    ap.add_argument("photo")
    ap.add_argument("-o", "--out", default="ascii.svg")
    ap.add_argument("--rows", type=int, default=56,
                    help="character rows; the reference portrait uses 56")
    ap.add_argument("--cols", type=int,
                    help="override the column count instead of deriving it "
                         "from the crop's aspect ratio")
    ap.add_argument("--crop", help="left,top,right,bottom as fractions")
    ap.add_argument("--flatten", type=float, default=24.0,
                    help="blur radius for the lighting-gradient subtraction; "
                         "0 disables it (default: 24)")
    ap.add_argument("--denoise", type=int, default=3,
                    help="median filter size, odd; 1 disables (default: 3)")
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--equalize", action="store_true",
                    help="full histogram equalisation after the stretch")
    ap.add_argument("--autocontrast", type=float, default=1.0,
                    help="percent clipped off each tail (default: 1)")
    ap.add_argument("--invert", action="store_true",
                    help="map bright pixels to dense characters instead")
    ap.add_argument("--preview", action="store_true",
                    help="print the grid as text and write nothing")
    args = ap.parse_args()

    check_ramp_font()
    im = Image.open(args.photo)
    if args.crop:
        im = im.crop(crop_box(im, args.crop))
    im = prepare(im, args.flatten, args.denoise, args.gamma,
                 args.equalize, args.autocontrast)
    rows, cols = to_rows(im, args.rows, args.cols, args.invert)

    if args.preview:
        print("\n".join(rows))
        print(f"\n[{cols} x {len(rows)} cells, source crop "
              f"{im.size[0]}x{im.size[1]}]", file=sys.stderr)
        return

    svg = build_svg(rows, cols)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{args.out}: {cols} x {len(rows)} cells, "
          f"{len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
