# Historic & decorative movements

Reference for: Art Nouveau, Art Deco, Bauhaus, Brutalist, Vintage Poster, Medieval Manuscript, Gothic.

---

## Art Nouveau {#art-nouveau}

**Layer stack**: `ground` → `halo/arch panel` → `border ornament` → `subject` (flat colour) → `pattern fills` → `contour lines` → `lettering panels`.

**Design moves**
- One dominant S-curve carries the eye through the piece (hair → stem → border).
- Contour lines taper: draw each as a filled path, or two strokes (dark 3 + lighter 1.2 offset).
- Frame = arch + inner offset arch; flowers overlap the frame to integrate it with the subject.

**Recipe - arched double frame**
```svg
<path d="M80 470 V210 A176 176 0 0 1 432 210 V470Z" fill="#efe2c0" stroke="#2c2a25" stroke-width="3"/>
<path d="M98 452 V212 A158 158 0 0 1 414 212 V452Z" fill="none" stroke="#c8a24a" stroke-width="1.5"/>
```
**Recipe - tendril (smooth handles)**
```svg
<path d="M256 470 C 210 400, 300 340, 250 280 S 200 170, 262 120" fill="none" stroke="#3f6b5e" stroke-width="4" stroke-linecap="round"/>
```
**QA**: [ ] no straight lines except architecture [ ] ≥ 2 stroke widths, round caps [ ] muted palette (no neon) [ ] frame integrated with subject

---

## Art Deco {#art-deco}

**Layer stack**: `black/emerald ground` → `sunburst rays` → `stepped frame` → `central motif` → `gold hairline sets` → `title lettering`.

**Design moves**
- Draw the **left half only**, mirror with `<use transform="matrix(-1 0 0 1 W 0)">` for perfect symmetry.
- Triple rules: three parallel gold lines, 1-2.5 wide with 3-4 gaps.
- Chamfer corners (45° cuts) instead of rounding.

**Recipe - sunburst + mirrored half**
```svg
<defs>
  <path id="ray" d="M0 0 L-9 -230 L9 -230Z"/>
  <linearGradient id="gold" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
    <stop offset="0" stop-color="#8c6a1a"/><stop offset=".4" stop-color="#f3dd8b"/><stop offset=".7" stop-color="#c9a227"/><stop offset="1" stop-color="#f3dd8b"/></linearGradient>
  <g id="half"> … left half art … </g>
</defs>
<g transform="translate(256 300)" fill="url(#gold)">
  <use href="#ray" transform="rotate(-70)"/><use href="#ray" transform="rotate(-50)"/><!-- every 20deg -->
</g>
<use href="#half"/><use href="#half" transform="matrix(-1 0 0 1 512 0)"/>
```
**QA**: [ ] exact bilateral symmetry [ ] gold is a gradient [ ] miter joins, butt/square caps [ ] no rounded corners [ ] ≤ 6 colours

---

## Bauhaus {#bauhaus}

**Layer stack**: `off-white ground` → `large primary shape` → `overlapping secondary shapes` → `black bars/rules` → `rotated type`.

**Design moves**
- Grid unit U; big red circle, blue rectangle, yellow triangle, black bar - then move things until the *tension* is right (asymmetric, diagonal).
- Overlap by explicit intersection colours (black) not transparency.

**Recipe - half circle + intersection**
```svg
<path d="M90 300 A110 110 0 0 1 310 300Z" fill="#d62828"/>
<rect x="200" y="180" width="200" height="120" fill="#1d4e9f"/>
<clipPath id="i"><path d="M90 300 A110 110 0 0 1 310 300Z"/></clipPath>
<rect x="200" y="180" width="200" height="120" fill="#111" clip-path="url(#i)"/>  <!-- intersection -->
<text x="60" y="430" font-family="Futura, 'Century Gothic', sans-serif" font-weight="700" font-size="40" transform="rotate(-90 60 430)">BAUHAUS</text>
```
**QA**: [ ] zero gradients/filters [ ] primaries + black + off-white only [ ] asymmetric balance [ ] angles multiples of 15°

---

## Brutalist {#brutalist}

