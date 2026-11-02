# Figures

The figures in [algorithm.md](../algorithm.md) are drawn in Inkscape and typeset through TikZ,
as in the writeup.

| path | what | edit? |
|---|---|---|
| `svg_src/<panel>.svg` | one diagram, as an Inkscape SVG | yes, in Inkscape |
| `layouts/<figure>.tex` | how panels combine into one figure (`\mapsto`, `+`, …) | yes |
| `<figure>.svg` | the rendered figure the docs embed | no, generated |
| `build/` | svg2tikz output and LaTeX intermediates | no, generated and ignored by git |

The rendered `<figure>.svg` files are committed so that GitHub can show them, but their text
is outlined into paths, so Inkscape cannot edit them usefully. Edit `svg_src/` instead.

## Editing a figure

```bash
inkscape docs/figs/svg_src/algo_start_region.svg &
bash docs/figs/build.sh -w        # rebuilds whatever you save, until Ctrl-C
```

or run `bash docs/figs/build.sh` once after saving: it rebuilds every figure whose layout or
panels have changed, and `-f` rebuilds everything.

The pipeline is

```
svg_src/<panel>.svg  --svg2tikz-->  build/panels/<panel>.tex
layouts/<figure>.tex --pdflatex-->  build/<figure>.pdf  --pdftocairo-->  <figure>.svg
```

with svg2tikz run as by the writeup's svg watcher (`-t raw --markings interpret --arrow
stealth`), so the conventions are the same as there:

- **Text is LaTeX source.** Text is passed to LaTeX verbatim, so a label is typed as e.g.
  `{\contour{white}{$\scriptstyle -3$}}`. Its position in Inkscape is the south-west corner of
  the typeset text; its size in Inkscape is ignored.
- **`baseline_text`.** The layouts align panels on the object with id `baseline_text` (often
  an empty text), so every panel needs one.
- **One A4 page per panel.** svg2tikz maps the point $(x, y)$ in mm to
  $(x/10, (297 - y)/10)$ in cm; only the relative positions matter.

## TODO notes

A panel that still needs work has a layer called **TODO** holding red text
`\todonote{...}`. It renders as a red note above the panel, wrapped to 2.3 cm
(`\todonote[3cm]{...}` for another width). When the panel is done, delete the layer and rebuild.

```bash
grep -l 'inkscape:label="TODO"' docs/figs/svg_src/*.svg       # panels still to do
```

The `details_case_boundary_*` panels are placeholders: copies of the case 0, 1A, 1B and 2
panels, to be redrawn for starting and ending on the boundary.

## Adding a figure

1. Draw each panel as `svg_src/<panel>.svg`, starting from a copy of a similar one.
2. Write `layouts/<figure>.tex`, which is the body of one display, inputting each panel as
   `\includetikz[baseline=(baseline_text.center)]{panels/<panel>.tex}`.
3. Run `bash docs/figs/build.sh` and embed `figs/<figure>.svg` in the docs. Widths of about
   2.2 × the SVG's width in pt keep the figures to one scale.

## Requirements

- [svg2tikz](https://github.com/xyz2tex/svg2tikz) (`pip install svg2tikz`). If it is not on
  `PATH`, for instance if it is only a shell alias, set `SVG2TIKZ=/path/to/svg2tikz`.
- `pdflatex` with the `tikz` and `contour` packages.
- `pdftocairo`, from poppler-utils.

## Provenance

The panels were copied unchanged from the writeup's `svg_src/`, apart from the TODO layers. The
docs also cover arcs on the boundary, so from here on they diverge from the writeup's: edit
these copies, not those.
