# Print & street styles

Reference for: Screen Print, Risograph, Graffiti / Street Art.

---

## Screen Print {#screen-print}

**Layer stack**: `paper` → `ink-1 (lightest)` → `ink-2` → `ink-3` → `ink-black (key)` → `overprints` → `speckle/halftone`.

**Design moves**
- Choose the ink set first (3-5) and *compute the overprint colours* (e.g. yellow over cyan → green) - paint those overlaps as explicit fills.
- Every ink is one `<g id="ink-…">`; offset the key layer by (0.5-1.5, 0.5-1) for mis-registration.
- Tone = halftone dots or line screens, not gradients.

**Recipe - overprint area**
```svg
<clipPath id="ov"><circle cx="220" cy="240" r="120"/></clipPath>
<circle cx="220" cy="240" r="120" fill="#f2b134"/>          <!-- ink A -->
<circle cx="300" cy="240" r="120" fill="#2a4dab"/>          <!-- ink B -->
<circle cx="300" cy="240" r="120" fill="#2a5f45" clip-path="url(#ov)"/>  <!-- overprint (A×B) -->
```
**Recipe - ink dropout speckle** (apply to ONE ink group)
```svg
<filter id="speck"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="2" result="n"/>
  <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -9 5.2" result="m"/>
  <feComposite in="SourceGraphic" in2="m" operator="in"/></filter>
```
**QA**: [ ] ≤ 6 inks, no gradients [ ] overprints painted explicitly [ ] mis-registration visible but modest [ ] ≥ 3 ink groups

---

## Risograph {#risograph}

**Layer stack**: `paper (#f4efe4)` → `ink-1 (fluoro pink)` → `ink-2 (blue)` → `ink-3 optional` → `grain overlay`.

**Design moves**
- 2-3 inks max. The overprint of pink + blue makes the deep purple - use it deliberately for shadows.
- Gradients = *grain gradients* (dots that thin out), never smooth.
- Everything slightly off-register (1-3 units).

**Recipe - grain gradient fill** (dots that thin out; no smooth gradient)
```svg
<defs>
  <pattern id="grain" width="3" height="3" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r=".8" fill="#ff48b0"/></pattern>
  <linearGradient id="fadeg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
  <mask id="grainmask"><rect width="512" height="512" fill="url(#fadeg)"/></mask>
</defs>
<rect x="60" y="60" width="392" height="392" fill="url(#grain)" mask="url(#grainmask)"/>
```
Overprint: `style="mix-blend-mode:multiply"` on each ink group, **plus** explicit overlap fills as fallback for renderers without blend support.

**QA**: [ ] ≤ 3-4 inks [ ] ≥ 1 grain/halftone pattern [ ] paper is off-white (never `#fff`) [ ] no smooth gradients

---

## Graffiti / Street Art {#graffiti-street-art}

**Layer stack**: `wall texture (brick/concrete)` → `grime` → `letter extrusion (dark offset)` → `letter fill (gradient)` → `outline black` → `inner highlight` → `drips` → `sparkles/arrows/crowns` → `overspray`.

**Design moves**
- Letters are **drawn paths** (bubbly, overlapping), not `<text>`. Build each with 4 stacked copies: extrusion, fill, black outline, white inner line.
- Drips: tapered vertical paths ending in a round blob; place under letter bottoms.
- Wall: brick `<pattern>` with 3 slightly different brick fills.

**Recipe - letter stack via `<use>`**
```svg
<defs><path id="L" d="…bubble letter path…"/></defs>
<use href="#L" transform="translate(6 8)" fill="#3a1f5a"/>                                   <!-- extrusion -->
<use href="#L" fill="url(#spray)" stroke="#111" stroke-width="8" stroke-linejoin="round"/>    <!-- fill + outline -->
<use href="#L" fill="none" stroke="#fff" stroke-width="2" transform="translate(-2 -2)" opacity=".8"/>  <!-- highlight -->
<path d="M180 340 v46 q0 8 6 0 v-46" fill="#ff2e93"/>                                          <!-- drip -->
```
**QA**: [ ] ≥ 2 stroke widths [ ] gradient/spray fade present [ ] wall texture present [ ] no real artist signatures/tags copied
