# SVG craft rules

Every output is genuine, editable, scalable vector. No `<image>` with raster data, ever.

## Skeleton

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 900" role="img" aria-labelledby="t d">
  <title id="t">Red fox on a rock</title>
  <desc id="d">Ukiyo-e style illustration of a fox in front of Mount Fuji.</desc>
  <defs>
    <!-- gradients, patterns, filters, clipPaths, masks, symbols: defined ONCE -->
  </defs>
  <g id="background">…</g>
  <g id="scene">
    <g id="far">…</g><g id="mid">…</g>
  </g>
  <g id="subject">…</g>
  <g id="details">…</g>
  <g id="overlay">…</g>   <!-- texture, vignette, scanlines: last -->
</svg>
```

- `xmlns` always; `viewBox` always; **no fixed width/height** (responsive).
- `<title>` (2-4 word name) + optional `<desc>`.
- Named groups (`id=`) for every semantic part: `background`, `subject`, `ink`, `neon-signs`, `key-block` … The optimiser keeps them.
- Layer order = paint order: background → far → mid → subject → details → overlay.

## Reuse
- Anything appearing ≥ 3 times becomes a `<symbol>`/`<g id>` in `<defs>` and is instanced with `<use href="#id">`. Per-instance differences go on the `<use>` (`transform`, `fill` if the source leaves fill unset, CSS variables).
- Palette as CSS custom properties (`--ink`, `--accent`) *when the style benefits from recolouring*; otherwise plain hex. Remember some converters ignore CSS variables.
- Symmetry: author half, mirror with `<use transform="matrix(-1 0 0 1 W 0)">`.

## Element choice
- Prefer `<path>`, `<rect>`, `<circle>`, `<ellipse>`, `<polygon>`, `<polyline>`, `<line>`.
- Use the simplest primitive that gives the shape (`<circle>` beats a 4-arc path; `<rect rx>` beats a hand-drawn rounded path).
- Paths: absolute commands for readability, relative for compactness in the optimiser; smooth joins need mirrored control handles; use `A` arcs for true circles/pointed arches; close shapes with `Z`.
- Path budget: ≤ ~2000 chars per path in hand-authored art; split by meaning, not by size.
- Precision: 1-2 decimals for a 1000-unit canvas (`optimize_svg.py --precision 2`), 0 for pixel grids.

## Paint servers & effects

| Need | Preferred technique | Filter needed? |
|---|---|---|
| Soft light/glow | `radialGradient` with opacity stops | no |
| Neon halo | second wider stroke at low opacity, or `feGaussianBlur` on a group | only for real blur |
| Drop shadow | offset dark copy with low opacity | only if soft edge required |
| Texture | `<pattern>` tile | no (unless organic noise: `feTurbulence`) |
| Fade-out | `<mask>` with a gradient | no |
| Trim/shape | `<clipPath>` | no |
| Gloss | clipped shape + gradient | no |

Filter rules
- **Do not use a filter when a gradient/stack of shapes gives the same result.**
- Define each filter once; apply to *groups*; set `x/y/width/height` (e.g. `-30% / 160%`) so blurs are not clipped; `color-interpolation-filters="sRGB"` for predictable glow colour.
- Budget: ≤ 3 distinct filters, ≤ ~12 filtered elements.
- `feTurbulence` textures: keep `numOctaves ≤ 3`, apply to one overlay rect at low opacity.

Masks vs clip-paths: clip-path = hard shape trim; mask = luminance/alpha-controlled fade. Both must contain at least one shape (validator errors on empty ones).

Blend modes: `mix-blend-mode: multiply` is fine in browsers but not portable - provide explicit overlap fills for print styles (screen print, riso).

## Text
- Fonts are **not embedded**. Always give a generic fallback (`serif`, `sans-serif`, `monospace`).
- Logos, posters with exact type, and anything for print: convert to paths with `scripts/text_to_path.py` (`--glyphs` gives one path per letter inside `<g aria-label="TEXT">`, which the validator counts as typography), or tell the user text is live and which fonts are assumed.
- Text sits after the art it lives on (z-order) and never under an opaque shape.

## Structure hygiene (what `optimize_svg.py` enforces)
- no comments/editor metadata, no empty groups/defs, no unused defs
- duplicate gradients/filters merged; repeated long paths → `<use>`
- shared presentation attributes hoisted into groups
- bare `<g>` wrappers unwrapped; **named groups preserved**

## Common failure modes
| Symptom | Cause | Fix |
|---|---|---|
| Blank/partial render | missing `viewBox`, broken `url(#id)`, empty `<clipPath>` | run `validate_svg.py` |
| Glow cut off in a box | filter region too small | widen `x/y/width/height` |
| Gradient invisible | `gradientUnits` mismatch or zero-size bbox (horizontal line + objectBoundingBox) | use `userSpaceOnUse` |
| Hairline gaps between tiles | anti-aliased seams | overlap 0.2-0.5 units or same-colour hairline stroke |
| Blurry pixel art | non-integer coords / missing `crispEdges` | integer grid, `shape-rendering="crispEdges"` |
| Text wrong font | font not installed | outline text or use generic fallbacks |
| Huge file | thousands of tiny paths, 6-decimal numbers | simplify, `optimize_svg.py` |
