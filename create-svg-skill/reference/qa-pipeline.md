# Quality-control pipeline

Run this loop after **every** SVG you write. Passing the parser is not "done" - visual quality is.

```
write → validate → optimise → validate again → render → LOOK → fix → (repeat) → deliver
```

## Commands

```bash
S=.claude/skills/create-svg/scripts        # adjust to where the skill lives

python3 $S/validate_svg.py art.svg --style <style-id>          # 1-10 (+ style conformance)
python3 $S/optimize_svg.py art.svg --in-place                  # 10 (add --precision 0 for pixel art)
python3 $S/validate_svg.py art.svg --style <style-id> --quiet  # re-check after optimisation
python3 $S/render_svg.py art.svg -o /tmp/preview.png -w 1024 --analyze   # 11
# then open /tmp/preview.png with the Read tool and LOOK at it                # 12
```
Sheets: `render_svg.py a.svg b.svg c.svg --sheet compare.png --cols 3`.

## The 12 checks

| # | Check | How |
|---|---|---|
| 1 | Valid SVG syntax | `validate_svg` (`xml-syntax`, `xmlns`, `root`) |
| 2 | Broken references | `broken-url-ref`, `broken-href`, `duplicate-id` |
| 3 | `viewBox` | `viewbox` (missing/invalid → error) |
| 4 | Important content not clipped | `clipped`, `off-canvas`, `tight-margin`, `small-subject`; render `edge_touch` |
| 5 | Layering / z-order | `z-background`, `z-cover`, `z-hidden` (incl. text hidden behind shapes) |
| 6 | Accidental invisible objects | `invisible`, `zero-size` |
| 7 | Gradients, masks, filters work | `gradient-stops`, `empty-clippath`, `empty-mask`, `empty-filter`, `filter-input`, `filter-region` |
| 8 | Matches the requested style | `--style <id>` (style checks) **and your eyes against the brief's checklist** |
| 9 | Balance & spacing | stats `content_margins_pct`, `weight_offset_pct`, render `ink_balance_*`, plus looking |
| 10 | Optimised | `optimize_svg.py`; validator `precision`, `duplicate-geometry`, `huge-path`, `size` |
| 11 | Preview rendered | `render_svg.py` (headless Chromium) |
| 12 | Rendered result inspected | Read the PNG; use the checklist below |

Severity: **error** = must fix. **warn** = fix unless you can justify it (say why in the reply). **info** = consider.

## Looking at the render - what to check

Take the PNG and answer honestly:
1. **Squint test**: blur your eyes - is there one clear focal point and a readable silhouette?
2. **Style test**: would someone name the style without being told? Check the brief's *signature techniques* are all visibly present (e.g. ukiyo-e: flat blocks + key-block outline + pattern + cartouche; pixel art: crisp grid, no soft edges; cyberpunk: dark base + glow on hero edges).
3. **Clipping**: nothing cut by the canvas unless it is deliberate bleed.
4. **Edges/quality**: jagged joins, gaps between shapes, wobbly geometry that should be exact, mis-aligned mirrored halves.
5. **Balance**: is the weight sensible? are margins even? is there dead space that looks accidental?
6. **Legibility**: text readable at the intended size; contrast OK.
7. **Polish**: does it look *designed* or *assembled*? Look for the "few rectangles and circles" trap - add layered detail, secondary forms, texture appropriate to the style.

Render at more than one size when relevant (`-w 128` for icons/logos, `-w 1600` for detail).

## Analysis fields (`--analyze`)
`blank` (nothing drawn) · `alpha_coverage_pct` · `content_bbox_pct` / `edge_touch` (transparent art) · `subject_bbox_pct` / `subject_edge_touch` / `subject_fill_pct` (full-bleed art) · `rendered_colors`, `top32_share_pct` (≈100 for crisp pixel art; lower means anti-aliasing leaks) · `mean_luma`, `contrast` (is it as dark/high-contrast as the style demands?) · `ink_balance_lr_pct` / `_tb_pct` (0 = balanced).

## Iteration rules
- Fix in priority: errors → clipping/z-order → style mismatch → composition → polish.
- After each fix re-run validate + render. Stop when: 0 errors, no unexplained warnings, the render passes the looking checklist, and you would be comfortable putting it in a portfolio.
- Max ~4 loops per file; if still off, say precisely what remains and why (don't loop forever).
- If Chromium/rendering is unavailable: say so, rely on validator + careful reasoning, and mark the visual inspection as **not performed**.

## Common defects → fixes
| Defect | Fix |
|---|---|
| `dark-base` / `light-base` warning | change the background/base fill; dark styles need a dark first layer |
| `min-gradients`, `min-filters` | add the style's signature lighting (glow, gloss, metal) |
| `forbid-*` | replace the technique with the style-legal alternative (see the brief) |
| `z-hidden` (info) | remove wasted shape or reorder |
| `small-subject` | tighten the viewBox or scale the subject group |
| pixel art `curves` / `grid` | rebuild from ASCII via `pixel_grid.py` |
| Too plain | add mid-ground detail, secondary forms, pattern/texture, atmosphere, rim light, props - as the style dictates |
