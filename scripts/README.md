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

## The tube

```
python scripts/generate_waves.py -o waves.svg --frames 12 --period 6
```

Standard library only. No image is involved — the barrel is drawn from a closed
form — so there is no licence, no attribution and no third-party asset on the
page.

`--preview` prints frame 0 as text and writes nothing. Use it while tuning; the
knobs worth touching are `EXIT_*` for the opening, `WALL` and `RIM` for how the
water darkens, and `SPIN`/`SWIRL` for the striations. `--frames 1` gives a still
with the same line-by-line reveal the rest of the page uses.

**After editing anything in the model, check the loop still closes:**

```
python -c "import importlib.util,math; s=importlib.util.spec_from_file_location('w','scripts/generate_waves.py'); w=importlib.util.module_from_spec(s); s.loader.exec_module(w); print(w.field(76,24,0)==w.field(76,24,2*math.pi))"
```

Three things break it, and all three were hit while writing this:

* **`SWIRL` must be a whole number.** `atan2` jumps from +π to −π along the
  negative x axis. A fractional coefficient turns that branch cut into a seam
  running visibly out of the frame.
* **`SPEED` must be a whole number**, or the animation jumps on every repeat.
* **The foam cannot reseed its hash per frame.** It is one fixed speckle pattern
  scrolled sideways and wrapped at the frame width, which returns to its start by
  construction. Seeding from the phase gives one more distinct value than there
  are frames, and the foam resets visibly once per loop.

Also worth knowing: everything is computed in **pixel** space, not cell space. A
cell is 7.74 by 15, so a shape laid out in rows and columns comes out half as
tall as intended.

Three models were tried before this one, which is why the file looks the way it
does:

1. Shading the slope of a height field in perspective. Physically the most
   honest, and it reads as an interference pattern — the crest bands come out
   longer than the frame is wide.
2. Layered swell: crest lines filled solid and overpainted front to back. This
   reads as water, and is in the git history if a calm sea is ever wanted. A
   denser character on each crest was tried and dropped, because denser is
   *darker* on a light background and foam is the bright part of a wave.
3. The barrel seen from outside — a wave with a hole in it. At this resolution it
   reads as a hook, not a tube.

What works is the barrel seen from **inside**: a bright almond exit, ink rising
with distance out from it, striations sheared by bearing. The vignette is what
carries it.

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