**Recipe - block with hard shadow**
```svg
<g id="block">
  <rect x="48" y="48" width="240" height="140" fill="#111"/>                     <!-- hard shadow, +8,+8 -->
  <rect x="40" y="40" width="240" height="140" fill="#ffe600" stroke="#111" stroke-width="6" stroke-linejoin="miter"/>
  <text x="56" y="120" font-family="'Courier New', monospace" font-weight="700" font-size="44">RAW.</text>
</g>
```
**Design moves**: heavy borders (4-8), hard offset shadows, monospace caps, visible grid, one or two shouting colours, deliberately awkward but structured.

**QA**: [ ] no gradients/blur/rounding [ ] borders ≥ 4 [ ] ≤ 6 colours [ ] type oversized

---

## Vintage Poster {#vintage-poster}

**Layer stack**: `paper + vignette` → `sky bands + sun rays` → `far → near scenery (flat inks)` → `overprint accents` → `title block` → `paper-texture overlay` → `border`.

**Design moves**
- Ink budget of 4-6. Distance = lighter and bluer. Sun = concentric circle + wedge rays clipped to the sky.
- Title in the lower or upper band (20-25 % of height); subtitle small, letter-spaced.
- Age it: warm vignette + speckle overlay, never blur.

**Recipe - paper wear overlay**
```svg
<defs>
  <filter id="wear" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="4"/>
    <feColorMatrix type="matrix" values="0 0 0 0 .35  0 0 0 0 .25  0 0 0 0 .15  0 0 0 .8 -.28"/></filter>
  <radialGradient id="age" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#7a5a2b" stop-opacity="0"/><stop offset="1" stop-color="#7a5a2b" stop-opacity=".35"/></radialGradient>
</defs>
<rect width="900" height="1300" fill="url(#age)"/><rect width="900" height="1300" filter="url(#wear)" opacity=".35"/>
```
**QA**: [ ] `<text>` title present (or outlined) [ ] ≤ 6 inks [ ] scenery flat (no gradient shading) [ ] margin + border frame [ ] warm paper base

---

## Medieval Manuscript {#medieval-manuscript}

**Layer stack**: `parchment` → `ruling lines` → `gold-leaf panel (initial + border ground)` → `historiated initial` → `vine border + drolleries` → `text block placeholder` → `stains/aging`.

**Design moves**
- Flattened perspective; important = large; opaque pigments with brown-black contour.
- Gold: 4-5 stop gradient + fine burnish pattern.
- Text block = ruled thin lines (do not fake unreadable text).

**Recipe - vine with leaf uses**
```svg
<path id="vine" d="M40 60 C 60 200, 20 320, 60 460" fill="none" stroke="#3b7a5c" stroke-width="3" stroke-linecap="round"/>
<g id="leaf"><path d="M0 0 C 12-10 26-6 30 8 C 16 14 4 10 0 0Z" fill="#3b7a5c"/></g>
<use href="#leaf" transform="translate(52 150) rotate(20)"/><use href="#leaf" transform="translate(30 250) rotate(160) scale(-1 1)"/>
```
**QA**: [ ] gold = gradient [ ] parchment darkens toward edges [ ] borders filled with vine/creature detail [ ] no modern perspective/shading

---

## Gothic {#gothic}

**Layer stack**: `night sky/vignette` → `stone architecture silhouette` → `light shafts` → `stained-glass window (jewel panes + lead lines)` → `foreground silhouette` → `fog bands`.

**Design moves**
- Pointed arch = two circular arcs meeting at the apex. Rose window = a petal rotated in equal steps + leading strokes over jewel fills.
- One motivated light (window/moon/candle), everything else falls into shadow.

**Recipe - lancet arch + rose window**
```svg
<path d="M150 470 V240 A110 110 0 0 1 256 130 A110 110 0 0 1 362 240 V470Z" fill="#231a33"/>   <!-- approximate lancet -->
<g transform="translate(256 260)" fill="#1e3a6b" stroke="#0c0a12" stroke-width="3">
  <path id="pane" d="M0-10 L22-60 A62 62 0 0 1-22-60Z"/>
  <use href="#pane" transform="rotate(45)" fill="#6b1e2e"/><use href="#pane" transform="rotate(90)" fill="#d9a441"/> <!-- … every 45deg -->
</g>
```
**QA**: [ ] value-dark overall with one bright focal area [ ] vertical emphasis [ ] lead-line strokes consistent [ ] fog/vignette present [ ] no cheerful pastel palette
