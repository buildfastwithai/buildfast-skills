# Comics & manga

Reference for: Comic Book, Manga.

---

## Comic Book {#comic-book}

**Layer stack**: `paper` → `flat-colour` → `halftone-shadows` → `ink-line` → `spotted-blacks` → `speed-lines/FX` → `lettering/captions` → `panel-border`.

**Design moves**
- Ink before colour: decide where the blacks go (they anchor the composition), then flat colour, then halftone for shadow.
- Three line weights: contour 4-6, interior 2-3, detail 1. Foreground thick, background thin.
- Mis-registration: offset the colour layer by (1.5, 1) relative to ink.

**Recipe - Ben-Day halftone at 3 densities**
```svg
<defs>
  <pattern id="ht-l" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="4" cy="4" r="1.2" fill="#d81b60"/></pattern>
  <pattern id="ht-m" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="4" cy="4" r="2.0" fill="#d81b60"/></pattern>
  <pattern id="ht-d" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="4" cy="4" r="2.9" fill="#d81b60"/></pattern>
</defs>
<path d="…shadow region…" fill="url(#ht-m)"/>
```
**Recipe - impact burst + outlined SFX**
```svg
<polygon id="burst" points="…alternating radii 90/55, 16 points…" fill="#ffd60a" stroke="#111" stroke-width="5" stroke-linejoin="miter"/>
<text x="256" y="270" text-anchor="middle" font-family="Impact, 'Arial Black', sans-serif" font-size="72"
      fill="#e63946" stroke="#111" stroke-width="6" paint-order="stroke" transform="rotate(-8 256 256)">POW!</text>
```
**QA**: [ ] ≥ 2 stroke widths [ ] ≥ 1 halftone `<pattern>` [ ] blacks are *shapes* (not just thick lines) [ ] no gradients [ ] dynamic angle/cropping

---

## Manga {#manga}

**Layer stack**: `paper` → `screentone regions` → `solid-black shadows` → `ink-lines (tapered)` → `effect lines` → `speech/SFX` → `panel frame`.

**Design moves**
- Contours are *tapered filled paths* (thick on shadow side, hairline at highlights), not uniform strokes. Simulate with 2 layers if needed: a 3-unit stroke + a thinner paper-coloured stroke offset on the lit side.
- Hair as flowing clumps with highlight gaps left as paper.
- Focus/speed lines: many `<line>`s radiating from a point, varying length and weight, clipped to the panel.
- Colour pages: keep cel colours flat with a single cool shadow tone.

**Recipe - screentone set**
```svg
<pattern id="tone-20" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="2" cy="2" r=".55" fill="#111"/></pattern>
<pattern id="tone-50" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="2" cy="2" r="1.1" fill="#111"/></pattern>
<pattern id="tone-70" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><circle cx="2" cy="2" r="1.6" fill="#111"/></pattern>
```
**Recipe - radial focus lines**
```svg
<g stroke="#111" stroke-linecap="round" clip-path="url(#panel)">
  <line x1="256" y1="256" x2="256" y2="-20" stroke-width="2"/> <!-- repeat with rotate(i*7.5 256 256), vary length + width -->
</g>
```
**QA**: [ ] ≥ 2 stroke widths [ ] ≥ 1 screentone pattern [ ] ≤ 10 colours (mostly B/W) [ ] no gradient shading [ ] eyes/face have the strongest contrast
