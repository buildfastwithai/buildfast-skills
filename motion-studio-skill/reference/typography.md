# Typography in motion

Type is animated, not placed. Pick a role per line (`size`: display/h1/h2/h3/body/caption; `font`: display/body/mono); the style supplies the families, case, tracking and leading.

Techniques and how to do them:
| technique | engine |
|---|---|
| kinetic phrase sequences | `MS.kinetic(s, phrases, {moves})`, one move per phrase on the beat |
| word-by-word / char-by-char | `split:'words'|'chars'` + `wordReveal` / `charReveal` (`each:` any preset, `order:'center'|'random'`) |
| line reveals | `split:'lines'` + `lineReveal` (masked rise) |
| masking | `maskReveal`, `wipeIn/wipeOut` |
| tracking changes | `tracking` (from wide → set) |
| scale transitions | `slam`, `scaleIn`, `pop`, camera `push` |
| rotation / perspective | `rotateIn`, `flipIn`, `perspectiveIn`, `rx/ry` in tweens |
| text along paths | `s.textPath(str, d, {from, to, dur})` |
| glitch text | `decode` (scramble → resolve), `glitchText`, `rgbSplit` |
| morphing | cross-dissolve two texts with `blurOut`/`blurIn` at the same position, or morph outlines with `s.morphPath` |
| highlight/underline/strike | `highlight`, `underline`, `strike` |
| typewriter / code | `typewriter`, `MS.ui.code` (typing cues automatic) |

Rules: hierarchy (one display line per screen), ≤ 6 words per display line, line length ≤ ~40 characters for body, keep text in the safe area (QC), never below the minimum size, consistent families (max two + mono), and let key lines hold still long enough to read. Numbers in display fonts with ambiguous digits (e.g. Bangers' 7 reads as 1) go in the body font.
