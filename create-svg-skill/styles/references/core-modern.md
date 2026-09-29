# Core / Modern styles

Reference for: Minimal / Modern, Flat Design, Geometric, Monochrome, Luxury / Premium.
Registry entries hold the rules; this file holds **build order, SVG recipes and QA checklists**.

---

## Minimal / Modern {#minimal-modern}

**Layer stack**: `background` → `subject-mass` (1-3 shapes) → `accent` (1 small shape) → optional `shadow-hint`.

**Design moves**
1. Squint test first: reduce the subject to a silhouette of 2-4 primitives. If it does not read, add a *defining* shape - never texture.
2. Pick the grid unit U (8 or 16). Every coordinate is a multiple of U/2.
3. One accent colour on the single thing the eye should land on.

**Recipe - palette as variables (easy recolouring)**
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <title>Minimal fox mark</title>
  <style>
    :root { --bg:#f5f3ee; --ink:#1a1a1f; --accent:#ff5a36; }
  </style>
  <rect id="background" width="512" height="512" fill="var(--bg)"/>
  <g id="subject">
    <path d="M136 328 L256 152 L376 328 Q256 400 136 328Z" fill="var(--ink)"/>
    <circle id="accent" cx="256" cy="288" r="24" fill="var(--accent)"/>
  </g>
</svg>
```
> CSS variables are honoured by browsers and most editors, but some converters ignore them. For files that must survive Illustrator/Figma round-trips, inline the hex values and keep the palette in a comment.

**QA checklist**
- [ ] Reads at 32×32 px
- [ ] ≥ 40 % of the canvas is empty
- [ ] ≤ 4 colours, ≤ 2 stroke widths, no filters
- [ ] Optical centring: circles/triangles nudged 2-3 % so they *look* centred

---

## Flat Design {#flat-design}

**Layer stack**: `bg` → `far-shapes` → `mid-scene` → `subject` (base shapes, then `shade` shapes) → `props` → `long-shadow`.

**Design moves**
- Every object = base fill + one darker "shade" shape + optionally one lighter "hilite" shape. No blends.
- Keep saturation equal across hues so nothing "pops" by accident.
- Long shadow: a polygon projected at 45°, `fill-opacity .12-.2`, clipped to the object's ground.

**Recipe - shade shape via clip-path (define once, reuse)**
```svg
<defs>
  <clipPath id="clip-body"><rect x="120" y="160" width="200" height="220" rx="48"/></clipPath>
</defs>
<rect x="120" y="160" width="200" height="220" rx="48" fill="#ef476f"/>
<!-- shade: same shape, offset circle clipped inside it -->
<circle cx="330" cy="330" r="190" fill="#c9345a" clip-path="url(#clip-body)"/>
```

**QA checklist**
- [ ] Zero gradients, zero filters
- [ ] Each object has exactly one shade step (consistent light direction)
- [ ] Palette ≤ 14 colours, grouped as hue families

---

## Geometric {#geometric}

**Layer stack**: `grid-comment` → `background` → `structure` (large primitives) → `rhythm` (repeats) → `accents`.

**Design moves**
- Declare the construction in a comment: `<!-- grid: 12 units, module 40, golden-ratio radii 40/65/105 -->`.
- Use even-odd fills for concentric cut-outs; use `<use>` + rotate for radial repetition.
- Alternate warm/cool at every boundary so overlapping primitives never merge.

**Recipe - radial repetition**
```svg
<defs><path id="petal" d="M0 0 C 20 -40 20 -80 0 -110 C -20 -80 -20 -40 0 0Z"/></defs>
<g transform="translate(256 256)" fill="#e63946">
  <use href="#petal" transform="rotate(0)"/>
  <use href="#petal" transform="rotate(45)"/>
  <use href="#petal" transform="rotate(90)"/>
  <!-- ... every 45deg -->
</g>
```

**QA checklist**
- [ ] Every angle is a multiple of 15°
- [ ] Shared tangent points actually touch (zoom to 800 %)
- [ ] Repeats are `<use>`, not copy-pasted paths

---

## Monochrome {#monochrome}

**Layer stack**: `paper` → `light-masses` → `mid-masses` → `dark-masses` → `line/hatch` → `spot-black`.

**Design moves**
- Plan a value ladder first (5-7 steps) and *assign every region a step* before drawing.
- Line weight and hatch density are the variables that replace colour.
- Keep the darkest darks connected so the shadow reads as one shape.

**Recipe - hatch density ramp**
```svg
<defs>
  <pattern id="hatch-l" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="8" stroke="#3a4550" stroke-width="1"/></pattern>
  <pattern id="hatch-d" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="#101418" stroke-width="1.4"/></pattern>
</defs>
```

**QA checklist**
- [ ] Only one hue family (check `convert_svg.py inspect` palette)
- [ ] Squint: three clear value masses
- [ ] Silhouette still reads in pure black

---

## Luxury / Premium {#luxury-premium}

**Layer stack**: `base` → `hairline-frame` → `central-mark` → `metallic-accents` → `typography`.

**Design moves**
- 70 %+ empty. The mark is small and perfectly aligned; margins ≥ 15 %.
- Gold lives in *lines and small masses*. Define ONE gradient in `userSpaceOnUse` so every gold element shares the same light sweep.

**Recipe - reusable gold**
```svg
<defs>
  <linearGradient id="gold" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="512" y2="512">
    <stop offset="0"   stop-color="#8f6a25"/>
    <stop offset=".35" stop-color="#f1d99a"/>
    <stop offset=".6"  stop-color="#b8893b"/>
    <stop offset="1"   stop-color="#e9cf8b"/>
  </linearGradient>
</defs>
<rect x="56" y="56" width="400" height="400" fill="none" stroke="url(#gold)" stroke-width="1.5"/>
<rect x="68" y="68" width="376" height="376" fill="none" stroke="url(#gold)" stroke-width=".75"/>
```

**QA checklist**
- [ ] Gold is a gradient, never a flat yellow
- [ ] Hairlines ≥ 0.75 at 512 px (they must survive small sizes)
- [ ] Text converted to paths for logos (fonts are not embedded)
