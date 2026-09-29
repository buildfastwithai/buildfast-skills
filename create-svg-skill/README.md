# SVG Style Studio  -  `/create-svg`

A Claude Code skill that turns "draw X in style Y" into polished, editable, **genuine vector** SVG - then proves it looks right by validating, optimising, rendering and looking at the result.

- 44 styles across 10 families, each a full visual language (geometry, line, palette, texture, light, composition, typography) with machine-checkable conformance rules
- natural-language routing ("8 bit", "Japanese woodblock"), modifiers ("but darker"), blends ("cyberpunk + minimalist"), multi-style sets, and SVG conversion
- a 12-point QC pipeline backed by scripts (validator, optimiser, headless-Chromium renderer)

## Install

The skill's id is **`create-svg`**, so once installed anyone can type `/create-svg ...`.

- Claude Code, project: copy this folder to `<repo>/.claude/skills/create-svg/`
- Claude Code, personal: `~/.claude/skills/create-svg/`
- Claude apps: upload the zip of this folder as a skill
Requirements: Python 3.9+, `lxml`, `Pillow`; rendering needs `playwright` with Chromium (validate/optimise/route work without it, and the skill then reports that the visual check was not performed).

## Use

Type `/create-svg` followed by what you want (or just ask for SVG art - the skill triggers on its own):

```
/create-svg a fox in pixel art
/create-svg                              # asks what to draw + shows the style menu
A fox in pixel art
Ukiyo-e but darker: a heron by a river
cyberpunk + minimalist logo for a coffee brand
Create a lighthouse in 5 styles
Convert this SVG to cyberpunk
```
More in [`examples/example-prompts.md`](examples/example-prompts.md). No style given for a single artwork -> it shows a menu and asks.

## Layout

```
SKILL.md                 workflow + rules (kept short; loaded first)
scripts/
  route_style.py         NL -> mode, styles, modifiers, asset, blend plan, style brief(s); --menu --list --show --lint
  validate_svg.py        syntax, refs, viewBox, clipping, z-order, invisible, gradients/masks/filters, --style conformance
  optimize_svg.py        cruft strip, precision, path re-serialise, dedupe defs, <use>, hoist attrs, unused defs
  render_svg.py          headless-Chromium PNG, contact sheets, --analyze (coverage, colours, contrast, balance)
  pixel_grid.py          ASCII sprite -> crisp merged-rect SVG
  text_to_path.py        outline lettering from any .ttf/.otf/.woff2 (logos, posters: no font dependency)
  convert_svg.py         inspect | recolor | strokes | inject  (convert mode)
  new_style.py           scaffold a new style
  svgtools.py            shared parsing / geometry helpers
styles/
  registry/*.json        one file per family; the source of truth for every style
  references/*.md        per-style recipes, layer stacks, QA checklists (anchors = style ids)
  modifiers.json         darker, minimalist, realistic, modern-palette, ...
reference/               composition.md, svg-craft.md, modes.md, qa-pipeline.md
examples/                outputs/ (finished SVGs + fox-styles.png), src/ (generators + pixel sprite), example-prompts.md
```

Progressive disclosure: `SKILL.md` -> router prints only the matched style briefs -> `styles/references/<family>.md#<id>` and `reference/*.md` are read when needed.

## Styles (44)

core-modern: minimal-modern, flat-design, geometric, monochrome, luxury-premium - pixel-retro: pixel-art, retro-8bit, retro-16bit - digital-glossy: cyberpunk-neon, y2k, frutiger-aero, glassmorphism, clay-soft-3d, isometric, low-poly - craft: paper-cutout, hand-drawn-doodle, sticker, childrens-illustration, editorial-illustration, organic-botanical - comics: comic-book, manga - east-asian: sumi-e, ukiyo-e - decorative-eras: art-nouveau, art-deco, bauhaus, brutalist, vintage-poster, medieval-manuscript, gothic - print: screen-print, risograph, graffiti-street-art - technical: blueprint, technical-illustration, scientific-illustration, infographic - genre: cinematic-poster, fantasy, sci-fi, horror, retro-futurism

