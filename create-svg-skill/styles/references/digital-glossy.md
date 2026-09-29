# Digital, glossy & 3D styles

Reference for: Cyberpunk Neon, Y2K, Frutiger Aero, Glassmorphism, Clay / Soft 3D, Isometric, Low Poly.

**Effect budget rule**: filters are expensive and can clip. Prefer gradients + stacked shapes; use a filter only when no vector construction gives the same result, define each filter ONCE, and apply it to *groups*.

---

## Cyberpunk Neon {#cyberpunk-neon}

**Layer stack**: `sky-gradient` → `far-skyline` (dark silhouettes) → `haze-band` → `mid-buildings` (windows, signs) → `neon-signs` (glow group) → `subject` (silhouette + rim) → `ground-reflection` → `rain/scanlines` → `vignette`.

**Design moves**
- 70 % dark / 25 % mid / 5 % pure neon. Two coloured lights from opposite sides (magenta vs cyan).
- Neon tube = 2 strokes on the same path: a bright thin core (`#fff` or pale tint, 1-2 units) over a saturated wider stroke (3-5 units); the *glow filter* goes on the parent `<g>`.
- Reflection: `<use>` the skyline flipped, masked by a fading gradient.

**Recipe - glow filter + neon tube**
```svg
<defs>
  <filter id="glow" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">
    <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#07040f"/><stop offset=".65" stop-color="#2a0f4d"/><stop offset="1" stop-color="#ff2a6d"/>
  </linearGradient>
</defs>
<g id="neon-signs" filter="url(#glow)" fill="none" stroke-linecap="round">
  <path id="tube" d="M120 300h160" stroke="#ff2a6d" stroke-width="5"/>
  <use href="#tube" stroke="#ffd6e4" stroke-width="1.6"/>
</g>
```
**Scanlines / rain overlay**
```svg
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity=".18"/></pattern>
<rect width="100%" height="100%" fill="url(#scan)"/>
```

**QA checklist**
- [ ] Base is genuinely dark (validator `dark-base`)
- [ ] Glow is on ≤ 3 groups; filter region ≥ 160 % (no clipped halos)
- [ ] Two opposing light colours; one warm accent at most
- [ ] Render: bright neon occupies a *small* share of pixels

---

## Y2K {#y2k}

**Layer stack**: `gradient-field` → `orbit-rings` → `hero-chrome-object` → `gloss-highlights` → `sparkles` → `ui/cursor fragments`.

**Recipe - chrome gradient (fake horizon reflection)**
```svg
<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0"   stop-color="#ffffff"/>
  <stop offset=".35" stop-color="#9fb4d6"/>
  <stop offset=".5"  stop-color="#33456b"/>  <!-- hard horizon line -->
  <stop offset=".51" stop-color="#b9c8e6"/>
  <stop offset="1"   stop-color="#f4f8ff"/>
</linearGradient>
<!-- 4-point sparkle, define once -->
<path id="spark" d="M0-10 C1-3 3-1 10 0 C3 1 1 3 0 10 C-1 3 -3 1 -10 0 C-3-1 -1-3 0-10Z" fill="#fff"/>
```

**QA checklist**
- [ ] Chrome has a *hard* mid-stop (two stops 0.01 apart) - soft chrome reads as plastic
- [ ] ≥ 3 gradients, sparkles are `<use>`
- [ ] Highlights are crisp white, not grey

---

## Frutiger Aero {#frutiger-aero}

**Layer stack**: `sky-gradient` → `clouds/bokeh` → `landscape-strip (grass/water)` → `glass-object` → `bubbles` → `lens-flare`.

**Recipe - bubble**
```svg
<radialGradient id="bub" cx=".35" cy=".3" r=".8">
  <stop offset="0" stop-color="#fff" stop-opacity=".9"/>
  <stop offset=".45" stop-color="#bfe8ff" stop-opacity=".25"/>
  <stop offset="1" stop-color="#5cc8ff" stop-opacity=".55"/>
</radialGradient>
<g id="bubble"><circle r="40" fill="url(#bub)" stroke="#fff" stroke-opacity=".6" stroke-width="1.2"/>
  <path d="M-24-12a28 28 0 0 1 22-18" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="4" stroke-linecap="round"/></g>
```
**Glossy button**: rounded rect + vertical gradient + upper-half highlight clipped to the button with `white .6 → .05` gradient.

**QA checklist**
- [ ] High-key (validator `light-base`), airy
- [ ] ≥ 4 gradients, bubbles are `<use>` with varied scale
- [ ] Only one soft-shadow filter (ground)

