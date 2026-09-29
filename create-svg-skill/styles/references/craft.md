# Handmade & illustrative styles

Reference for: Paper Cutout, Hand Drawn / Doodle, Sticker, Children's Illustration, Editorial Illustration, Organic / Botanical.

---

## Paper Cutout {#paper-cutout}

**Layer stack**: `paper-texture (top overlay)` ← `layer-5 (subject)` ← `layer-4` … ← `layer-1 (sky)`. Each layer is a `<g id="layer-N" filter="url(#shadow)">`.

**Design moves**
- 4-6 sheets. Adjacent sheets differ in value by ≥ 15 %.
- Hand-cut edge: author paths with slightly irregular Q-curves; avoid perfect circles; add a few straight scissor facets.
- Same shadow everywhere: `dx 1.5 / dy 2.5 / blur 2 / opacity .3`.

**Recipe**
```svg
<defs>
  <filter id="shadow" x="-10%" y="-10%" width="125%" height="130%">
    <feDropShadow dx="1.5" dy="2.5" stdDeviation="2" flood-color="#3a2a1a" flood-opacity=".3"/>
  </filter>
  <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 .3  0 0 0 0 .25  0 0 0 0 .2  0 0 0 .5 0"/></filter>
</defs>
<g id="layer-2" filter="url(#shadow)"><path d="M0 330 Q90 260 190 310 T400 300 T512 320 V512 H0Z" fill="#8ab17d"/></g>
<rect width="512" height="512" filter="url(#paper)" opacity=".06"/>
```
**QA**: [ ] no gradients [ ] no strokes [ ] one shadow filter reused [ ] ≥ 3 layer groups in back-to-front order

---

## Hand Drawn / Doodle {#hand-drawn-doodle}

**Layer stack**: `paper` → `fills` (offset by 2-4 units) → `hatching` → `ink-lines` → `doodle-fillers`.

**Design moves**
- Wobble comes from *authoring*, not effects: use uneven Q/T control points, let closed shapes overshoot their start point by 2-4 units.
- Fill offset: `<g id="fills" transform="translate(2.5 2)">` under the line layer = instant mis-registration charm.
- Vary `stroke-width` between paths (2-5). Ink is dark blue/brown, not `#000`.

**Recipe - wobbly circle**
```svg
<path d="M120 200 C 118 150, 170 118, 222 126 C 275 134, 300 178, 290 218 C 280 262, 226 288, 178 276 C 138 266, 122 236, 124 204" 
      fill="none" stroke="#1d2433" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
```
Optional ONE `feTurbulence`+`feDisplacementMap` (scale ≤ 2.5) on the entire line group for extra tremor.

**QA**: [ ] round caps/joins everywhere [ ] no perfect circles/straight edges [ ] fills visibly offset [ ] no gradients

---

## Sticker {#sticker}

**Layer stack**: `shadow` → `die-cut border (white)` → `artwork` → `gloss`.

**Recipe - die-cut border from the silhouette**
```svg
<defs>
  <path id="cut" d="…merged silhouette path…"/>
  <filter id="ds" x="-10%" y="-10%" width="125%" height="130%"><feDropShadow dx="2" dy="4" stdDeviation="3" flood-opacity=".25"/></filter>
</defs>
<use href="#cut" fill="#fff" stroke="#fff" stroke-width="14" stroke-linejoin="round" filter="url(#ds)"/>
<!-- artwork here, with 3-4 unit dark interior outlines -->
```
Merge islands (small gaps become bridges) so the border is ONE continuous shape. Transparent background - no canvas rect.

**QA**: [ ] border thickness uniform [ ] no notches [ ] shadow only on the border [ ] no background rect

---

## Children's Illustration {#childrens-illustration}

**Layer stack**: `sky/vignette` → `hills` → `props` → `character` → `soft-glow` → `grain (single overlay)`.

**Design moves**
- Head-to-body ≈ 1:1.5; eyes low and wide-set; cheeks as soft ellipses; no sharp corners.
- Outline colour is warm-dark (`#4a3b52`), 2-3 units, round caps - or no outlines with colour-on-colour details.
- Story details: tiny secondary characters or props reward a second look.

**Recipe - reusable face**
```svg
<g id="face"><ellipse cx="-16" cy="0" rx="5" ry="6" fill="#4a3b52"/><ellipse cx="16" cy="0" rx="5" ry="6" fill="#4a3b52"/>
  <circle cx="-14" cy="-2" r="1.6" fill="#fff"/><circle cx="18" cy="-2" r="1.6" fill="#fff"/>
  <ellipse cx="-26" cy="12" rx="7" ry="4.5" fill="#f4a3a8" opacity=".7"/><ellipse cx="26" cy="12" rx="7" ry="4.5" fill="#f4a3a8" opacity=".7"/>
  <path d="M-6 14q6 6 12 0" fill="none" stroke="#4a3b52" stroke-width="2.4" stroke-linecap="round"/></g>
```
**QA**: [ ] warm palette, no greys [ ] rounded everything [ ] negative space kept for text [ ] ≤ 2 filters

---

## Editorial Illustration {#editorial-illustration}

**First decide the idea** (one sentence: "X is Y") - then draw only what serves it.

**Layer stack**: `background field` → `hero metaphor` (big shape) → `contrast element` (scale surprise) → `accent` → `texture overlays`.

**Recipe - halftone shading via pattern + gradient mask**
```svg
<pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="3" cy="3" r="1.6" fill="#1f3a4d"/></pattern>
<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
<mask id="m"><rect width="512" height="512" fill="url(#fade)"/></mask>
<rect width="512" height="512" fill="url(#dots)" mask="url(#m)"/>
```
**QA**: [ ] concept readable at thumbnail [ ] 3-5 colours + 1 accent [ ] cropping/bleed deliberate [ ] no clip-art literalism

---

## Organic / Botanical {#organic-botanical}

**Layer stack**: `paper` → `stems` → `leaf-back` → `leaf-front` → `blooms` → `veins/details` → `caption`.

**Design moves**
- One leaf symbol, many variants: vary `rotate`, `scale`, and hue slightly with per-`<use>` `fill`.
- Stems are stroked Béziers (round caps); leaves attach at stem points.
- Petal ring = one petal rotated in equal steps.

**Recipe**
```svg
<defs>
  <g id="leaf"><path d="M0 0 C 26-30 26-90 0-130 C -26-90 -26-30 0 0Z"/>
    <path d="M0 0 V-120" fill="none" stroke="#1f3f28" stroke-width="1.2" opacity=".6"/></g>
</defs>
<use href="#leaf" fill="#5f9b58" transform="translate(256 400) rotate(-28) scale(.9)"/>
<use href="#leaf" fill="#7bb26a" transform="translate(256 400) rotate(18) scale(1.05)"/>
```
**QA**: [ ] no two leaves identical [ ] curves have smooth handles (no kinks) [ ] shading is tonal green, not black [ ] ≥ 30 elements
