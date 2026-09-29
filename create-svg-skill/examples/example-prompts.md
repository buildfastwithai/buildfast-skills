# Example prompts

Every prompt below works as-is or prefixed with the slash command, e.g. `/create-svg A fox in pixel art`. A bare `/create-svg` asks what to draw and shows the style menu.

What to type, what the router does with it, and what you should get. Run any prompt through the router yourself:
`python3 scripts/route_style.py "<prompt>" --no-brief`

## Single style
| Prompt | Routed to | Notes |
|---|---|---|
| `A fox in pixel art` | pixel-art | grid sprite via `pixel_grid.py`, no anti-aliasing |
| `an 8 bit dragon` | retro-8bit | "8 bit" alias; tighter palette than pixel-art |
| `Ukiyo-e heron by a river` | ukiyo-e | flat blocks, key-block outline, bokashi sky, seigaiha, cartouche |
| `Japanese woodblock print of a crane` | ukiyo-e | natural-language alias |
| `art deco luxury hotel logo` | art-deco (asset: logo) | symmetric, gold gradient, live text with fallback fonts |
| `blueprint of a steam engine` | blueprint | grid paper, dimensions, title block |
| `vintage travel poster for the Alps` | vintage-poster (asset: poster) | limited inks, title band, border |
| `early 2000s glossy internet aesthetic app icon` | y2k + frutiger-aero | shared alias = intentional blend |

## Modifiers (adjust a style, never replace it)
| Prompt | Result |
|---|---|
| `Ukiyo-e but darker: a heron by a river` | ukiyo-e + `darker` - night palette, flat blocks unchanged |
| `Art Nouveau with a modern palette: a peacock` | art-nouveau + `modern-palette` - ornament untouched, contemporary colours |
| `Comic book but realistic: a detective` | comic-book + `realistic` |
| `Make the cyberpunk one more minimal` | routed as a blend: cyberpunk-neon (primary) + minimal-modern (reduction secondary) |

## Blends (primary owns structure, secondary owns mood)
| Prompt | Primary / secondary |
|---|---|
| `cyberpunk + minimalist logo for a coffee brand` | cyberpunk-neon / minimal-modern: dark base, few shapes, one glowing edge, lots of negative space |
| `pixel art with a horror aesthetic, haunted house` | pixel-art / horror: grid intact, horror comes from palette, silhouette, dithered fog |
| `blueprint + sci-fi starship` | blueprint / sci-fi |

## Multi-style (comparable set)
| Prompt | Behaviour |
|---|---|
| `Create a lighthouse in 5 styles` | no styles named -> a contrasting set is chosen and announced; `lighthouse.svg` + `lighthouse-<style>.svg`, then a contact sheet |
| `Draw a fox in pixel art, ukiyo-e, cyberpunk, paper cutout and blueprint` | a list of 3+ styles is multi mode (blends use `+`, `with`, `meets`); exactly those, one shared scene spec (see `outputs/fox-styles.png`) |

## Convert
| Prompt | Behaviour |
|---|---|
| `Convert this SVG to cyberpunk` (attached logo.svg) | transform in place: palette remap, neon strokes, glow, grid underlay; report what was preserved |
| `Turn this PNG into a screen-print poster` | raster is never embedded - viewed, described, redrawn as native vector |
| `Convert my SVG to pixel art` | geometry-dependent style -> rebuilt from a subject spec, not recoloured |

## Cases where the skill asks first
| Prompt | Why |
|---|---|
| `Make me an SVG of a mountain cabin` | no style -> shows `route_style.py --menu` (never picks for a single artwork) |
| `Draw a fox in Japanese style` | ambiguous -> ukiyo-e / sumi-e / manga? |

## Prompts that are declined or redirected
| Prompt | Response |
|---|---|
| `Draw <trademarked character> in manga style` | offers an original character in the style |
| `In the style of <living artist>` | offers the underlying movement/technique instead |
