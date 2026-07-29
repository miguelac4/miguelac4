# Generating the page

Nothing here runs on a schedule. Every graphic is generated locally and
committed, so the rendered README makes no third-party requests and cannot
break because someone else's service went down or rate-limited you.

## The section headings

```
python scripts/generate_headings.py
```

Writes `hd-about.svg`, `hd-stack.svg`, `hd-tools.svg` and
`hd-a-little-bit-more-about-me.svg`.

To rename or add a section, edit `HEADINGS` at the top of the script. The
embedded font is subset to exactly the letters those words spell, so a new
letter needs a new subset — the script checks and tells you the command if so.
The letters currently available are `abceiklmorstu` and space.

## The ASCII pictures

```
python scripts/generate_portrait.py PHOTO -o ascii.svg [options]
```

Needs Pillow (`python -m pip install Pillow`). Pillow is a build dependency
only: the finished SVG carries its own font and needs nothing at render time.

Always start with `--preview`, which prints the character grid to the terminal
and writes no file. Tune, then drop `--preview` and add `-o`.

Useful options:

| option | what it does |
|---|---|
| `--crop L,T,R,B` | fractions of width/height; crop tight on the subject |
| `--rows N` | character rows, and so the detail level (default 56) |
| `--invert` | map **bright** pixels to dense characters |
| `--flatten R` | subtract a blurred copy to remove a lighting gradient; `0` off |
| `--autocontrast P` | percent clipped off each tonal tail |
| `--equalize` | full histogram equalisation |
| `--gamma G` | mid-tone lift |

`--invert` is a composition decision, not a preference. The design wants an
empty background and a dense subject. If the subject is *lighter* than its
background — a lit face in a dark room — you need `--invert` to get that.
If the subject is *darker* — a cliff against bright sky — you don't.

What actually decides whether the result reads: the subject filling the frame,
real tonal separation between it and the background, and sharp focus. A dark,
soft, or busy photo cannot be rescued by these options; crop harder or use a
different photo.

The two pictures currently committed were made with:

```
# ascii.svg — a face, lighter than its background, so inverted
python scripts/generate_portrait.py PHOTO \
  --crop 0.20,0.33,0.63,0.72 --rows 50 --flatten 0 --autocontrast 2 \
  --invert -o ascii.svg

# sea.svg — a cliff against bright sky, so not inverted.
# 76 columns is what makes it exactly the 620px page width.
python scripts/generate_portrait.py assets/img/surfing-in-ericeira.jpg \
  --rows 20 --cols 76 --flatten 0 --autocontrast 1 -o sea.svg
```

The source photo for `ascii.svg` is deliberately **not** committed — it is not
needed to render the page, and the frame has other people in it.

## Checking the render before pushing

`_preview.html` (gitignored) shows the page in light and dark side by side.
Browsers refuse `file://` subresources for image documents, so serve it:

```
python -m http.server 8731
# then open http://127.0.0.1:8731/_preview.html
```

## Credit

Layout, palette, typography, the character ramp and the reveal animation follow
[andriidrok1/andriidrok1](https://github.com/andriidrok1/andriidrok1). That
repository ships its finished `ascii.svg` but not a generator for it, so
`generate_portrait.py` is a fresh implementation of the same idea.

The typeface is JetBrains Mono under the SIL Open Font License — see
`fonts/OFL.txt`.
