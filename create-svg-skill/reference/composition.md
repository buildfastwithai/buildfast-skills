# Composition intelligence

Decide composition **before** writing any SVG. Write a 6-10 line design brief (see the template at the bottom), then draw.

## 1. Pick the canvas

| Asset | viewBox | Notes |
|---|---|---|
| Icon | `0 0 64 64` or `0 0 24 24` | keep 2-4 % padding; stroke 2-3 units at 24 |
| Logo / mark | `0 0 512 512` | square; centre with optical correction; must work in one colour |
| Illustration / scene | `0 0 1200 900` (4:3) or `0 0 1024 1024` | choose 16:9 (`1600 900`) for cinematic |
| Character / sticker | `0 0 1024 1024` | transparent background |
| Poster | `0 0 900 1350` (2:3) | margins ≥ 6 % |
| Infographic | `0 0 1000 1400` (or as long as the content needs) | 12-column mental grid |
| Pixel art | grid size (`0 0 32 32`, `0 0 64 64`, `0 0 128 72`) | integer scaling only |
| Pattern tile | `0 0 200 200` | edges must wrap |

Never set fixed `width`/`height` on `<svg>` unless asked: `viewBox` alone keeps the file responsive.

## 2. Illustrations & scenes
- **Focal point**: one. Decide it, then put the highest contrast, the sharpest detail and the most saturated colour there.
- **Planes**: foreground (large, dark or framing), middle ground (subject), background (small, light, low contrast). State them in the brief.
- **Silhouette**: fill the subject with a single colour mentally - if it does not read, redesign the pose.
- **Balance**: asymmetric balance via scale/colour weight; keep the visual centre of mass within ~15 % of the centre unless deliberately off-balance.
- **Negative space**: reserve it on purpose (for text, for breathing, for the eye's path).
- **Hierarchy**: 1 hero, 2-3 supporting, everything else quiet. Cap the number of distinct scales.
- **Eye path**: lay out a route (leading lines, gaze direction, light path) from entry point → focal point.
- **Scale**: subject fills 55-75 % of the canvas (validator warns < 30 %).

## 3. Icons
- Optical alignment beats mathematical alignment (circles overshoot squares by ~3 %).
- One stroke weight, one corner radius, one cap/join policy.
- Padding ≥ 4 %; must remain recognisable at 24 px - render at that size to check.
- Silhouette recognition first, detail second. Test in solid black.

## 4. Logos
- Simple, memorable, geometric consistency (shared radii/angles, shared stroke).
- Use negative space deliberately (the classic hidden-shape idea).
- Monochrome must work: check by rendering with `convert_svg.py recolor --grayscale`.
- Convert text to paths (fonts are not embedded) and keep the mark ≤ 3 colours.
- Deliver the mark alone plus optional lock-up with wordmark; both scalable.

## 5. Posters
- Hierarchy: **title → focal image → tagline → supporting info**. Title ≥ 2× the size of the second level.
- Margins ≥ 6 %; align text to a shared edge or the centre axis.
- Rhythm: repeat a shape/colour at three scales to move the eye.
- Cinematic: low horizon or dramatic diagonal, light source that creates a path, foreground framing.
- Text is `<text>` with generic fallbacks *or* outlined paths when exact typography matters - say which in the reply.

## 6. Infographics
- Reading order first (Z or F pattern), then modules on a grid.
- Group by proximity, separate with whitespace, not lines.
- Consistent visual grammar: one icon style, one chart style, one label style.
- Compute geometry from data; label everything; never fabricate numbers (use clearly marked placeholder data).

## 7. Design-brief template (write it, keep it in your head or in a comment)

```
SUBJECT     : red fox, seated, three-quarter view, looking left
STYLE       : ukiyo-e (primary)   MODIFIERS: darker
CANVAS      : 0 0 1200 900, subject fills ~60%, focal point at (600, 380)
PLANES      : fg = cropped pine branch top-right / mid = fox on rock / bg = Fuji + bokashi sky
LIGHT       : no cast light; contrast via indigo vs cream fur
PALETTE     : cream #efe3c8, prussian #1f3c6e, vermilion #c8372d, ochre #d9a441, sumi #1c1a19
DETAILS     : seigaiha water pattern, cartouche top-left with red seal
LAYERS      : paper > colour-blocks > bokashi > patterns > key-block > texture > cartouche
CHECKS      : validate --style ukiyo-e ; render 1024 ; inspect focal point + edges
```
