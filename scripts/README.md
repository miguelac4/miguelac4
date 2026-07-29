# Generating the page

Nothing here runs on a schedule. Every graphic is generated locally and
committed, so the rendered README makes no third-party requests and cannot
break because someone else's service went down or rate-limited you.

## The section headings

```
python scripts/generate_headings.py
```

Writes `hd-about.svg`, `hd-stack.svg`, `hd-tools.svg` and `dash.svg`.

`dash.svg` is the hairline marking each item in the about list. It is an image
rather than a `-` or `─` character so it carries the page's own rule colour and
switches with the viewer's theme; a text character would render in GitHub's
sans at whatever weight that font gives it.

To rename or add a section, edit `HEADINGS` at the top of the script. The
embedded font is subset to exactly the letters those words spell, so a new
letter needs a new subset — the script checks and tells you the command if so.
The letters currently available are `abcklostu` and space.

## The waves

```
python scripts/generate_waves.py -o waves.svg --frames 12 --period 6
```

Standard library only. No image is involved: the swell is a sum of sines, so
there is no licence, no attribution and no third-party asset on the page.

`--preview` prints frame 0 as text and writes nothing — use it while tuning
`LAYERS`, `TOP`, `SPAN` and `BUNCH`. `--frames 1` gives a still with the same
line-by-line reveal the rest of the page uses.

Two things will break it if you edit the model:

* **Component speeds must be whole numbers.** Phase runs 0 to 2π across one
  cycle, so an integer speed lands back exactly where it started and the loop is
  seamless. A fractional speed visibly jumps on every repeat. `generate_waves.py`
  has a check for this in its docstring, not in code — verify with
  `field(c, r, 0) == field(c, r, 2*pi)`.
* **`TOP + SPAN` must stay at or below 1.0**, or the frontmost layer's crest
  falls below the last row and that layer never paints at all.

Two approaches were tried. Shading the slope of a height field in perspective —
physically the more honest one — reads as an interference pattern at one
character per cell, because the crest bands come out longer than the frame is
wide. Layered occlusion is stylised but actually reads as water. Likewise a
denser character on each crest was removed: on a light background denser means
darker, and foam is the bright part of a wave, so it inverted the tone.

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

**Nothing on the page uses this right now** — the hero is the photograph itself.
The script is kept because it works and the option is one command away.

A portrait was tried and dropped: the only photo available was dark, soft and
had three people in it, and at one character per cell that reads as texture
rather than a face. No amount of tuning fixes an input like that.

The Ericeira frame, by contrast, renders well — a cliff against a bright sky has
exactly the tonal separation this needs. No `--invert`, because the subject is
*darker* than its background, and 76 columns is what lands it on the 620px page
width:

```
python scripts/generate_portrait.py assets/img/surfing-in-ericeira.jpg \
  --rows 20 --cols 76 --flatten 0 --autocontrast 1 -o sea.svg
```

Then point the hero at `./sea.svg` instead of the photograph.

## Checking the render before pushing

Build `_preview.html` (gitignored) by pushing `README.md` through GitHub's own
markdown renderer, then serve it — browsers refuse `file://` subresources for
image documents, so it has to go over HTTP:

```
python scripts/preview.py
python -m http.server 8731
# then open http://127.0.0.1:8731/_preview.html
```

It shows the page stacked in light and dark. Two things worth knowing if you
edit the markdown by hand:

* Ask the API for `mode=markdown`, not `mode=gfm`. `gfm` is comment semantics
  and turns every single newline into a `<br>`, which double-spaces anything
  that already uses explicit `<br>`. README files do not behave that way.
* A line may start with `<img>` and still contain `**bold**` — `img` is inline,
  so it does not switch markdown off. A block-level tag such as `<div>` would.

## Credit

Layout, palette, typography, the character ramp and the reveal animation follow
[andriidrok1/andriidrok1](https://github.com/andriidrok1/andriidrok1). That
repository ships its finished `ascii.svg` but not a generator for it, so
`generate_portrait.py` is a fresh implementation of the same idea.

The typeface is JetBrains Mono under the SIL Open Font License — see
`fonts/OFL.txt`.