## Add a style (3 steps)

```bash
# 1. scaffold registry entry + reference stub (TODO-filled)
python3 scripts/new_style.py --id vaporwave --name "Vaporwave" --family genre \
    --alias "vapor wave" --alias "vaporwave aesthetic" --description "..." --best-for illustration,poster
python3 scripts/new_style.py --checks        # list machine checks you can use

# 2. fill every TODO in styles/registry/genre.json and write the recipe in styles/references/genre.md
#    (palette, geometry, stroke, texture, composition, svg_techniques, avoid, checks, compatible/conflicts)

# 3. lint - must report 0 errors
python3 scripts/route_style.py --lint
python3 scripts/route_style.py "vaporwave dolphin" --no-brief     # confirm routing
```
Use `weak_aliases` for common words that should only match with style context (e.g. "luxury", "futuristic"). Add a modifier by appending a row to `styles/modifiers.json`.

## QC pipeline

```bash
python3 scripts/validate_svg.py art.svg --style <id>        # errors must be 0; --strict fails on warnings too
python3 scripts/optimize_svg.py art.svg --in-place           # --precision 0 for pixel grids
python3 scripts/render_svg.py art.svg -o preview.png -w 1024 --analyze   # then LOOK at preview.png
```
Full checklist: `reference/qa-pipeline.md`.

## Examples (`examples/outputs/`)

**One fox, 15 styles** (same frozen scene spec, see `fox-styles.png`): `fox.svg` (flat base) · `fox-pixel-art` · `fox-ukiyo-e` · `fox-ukiyo-e-darker` (modifier demo) · `fox-cyberpunk-neon` · `fox-paper-cutout` · `fox-blueprint` · `fox-low-poly` · `fox-risograph` · `fox-comic-book` · `fox-sticker` · `fox-sumi-e` · `fox-horror` · `fox-bauhaus` · `fox-art-nouveau`

**Other formats** (see `showcase-more.png`):

| File | Style | Notes |
|---|---|---|
| `logo-art-deco-hotel.svg` | art-deco | logo; lettering outlined with `text_to_path.py` |
| `poster-vintage-highlands.svg` | vintage-poster | portrait poster, outlined title |
| `ship-pixel-art.svg` | pixel-art | mirrored sprite via `pixel_grid.py --mirror` |
| `island-isometric.svg` | isometric | generated axonometric boxes |
| `landscape-low-poly.svg` | low-poly | Delaunay mesh, facet shading |

Every file passes `validate_svg.py --style <id> --strict`. Generators: `examples/src/make_fox_set.py`, `make_showcase.py`, `make_logo_poster.py`, sprites `fox-pixel.txt`, `ship-pixel.txt`; fonts in `examples/src/fonts/` are OFL (Anton, Instrument Serif, Space Grotesk, Unbounded).

## Limitations (honest list)

- **Fonts are not embedded.** Live `<text>` uses the viewer's fonts; outline lettering with `scripts/text_to_path.py` (needs a font file + fontTools) for logos, posters and print. Wordmark widths are pinned with `textLength` so layout survives font substitution, but letterforms will differ.
- **The validator is static.** Bounding boxes are approximate (curves sampled, text estimated, `clipPath` extents handled for simple shapes only, filters' visual spread not modelled). Treat clipping warnings as hints and confirm on the render.
- **Rendering needs Playwright + Chromium.** Without it the visual inspection is not performed and the skill must say so. Other renderers (Inkscape, resvg) may differ on filters, `mix-blend-mode`, CSS variables and `textLength`.
- **Raster inputs are redrawn, not traced**; conversion of messy traced SVGs preserves structure only as far as the source has any.
- **Style quality is execution-dependent.** The registry and checks constrain and detect, but a convincing ukiyo-e or art nouveau still needs the drawing done with care; expect 1-3 QA iterations on complex subjects.
- Style checks catch technique violations (curves in pixel art, gradients in flat design), not taste.
- Trademarked characters, real people and living artists' specific work are declined in favour of original designs in the requested style.
