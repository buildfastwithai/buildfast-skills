# Cinematic & genre styles

Reference for: Cinematic Poster, Fantasy, Sci-Fi, Horror, Retro Futurism.

**Common approach** - these are *lighting-and-atmosphere* styles. Build the scene in value first (dark/mid/light masses), decide the single light source, then add colour grading, then detail. Depth comes from stacked layers separated by haze.

---

## Cinematic Poster {#cinematic-poster}

**Layer stack**: `graded sky/backdrop` → `far silhouettes` → `haze` → `hero silhouette + rim light` → `light shafts/flare` → `particles` → `vignette + grain` → `title treatment` → `billing block`.

**Design moves**
- One idea, one image. Pick the grading (teal/orange, mono + accent, night blue + warm key) and stay inside it.
- Title lower third, wide tracking; tagline above the hero or below the title; billing block ≈ 3 % height in condensed caps.
- Never use real film titles, actors, studio logos.

**Recipe - light shafts + vignette**
```svg
<defs>
  <linearGradient id="shaft" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffcf99" stop-opacity=".55"/><stop offset="1" stop-color="#ffcf99" stop-opacity="0"/></linearGradient>
  <radialGradient id="vig" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".75"/></radialGradient>
</defs>
<polygon points="440,0 520,0 640,900 300,900" fill="url(#shaft)"/>
<rect width="900" height="1350" fill="url(#vig)"/>
<text x="450" y="1120" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="96" letter-spacing="18" fill="#f5efe6">EMBERFALL</text>
```
**QA**: [ ] single focal light [ ] title/billing hierarchy (3 sizes) [ ] ≥ 3 gradients [ ] vignette last-but-text [ ] fictional title

---

## Fantasy {#fantasy}

**Layer stack**: `sky + aurora/sun` → `far mountains` → `mist` → `mid castle/ruins` → `mist` → `hero + creature` → `foreground framing (rocks/trees)` → `magic light + particles`.

**Design moves**
- Aerial perspective: each farther layer is lighter, cooler, lower contrast (mix toward the sky colour).
- Heroic scale: tiny figure, monumental structure. Light path leads to the focal point.
- Magic = radial gradient glow + 5-15 particle dots (single `<pattern>` or scripted `<circle>`s).

**Recipe - layered ranges with mist**
```svg
<path d="M0 520 L90 420 L170 490 L280 380 L380 480 L520 400 V640 H0Z" fill="#5b4b8a"/>
<rect y="470" width="900" height="120" fill="url(#mist)"/>   <!-- mist: sky colour, opacity 0 → .8 → 0 -->
<path d="M0 600 L110 510 L220 590 L360 470 L500 600 L640 520 V760 H0Z" fill="#3b2f66"/>
```
**QA**: [ ] ≥ 4 depth layers with mist bands [ ] one motivated magic light [ ] silhouette readable [ ] no trademarked creatures/worlds

---

## Sci-Fi {#sci-fi}

**Layer stack**: `space gradient` → `starfield` → `nebula` → `planet (shaded + atmosphere)` → `station/ship (hard-surface)` → `engine glow` → `HUD/annotation (optional)`.

**Design moves**
- Scale cues: tiny ship vs huge planet/station; a window row or docking arm gives size.
- Hull = layered polygons with a linear gradient for metal; panel lines as thin darker paths; warm rim from the sun, cool fill from the planet.
- Starfield from a script: 80-200 circles, radius 0.4-1.6, opacity 0.3-1.

**Recipe - planet with atmosphere**
```svg
<defs>
  <radialGradient id="pl" cx=".3" cy=".3" r=".9"><stop offset="0" stop-color="#7ec8d9"/><stop offset=".6" stop-color="#2b6f8f"/><stop offset="1" stop-color="#0a1f3a"/></radialGradient>
  <radialGradient id="atm" cx=".5" cy=".5" r=".5"><stop offset=".92" stop-color="#7ee6ff" stop-opacity="0"/><stop offset=".97" stop-color="#7ee6ff" stop-opacity=".55"/><stop offset="1" stop-color="#7ee6ff" stop-opacity="0"/></radialGradient>
  <clipPath id="pc"><circle cx="620" cy="520" r="300"/></clipPath>
</defs>
<circle cx="620" cy="520" r="300" fill="url(#pl)"/>
<g clip-path="url(#pc)"><path d="M300 470 Q520 430 940 500 V560 Q620 500 300 540Z" fill="#dff6ff" opacity=".25"/></g>  <!-- cloud band -->
<circle cx="620" cy="520" r="318" fill="url(#atm)"/>
```
**QA**: [ ] one light direction [ ] scale cue present [ ] planets shaded (not flat circles) [ ] ≥ 2 gradients [ ] no copied franchise ships

---

## Horror {#horror}

**Layer stack**: `near-black base` → `light cone (radial/linear, low opacity)` → `what the light touches` → `silhouette forms` → `fog bands` → `vignette` → `grain`.

**Design moves**
- Start black and *add light*, not the reverse. Show less: half-hidden shapes, eyes, hands.
- Off-centre focal point, Dutch angle, extreme proportions.
- One violent accent only (arterial red or sick green). No gore - dread, not splatter.

**Recipe - fog + vignette**
```svg
<linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9bb0a4" stop-opacity="0"/><stop offset=".5" stop-color="#9bb0a4" stop-opacity=".35"/><stop offset="1" stop-color="#9bb0a4" stop-opacity="0"/></linearGradient>
<rect y="520" width="900" height="200" fill="url(#fog)"/>
<rect width="900" height="1200" fill="url(#vig)"/>
```
**QA**: [ ] dark base (validator `dark-base`) [ ] ≥ 70 % of pixels dark [ ] a single bright focal area [ ] asymmetric framing

---

## Retro Futurism {#retro-futurism}

Two moods - pick one. **Atomic age**: cream + teal + mustard, googie shapes. **Synthwave**: indigo → magenta → orange sky, striped sun, perspective grid.

**Layer stack (synthwave)**: `sky gradient` → `stars` → `striped sun` → `mountains` → `horizon glow` → `grid floor` → `hero (car/palm/rocket)` → `chrome title`.

**Recipe - striped sun (mask) + perspective grid**
```svg
<defs>
  <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd23f"/><stop offset=".5" stop-color="#ff8a1f"/><stop offset="1" stop-color="#ff2e93"/></linearGradient>
  <mask id="stripes"><rect width="900" height="900" fill="#fff"/>
    <rect y="470" width="900" height="6" fill="#000"/><rect y="500" width="900" height="10" fill="#000"/><rect y="535" width="900" height="14" fill="#000"/></mask>
  <linearGradient id="gridfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>
  <mask id="gm"><rect x="0" y="600" width="900" height="300" fill="url(#gridfade)"/></mask>
</defs>
<circle cx="450" cy="470" r="170" fill="url(#sun)" mask="url(#stripes)"/>
<g mask="url(#gm)" stroke="#22d3ee" stroke-width="2" fill="none">
  <path d="M450 600 L-300 900M450 600 L-100 900M450 600 L150 900M450 600 L450 900M450 600 L750 900M450 600 L1000 900M450 600 L1200 900"/>
  <path d="M0 640H900M0 690H900M0 760H900M0 850H900"/>
</g>
```
**QA**: [ ] grid converges to ONE vanishing point on the horizon [ ] sun stripes widen downward [ ] ≥ 2 gradients [ ] one palette family only
