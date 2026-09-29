# East Asian traditions

Reference for: Japanese Ink / Sumi-e, Ukiyo-e.

> These are **visual languages, not palettes**. Recolouring a generic illustration with "Japanese colours" is a failure. Follow the construction below: it is what makes the result read as the tradition.

---

## Japanese Ink / Sumi-e {#sumi-e}

**Layer stack**: `paper` → `far mountains (pale wash)` → `mist bands` → `mid masses (grey wash)` → `subject strokes (black, dry brush)` → `accents (thin lines)` → `seal`.

**Design moves**
1. **Ma (negative space)** first: decide where nothing happens. The subject takes ≤ 40 %.
2. Draw with *brush shapes* - closed variable-width paths, not uniform strokes. A bamboo stalk = tall tapered shape with node gaps; a mountain = irregular soft mass.
3. Five ink tones: `#1a1a1a`, `#4a4a48`, `#8c8a84`, `#c9c5b8` + paper. Dark near / pale far.
4. One red seal, lower corner, opposite the main mass.

**Recipe - wet wash with halo + dry brush**
```svg
<defs>
  <filter id="wet" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter>
  <pattern id="bristle" width="200" height="6" patternUnits="userSpaceOnUse">
    <rect width="200" height="6" fill="#fff"/>
    <path d="M0 1h60M80 1h120 M0 3h140M160 3h40 M20 5h90M130 5h70" stroke="#000" stroke-width="1.2"/></pattern>
  <mask id="dry"><rect width="512" height="512" fill="url(#bristle)"/></mask>
  <linearGradient id="mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4eddc" stop-opacity="0"/><stop offset="1" stop-color="#f4eddc" stop-opacity=".9"/></linearGradient>
</defs>
<path id="mountain" d="…soft irregular mass…" fill="#8c8a84"/>
<use href="#mountain" fill="#8c8a84" opacity=".5" filter="url(#wet)"/>       <!-- wet halo -->
<path d="…tapered brush stroke…" fill="#1a1a1a" mask="url(#dry)"/>            <!-- dry brush -->
<rect y="300" width="512" height="90" fill="url(#mist)"/>                     <!-- mist band -->
<g id="seal" transform="rotate(-4 440 450)"><rect x="420" y="430" width="40" height="40" rx="2" fill="#c1272d"/>
  <path d="M430 442h20M440 442v20M432 456h16" stroke="#f4eddc" stroke-width="3" stroke-linecap="square"/></g>
```
**QA**: [ ] palette = paper + ink tones + one seal [ ] ≥ 60 % empty paper [ ] asymmetric [ ] brush shapes vary in width [ ] no outlines around washes

---

## Ukiyo-e {#ukiyo-e}

**Layer stack** (mirrors real print production):
1. `paper` (warm cream)
2. `colour-blocks` - one `<g>` per pigment block (blue, ochre, green, red, ...), **no outlines**
3. `bokashi` - gradient limited to sky/horizon via clip-path
4. `patterns` - waves (seigaiha), clouds, kimono motifs as `<pattern>`/`<use>`
5. `key-block` - the sumi outline layer, offset by (0.8, 0.6) for mis-registration
6. `texture` - wood-grain overlay (horizontal-stretched turbulence, ~6 %)
7. `cartouche + seal` - title box top corner, small red seal

**Design moves**
- Flat perspective: stack planes, overlap, crop the foreground element at one frame edge.
- Outline weights: 3 units exterior contours, 1-1.4 interior; round caps and joins; slight irregularity.
- Waves: curling crests with claw-like foam fingers; concentric-arc pattern for the water field.
- Limit to 8-12 colours from the pigment set: Prussian blue, pale indigo, vermilion, ochre, muted green, sumi, cream.

**Recipe - seigaiha (wave) pattern**
```svg
<pattern id="seigaiha" width="48" height="24" patternUnits="userSpaceOnUse">
  <g fill="none" stroke="#1f3c6e" stroke-width="1.4">
    <circle cx="0"  cy="24" r="24"/><circle cx="0"  cy="24" r="17"/><circle cx="0"  cy="24" r="10"/>
    <circle cx="48" cy="24" r="24"/><circle cx="48" cy="24" r="17"/><circle cx="48" cy="24" r="10"/>
    <circle cx="24" cy="12" r="24"/><circle cx="24" cy="12" r="17"/><circle cx="24" cy="12" r="10"/>
  </g>
</pattern>
```
**Recipe - wood-grain overlay**
```svg
<filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".002 .22" numOctaves="3" seed="7"/>
  <feColorMatrix type="matrix" values="0 0 0 0 .25  0 0 0 0 .18  0 0 0 0 .1  0 0 0 .9 -.25"/>
</filter>
<rect width="512" height="512" filter="url(#grain)" opacity=".18"/>
```
**Recipe - bokashi sky (only here)**
```svg
<linearGradient id="bokashi" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1f3c6e"/><stop offset=".7" stop-color="#6d8fb3"/><stop offset="1" stop-color="#efe3c8"/></linearGradient>
```
**QA**: [ ] colour blocks contain no strokes; outlines live in `#key-block` [ ] ≤ 12 colours, gradients only in the sky [ ] ≥ 1 `<pattern>` (water/cloud/cloth) [ ] cartouche + seal present [ ] no cast shadows/glow [ ] no vanishing-point perspective
