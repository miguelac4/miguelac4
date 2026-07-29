# Generating the page

Nothing here runs on a schedule. Every graphic is generated locally and
committed, so the rendered README makes no third-party requests and cannot
break because someone else's service went down or rate-limited you.

## The section headings

```
python scripts/generate_headings.py
```

Writes `hd-about.svg`, `hd-stack.svg`, `hd-tools.svg`,
`hd-a-little-bit-more-about-me.svg` and `dash.svg`.

`dash.svg` is the hairline marking each item in the about list. It is an image
rather than a `-` or `─` character so it carries the page's own rule colour and
switches with the viewer's theme; a text character would render in GitHub's
sans at whatever weight that font gives it.

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

`ascii.svg`, the only one the page currently uses, was made with:

```
# a face, lighter than its background, so inverted
python scripts/generate_portrait.py PHOTO \
  --crop 0.20,0.33,0.63,0.72 --rows 50 --flatten 0 --autocontrast 2 \
  --invert -o ascii.svg
```

Its source photo is deliberately **not** committed — it is not needed to render
the page, and the frame has other people in it.

The closing image is the photograph itself, not an ASCII treatment. To go back
to one, this is the command that produced it — no `--invert`, because a cliff
against a bright sky is *darker* than its background, and 76 columns is what
lands it exactly on the 620px page width:

```
python scripts/generate_portrait.py assets/img/surfing-in-ericeira.jpg \
  --rows 20 --cols 76 --flatten 0 --autocontrast 1 -o sea.svg
```

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
