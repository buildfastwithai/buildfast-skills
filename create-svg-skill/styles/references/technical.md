# Technical & data styles

Reference for: Blueprint, Technical Illustration, Scientific Illustration, Infographic.

**Principle**: geometry is *computed*, not eyeballed. For anything with real dimensions or data, write a small Python/JS generator and emit the SVG; keep the generator in the output folder if the user may want to tweak numbers.

---

## Blueprint {#blueprint}

**Layer stack**: `blue ground` → `minor grid` → `major grid` → `border + title block` → `construction lines (hairline)` → `object linework (thick)` → `hidden/centre lines` → `dimensions + leaders + callouts` → `notes`.

**Line hierarchy** (units at 1000-wide canvas)
| Role | Width | Dash |
|---|---|---|
| Object outline | 2.5 | solid |
| Feature edge | 1.5 | solid |
| Hidden edge | 1.0 | `6 3` |
| Centre line | 0.8 | `12 3 2 3` |
| Dimension / leader | 0.6 | solid |
| Minor grid | 0.4 | solid |

**Recipe - grid + dimension marker**
```svg
<defs>
  <pattern id="g-minor" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="#2a5cb5" stroke-width=".4" opacity=".5"/></pattern>
  <pattern id="g-major" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M50 0H0V50" fill="none" stroke="#2a5cb5" stroke-width=".8" opacity=".7"/></pattern>
  <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 1L10 5L0 9Z" fill="#dbeaff"/></marker>
</defs>
<rect width="1000" height="700" fill="#0d3b8c"/><rect width="1000" height="700" fill="url(#g-minor)"/><rect width="1000" height="700" fill="url(#g-major)"/>
<g id="dim-width" stroke="#dbeaff" stroke-width=".6" fill="none">
  <path d="M200 520H700" marker-start="url(#arr)" marker-end="url(#arr)"/>
  <path d="M200 470V530M700 470V530"/>
  <text x="450" y="514" fill="#dbeaff" stroke="none" text-anchor="middle" font-family="'Courier New', monospace" font-size="14">500</text>
</g>
```
**QA**: [ ] ≥ 3 distinct stroke widths [ ] grid `<pattern>` present [ ] every dimension has extension lines + arrows + value [ ] title block (name, scale, sheet) [ ] no gradients/shading [ ] colour = blue/white/cyan only

---

## Technical Illustration {#technical-illustration}

**Layer stack**: `paper` → `ground shadow (faint)` → `part fills (grey tones)` → `linework` → `section hatch` → `alignment lines (dashed)` → `arrows` → `callouts`.

**Design moves**
- Exploded view: parts separated along ONE axis with dashed alignment lines; keep them in assembly order.
- Signal colour marks *what moves* or *what matters* (orange); everything else is grey.
- Section hatch at 45° in cut faces via pattern + clip.

**Recipe - callout symbol**
```svg
<symbol id="callout" viewBox="-14 -14 28 28"><circle r="12" fill="#fff" stroke="#1a1a1a" stroke-width="1.5"/></symbol>
<g id="c1"><path d="M410 300 L470 250" stroke="#1a1a1a" stroke-width=".8"/>
  <use href="#callout" x="470" y="250" width="28" height="28" transform="translate(-14 -14)"/>
  <text x="470" y="255" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="700">1</text></g>
```
**QA**: [ ] consistent line weights [ ] every arrow means something (motion/assembly) [ ] numbered callouts sequential [ ] ≤ 2 signal colours

---

## Scientific Illustration {#scientific-illustration}

**Layer stack**: `plate paper + border` → `main specimen (washes)` → `contours + hatch` → `detail insets` → `labels + leader lines` → `caption + scale bar`.

**Design moves**
- Accuracy over flourish: research proportions; note uncertainty in the caption if approximating.
- Tone via gradient washes *inside* contours (opacity .6-.9), then hatch/stipple for form.
- Repeat units (scales, feathers, petals) via `<use>` with per-instance variation.
- Caption block in italic serif; scale bar with real units when a size is known.

**Recipe - stipple + hatch patterns**
```svg
<pattern id="stipple" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="1.2" cy="1.4" r=".6" fill="#3a2a1e"/><circle cx="4.4" cy="4.2" r=".5" fill="#3a2a1e"/></pattern>
<pattern id="hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><path d="M0 0V4" stroke="#3a2a1e" stroke-width=".6"/></pattern>
```
**QA**: [ ] labelled parts + leader lines [ ] Latin/common name caption [ ] scale bar [ ] muted natural palette [ ] hairline weights survive at 1000 px

---

## Infographic {#infographic}

**Layer stack**: `background` → `header` → `hero-stat` → `modules (cards)` → `charts` → `legend` → `footer/source`.

**Design moves**
- Sketch the reading order in one sentence before drawing.
- Compute geometry from data. Bar length = `value / max * width`; donut arc = `2πr · value/total`; never eyeball proportions.
- Colour encodes meaning; greys for context. Check distinguishability without hue (vary lightness).
- Text: title 3-4× body; label size ≥ 12 units on a 1000-wide canvas; `text-anchor` for alignment.

**Recipe - generated bar chart (Python)**
```python
data = [("Q1", 42), ("Q2", 58), ("Q3", 71), ("Q4", 66)]
mx, W, H, bar = max(v for _, v in data), 520, 260, 90
out = []
for i, (k, v) in enumerate(data):
    h = v / mx * H
    out.append(f'<rect x="{i*(bar+20)}" y="{H-h:.1f}" width="{bar}" height="{h:.1f}" rx="6" fill="#2563eb"/>')
    out.append(f'<text x="{i*(bar+20)+bar/2}" y="{H+22}" text-anchor="middle" font-size="14">{k}</text>')
```
**Donut arc path**: `M cx+r cy A r r 0 large 1 x y` with `large = 1 if share > .5` and `x,y = (cx + r·cos θ, cy + r·sin θ)`.

**QA**: [ ] ≥ 3 named groups (`header`, `chart-1`, `legend`, `footer`) [ ] numbers reconcile with source data [ ] no 3D/chartjunk [ ] `<title>`/`<desc>` present [ ] never invent statistics - use clearly labelled placeholder data if none supplied
