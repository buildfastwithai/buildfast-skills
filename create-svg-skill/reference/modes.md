# Modes, blending & modifiers

Everything here is driven by `scripts/route_style.py "<user request>"`, which returns `mode`, `styles`, `modifiers`, `blend_plan`, `source`, `asset`, `file_names`.

## 0. Style selection protocol

1. Run the router. Trust an explicit style match.
2. `needs_style: true` → **do not choose for the user.** Show the concise menu (`route_style.py --menu`) and ask one question. (Multi-style mode is the exception: "5 styles" without names means *you* pick a contrasting set and say which.)
3. `confirm_style: true` (only a generic word matched, e.g. "luxury hotel") → one-line confirmation, offering the menu.
3b. `ambiguous: true` (e.g. "Japanese style" → Ukiyo-e / Sumi-e / Manga) → ask which, offering just the candidates.
4. A **list of 3+ style names** separated by commas / "and" / "or" / "vs" is read as multi-style; blends need `+`, `with`, `meets`, or similar, and are capped at 3.
5. Two aliases may share a phrase (e.g. "technical schematic" → Blueprint + Technical Illustration). That is intentional: treat as a blend (first = primary).

## 1. Single-style mode
Design brief → build → QA pipeline (`qa-pipeline.md`). Read the routed style brief AND its reference section (`styles/references/<file>#<id>`) before drawing.

## 2. Blending styles ("cyberpunk + minimalist", "pixel art with a horror aesthetic")

Ownership model - the router prints this as `blend_plan`:

| Channel | Owner |
|---|---|
| Geometry, stroke rules, composition, typography, level of detail, **hard constraints** | **Primary** |
| Palette character, lighting, texture, atmosphere, motifs, decorative vocabulary | **Secondary** (adapted to fit primary's limits) |
| Detail level / negative space (when secondary is a *reduction* style: minimal, monochrome, geometric, flat, luxury) | Secondary as a modifier (`as_secondary` in the registry) |

Rules
1. **Primary's hard checks survive.** Pixel art + horror = still integer grid, no blur, ≤ 24 colours; horror arrives through palette, silhouette, dithered fog, composition.
2. **Emulate, don't import, forbidden techniques.** Pixel art forbids filters → build glow as stepped concentric rings.
3. **Budget palettes**, don't add: secondary hues replace, not join, the primary's set.
4. **Sanity test**: cover the palette → still reads as the primary; cover the drawing → the mood reads as the secondary.
5. A declared **conflict** (registry `conflicts_with`) is allowed if the user asked for it, but say what you dropped ("kept ukiyo-e flat blocks; dropped glassmorphism's blur").
6. Max 3 styles. More than that = mush; ask which two matter most.
7. Validate against the **primary** only: `validate_svg.py out.svg --style <primary>`.

Style ↔ modifier examples
| Request | Primary | Secondary / modifier | What to do |
|---|---|---|---|
| cyberpunk + minimalist | Cyberpunk Neon | Minimal (reduction) | dark base, 3-4 shapes, ONE neon edge with glow, ≥ 40 % negative space |
| Ukiyo-e but darker | Ukiyo-e | `darker` | night palette: deeper indigo blocks, moon/lantern accents; flat blocks + key-block unchanged |
| pixel art with a horror aesthetic | Pixel Art | Horror | grid intact; sickly ramps, one red accent, heavy shadow, half-hidden forms |
| Art Nouveau with a modern palette | Art Nouveau | `modern-palette` | curves/ornament identical; contemporary base + 1-2 saturated accents |
| blueprint + sci-fi | Blueprint | Sci-Fi | technical sheet layout; subject is a starship in orthographic views |
| comic book but realistic | Comic Book | `realistic` | inks/halftone stay; anatomy + lighting realistic |

## 3. Modifiers
The router lists matched modifiers with an `effect`. Apply each effect **on top of** the style; never let a modifier delete the style's signature technique.
Vocabulary lives in `styles/modifiers.json` (add rows freely: `id`, `triggers`, `effect`).

## 4. Multi-style mode ("Create this in 5 styles")

Goal: comparable outputs. The *only* thing that changes is style.

1. **Freeze a scene spec** before drawing anything (write it in your notes, or as `<name>.spec.txt` in the output folder):
   ```
   subject : red fox, seated, 3/4 view facing left, tail wrapped around feet
   canvas  : 0 0 1024 1024
   anchor  : head centre (512, 380), body base y=820, subject bbox ≈ 200..830 x 140..860
   props   : pine branch top-right, small moon top-left
   ```
2. If a base illustration already exists (`fox.svg`), keep its geometry as the *layout reference*.
3. For each style: read its brief, redraw/transform to the **same anchors**, respecting that style's rules. Same pose, same crop, same props (translated into each style's vocabulary).
4. Naming: `<subject>.svg` (base or neutral flat version, optional) + `<subject>-<style-id>.svg` for each variant (`fox-pixel-art.svg`, `fox-ukiyo-e.svg` …). The router prints `file_names`.
5. Validate each with its own `--style`, render all, then build a comparison sheet:
   `render_svg.py fox-*.svg --sheet fox-styles.png --cols 3`
6. Inspect the sheet: same subject recognisable in all? similar scale/position? styles clearly different from each other? Fix outliers.
7. No styles listed → the router chooses contrasting families (`multi_styles`). Say which you picked and why (one line).

## 5. Convert mode ("Convert this SVG to cyberpunk")

Decide **transform vs rebuild**:

| Input | Approach |
|---|---|
| SVG with clean structure (named groups, few hundred shapes) | **Transform in place** - preserve geometry/composition |
| SVG that is a flat trace / thousands of tiny paths | Transform palette + add layers; if the style needs different geometry (pixel, low-poly, isometric) rebuild from the *subject spec* extracted from a render |
| Raster (PNG/JPG/photo) | **Never embed it.** View the image, write a subject spec, and redraw as native vector in the target style |
| Style needs different geometry (pixel art, isometric, low poly) | Rebuild (recolouring cannot get there) |

Transform pipeline (all in `scripts/convert_svg.py`)
1. `inspect in.svg` → palette (dark→light), stroke widths, named groups, gradients/filters.
2. Plan the transformation from the style brief: palette · stroke treatment · lighting · texture · effects · decoration.
3. `recolor` - `--palette "<dark→light hexes>"` remaps by luminance rank (keeps light/dark structure); `--map` for hero colours; `--darken/--lighten/--saturate/--hue-shift` for modifiers.
4. `strokes` - `--linecap/--linejoin`, `--width-scale`, `--outline "#111:3"` (adds outlines to fills lacking them; skips the background), `--remove` for flat styles.
5. `inject` - `--wrap-id subject` (so filters target the art), `--drop-background` (otherwise the old background hides new underlays), `--defs` (filters/patterns/gradients), `--underlay` (new sky/grid), `--overlay` (scanlines/grain/vignette), `--set "#subject:filter=url(#glow)"`.
6. Validate + render; compare against the original (`render_svg.py in.svg out.svg --sheet cmp.png`); verify composition and subject are preserved.
7. Report what was preserved vs changed in one short paragraph.

Fragment files for `inject` are plain SVG elements (no `<svg>` wrapper). Keep style-specific snippets small and reusable; several are in `styles/references/*.md`.

## 6. Ambiguity cheatsheet
- "make this look like a vintage poster" with an *image* → convert mode, raster → redraw.
- "in the style of <named living artist>" → do not imitate a specific living artist's work; offer the closest movement/technique (e.g. flat colour blocks + halftone) instead.
- Trademarked characters/logos → do not reproduce; offer an original character in the requested style.