---

## Glassmorphism {#glassmorphism}

SVG has no `backdrop-filter`; **fake it**: blurred copy of the background, clipped to each panel.

**Layer stack**: `bg-blobs` → per panel: `blurred-bg-copy (clipped)` → `tint fill` → `gradient border` → `content`.

**Recipe**
```svg
<defs>
  <g id="bg"> <!-- blobs --> </g>
  <filter id="blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="14"/></filter>
  <clipPath id="p1"><rect x="90" y="140" width="330" height="220" rx="28"/></clipPath>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity=".05"/></linearGradient>
</defs>
<use href="#bg"/>
<g clip-path="url(#p1)"><use href="#bg" filter="url(#blur)"/></g>
<rect x="90" y="140" width="330" height="220" rx="28" fill="#fff" fill-opacity=".14" stroke="url(#edge)" stroke-width="1.5"/>
```

**QA checklist**
- [ ] Each panel visibly blurs what is behind it (compare render to a version without the clipped copy)
- [ ] ≤ 3 panel layers; text/icons ≥ 4.5:1 contrast
- [ ] One shared blur filter

---

## Clay / Soft 3D {#clay-soft-3d}

**Layer stack**: `bg` → `contact-shadow (blurred ellipse)` → per object: `base` → `core-shadow crescent` → `highlight patch` → `bounce rim`.

**Recipe - inflated sphere**
```svg
<defs>
  <radialGradient id="clay" cx=".32" cy=".28" r=".85">
    <stop offset="0" stop-color="#ffd0c2"/><stop offset=".55" stop-color="#ffb4a2"/><stop offset="1" stop-color="#e58f8f"/>
  </radialGradient>
  <clipPath id="c1"><circle cx="256" cy="240" r="110"/></clipPath>
  <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="14"/></filter>
</defs>
<ellipse cx="256" cy="380" rx="120" ry="18" fill="#7a4a3a" opacity=".28" filter="url(#soft)"/>
<circle cx="256" cy="240" r="110" fill="url(#clay)"/>
<!-- core shadow, clipped -->
<circle cx="300" cy="290" r="120" fill="#c96f78" opacity=".35" clip-path="url(#c1)"/>
<ellipse cx="216" cy="190" rx="34" ry="20" fill="#fff" opacity=".35" transform="rotate(-30 216 190)"/>
```

**QA checklist**
- [ ] No outlines; shadows are tinted, never grey
- [ ] Light direction identical across all objects
- [ ] Only the contact shadow is blurred

---

## Isometric {#isometric}

**Projection**: `X = (x − y)·cos30°`, `Y = (x + y)·sin30° − z`. Use a generator script for anything beyond a few blocks.

**Layer stack**: `ground-plane` → back-to-front sorted objects (sort by `x+y+z`) → `props` → `shadows` (parallelograms under objects, painted before the object).

**Recipe - cube symbol + reuse**
```svg
<defs>
  <g id="cube">  <!-- unit 40 -->
    <polygon points="0,-20 34.64,0 0,20 -34.64,0" fill="var(--top)"/>          <!-- top -->
    <polygon points="-34.64,0 0,20 0,60 -34.64,40" fill="var(--left)"/>        <!-- left -->
    <polygon points="34.64,0 0,20 0,60 34.64,40" fill="var(--right)"/>         <!-- right -->
  </g>
</defs>
<use href="#cube" x="256" y="200" style="--top:#c9d6ea;--left:#8fa8d0;--right:#5c7ab0"/>
```
Flat art onto the floor: `transform="matrix(0.866 0.5 -0.866 0.5 0 0)"`.

**QA checklist**
- [ ] All edges at 30°/90°; three consistent face tones
- [ ] No gaps between faces (overlap 0.2 units or add same-colour hairline)
- [ ] Draw order back-to-front

---

## Low Poly {#low-poly}

**Workflow**: don't hand-place hundreds of triangles. Place ~15-40 *anchor* points along the silhouette/feature lines, add jittered interior points (denser near features), Delaunay-triangulate in code, colour each triangle from a lighting function, emit `<polygon>`.

**Recipe - facet colouring**
```python
# value = clamp(0.5 + 0.5 * dot(normal, light)) then lerp between shadow/light colour
```
Close seams: `stroke="<same fill>" stroke-width=".5" stroke-linejoin="round"`.

**QA checklist**
- [ ] Silhouette clean; no sliver triangles (min interior angle > 15°)
- [ ] Facet values follow form (light side/dark side clear)
- [ ] ≤ ~12 distinct fills after quantisation (use classes)
