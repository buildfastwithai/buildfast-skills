# Pixel & retro-game styles

Reference for: Pixel Art, Retro 8-bit, Retro 16-bit.

**Universal pixel workflow (all three)**
1. Decide the grid (e.g. 32×32) and the palette *before* drawing.
2. Author the sprite as ASCII → `scripts/pixel_grid.py` → merged `<path>` per colour (integer coordinates, `shape-rendering="crispEdges"`, `viewBox` = grid size).
3. Compose scenes by concatenating grids (or several `pixel_grid.py` outputs as `<g>` with integer `translate`).
4. Validate: `validate_svg.py file.svg --style pixel-art` → no curves, no gradients, integer coords, colour budget.
5. Render with `render_svg.py --analyze` and check `top32_share_pct ≈ 100` (no anti-aliasing leaks).

**Sprite file format** (see `pixel_grid.py --help`)
```text
@k=#1a1423        ; outline
@o=#e8702a        ; fur
@w=#fdf0d5        ; cream
..kk......kk..    ; '.' = transparent
.kook....kook.
```
Use `--mirror` when only the left half is typed, `--outline "#1a1423"` for an automatic 1-cell outline, `--pad 2 --bg "#..."` for a framed tile.

---

## Pixel Art {#pixel-art}

**Layer stack**: `background` (flat or dithered) → `ground` → `shadow` (dithered ellipse) → `sprite` (outline, base, shade, highlight) → `fx`.

**Design moves**
- Silhouette first: fill the shape in one colour; it must be recognisable.
- Hue-shift ramps: shade → cooler/more purple, highlight → warmer/more yellow.
- Selective outline: outer outline dark, interior contours the darker tone of the neighbouring fill.
- Clusters, not noise. Avoid "jaggies" (single-pixel steps in an otherwise smooth curve) and "banding" (parallel 1-px ramps).
- Curves are staircases with run-lengths that step monotonically: 1-1-2-3-… or 3-2-1-1 (never 2-1-2).

**Recipe - Bayer 2×2 dither as pattern** (keeps integer geometry)
```svg
<defs>
  <pattern id="dither" width="2" height="2" patternUnits="userSpaceOnUse">
    <rect width="1" height="1" fill="#6b4a8e"/><rect x="1" y="1" width="1" height="1" fill="#6b4a8e"/>
  </pattern>
</defs>
<rect x="0" y="20" width="32" height="6" fill="url(#dither)"/>
```
> Rects with integer coordinates are the **only** allowed primitives (plus `<path>` using M/L/H/V/Z with integer values). Patterns of rects are fine.

**Sizes** 16² icon · 32² character · 64² detailed sprite · 128×72 scene. Scale by integer factors only (viewBox stays in grid units, so browsers scale it exactly).

**QA checklist**
- [ ] `shape-rendering="crispEdges"` on root
- [ ] No `<circle>`, `<ellipse>`, curves, gradients, filters, strokes
- [ ] ≤ ~24 colours, one shared outline colour (not pure black)
- [ ] Rendered analysis: `top32_share_pct` ≥ 99

---

## Retro 8-bit {#retro-8bit}

*Extends Pixel Art - everything above applies, with tighter limits.*

**Layer stack**: `sky-band` → `parallax-far` → `ground-tiles` → `sprite` → `hud`.

**Design moves**
- Max **3 colours + transparent per sprite**, ≤ 16 in the scene, from ONE hardware-style palette.
- 8×8 tile logic: backgrounds are repeated tiles (brick, grass, water) - draw one tile, tile it with `<pattern>` of integer size.
- No dithering except a two-tone checker on water/brick tiles. Bold 1-px outlines.

**Palettes** (pick one)
| Look | Colours |
|---|---|
| NES-like | `#000000 #fcfcfc #bcbcbc #f83800 #0058f8 #00a800 #fca044 #503000` |
| Game Boy | `#0f380f #306230 #8bac0f #9bbc0f` |
| C64-like | `#000000 #ffffff #883932 #67b6bd #8b5429 #b8c76f #40318d` |

**Recipe - HUD text from cells**: draw each glyph in a 5×7 sprite with `pixel_grid.py`, place glyphs at 6-cell intervals.

**QA checklist**
- [ ] Palette comment lists the exact hardware-style colours used
- [ ] Every sprite ≤ 3 visible colours
- [ ] Scene ≤ 16 colours

---

## Retro 16-bit {#retro-16bit}

*Extends Pixel Art.*

**Layer stack**: `sky (dithered gradient bands)` → `far` → `mid` → `near` → `sprites` → `glow rings` → `ui-frame`.

**Design moves**
- Ramps of 4-5 per material; distant parallax layers are tinted toward the sky colour (atmospheric perspective).
- Sky gradient = 6-10 hard bands separated by a 2-row Bayer dither transition.
- Glow = concentric hard-edged rings at stepped colours (never blur).
- Add specular pixels on metal and eyes; rim-light one edge of the hero.

**Recipe - dithered band transition**
```svg
<defs>
  <pattern id="d2" width="2" height="2" patternUnits="userSpaceOnUse">
    <rect x="0" y="0" width="1" height="1" fill="#3b2a6b"/><rect x="1" y="1" width="1" height="1" fill="#3b2a6b"/></pattern>
</defs>
<rect width="128" height="12" fill="#1b1035"/>
<rect y="12" width="128" height="2" fill="url(#d2)"/>
<rect y="14" width="128" height="12" fill="#3b2a6b"/>
```

**QA checklist**
- [ ] ≤ ~32 colours, ramps hue-shifted
- [ ] Parallax layers separable (`<g id="far|mid|near">`)
- [ ] No blur/gradient - glows are stepped rings
