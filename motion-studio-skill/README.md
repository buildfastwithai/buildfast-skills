# Motion Studio

A Claude skill that works like a small motion-design studio: it turns a brief into a finished, QC'd motion-graphics MP4 - concept, storyboard, visual system, animation, sound design and render - in one skill.

- **51 visual styles** in 7 families, **10 motion languages**, **13 video templates**, any aspect ratio
- Three independent creative layers: *visual style* (look) × *motion language* (movement) × *video type* (structure) - combine freely ("cyberpunk product ad with cinematic motion")
- Deterministic, frame-addressable engine (HTML/SVG/Canvas, optional Three.js) rendered by headless Chromium → FFmpeg
- Procedural, beat-synced music + SFX, loudness-normalised
- Automated video QC (16 checks) + contact sheets for visual review
- Multi-version (same video in N styles + comparison grid), style-cut reels (one scene cut through many styles on the beat), style transformation, reproducible benchmark mode

## Install
Copy `motion-studio/` to `.claude/skills/` (project) or `~/.claude/skills/` (personal); in Claude apps upload the zip as a skill. Then just ask for a video, or type `/motion-studio <brief>`.
Requirements: Python 3.9+ with `playwright` (+ Chromium), `numpy`, `scipy`, `pillow`; `ffmpeg`/`ffprobe`. Optional: Node/npm (Three.js via `scripts/vendor.py`), Blender. Check with `python3 scripts/detect_env.py`.

## Basic usage
```
Create a 30 second cinematic video explaining how AI agents work.
Create a 20-second advertisement for an AI coding tool.
Make a 15 second vertical short about our new feature, snappy motion.
```
Unstated choices get sensible defaults (the plan lists them). Explicit control:
```
Duration: 30s   Style: Cyberpunk   Motion: Cinematic   Format: 9:16   Music: Yes   Voiceover: No
```

## Advanced usage
| goal | say / run |
|---|---|
| style combinations | "cyberpunk + cinematic", "anime + energetic", "minimal + calm", "retro VHS + glitch", "SaaS + snappy", "luxury + cinematic", "blueprint + mechanical", "make this infographic feel like an Apple product commercial" |
| same video in N styles | "…in 3 styles" → `scripts/render.py <project> --variants "minimal:calm;cyberpunk:cinematic;vhs:glitch"` (per-style MP4s + side-by-side compare) |
| one scene in every style (launch reel) | `scripts/stylecut.py <project> cuts.json` - style cuts on the beat, split-screen grids, music genre follows the style |
| restyle an existing project | "make this more cinematic", "convert it to cyberpunk" → spec.json style/motion change, timing and narrative preserved |
| other aspect ratio | `render.py <project> --format 9:16` (then adjust scenes that need a vertical layout) |
| music visualizer / lyric video | `scripts/audio.py --analyze song.mp3 <project>` → audio-reactive `C.audio.*` |
| benchmark models | `scripts/benchmark.py init agent-explainer ./bench/x` → give BENCHMARK.md to the model → `benchmark.py run ./bench/x` |

## Pipeline (what the skill does)
```
brief → plan.py (type / style / motion / format / duration / audio / mode)
      → concept + storyboard (reference/storyboard.md)  → plan.py --scaffold  (spec.json, storyboard.md, composition.html)
      → composition.html (engine API)  → render.py --stills / --preview  → look, fix
      → render.py  (frames → H.264, generated audio, loudnorm, QC)  → read QC sheet, fix, re-render → MP4
```

## Layout
```
SKILL.md                 workflow + routing (loaded first)
engine/ms.js, ms.css     the animation engine; fonts/ (bundled OFL fonts); extensions/*.js (your presets/transitions)
styles/visual/*.json     51 visual styles (palette, fonts, type, texture overlays, background, transitions, sound, camera, do/don't)
styles/motion/motion.json 10 motion languages (easing, durations, stagger, camera, transitions, pacing, signature channels)
styles/formats.json      aspect ratios, safe areas, platform notes
templates/*.json         13 video types as beat structures (purpose, share, energy, camera, typography, transition intent, audio)
scripts/  plan.py render.py stylecut.py audio.py qc.py benchmark.py extend.py vendor.py detect_env.py mslib.py
reference/ engine-api storyboard typography camera transitions formats audio qc tool-selection modes benchmark
benchmarks/standard.json frozen benchmark briefs
examples/prompts.md, examples/projects/01-08 (test projects with storyboards, compositions and renders)
```

## Styles (51)
- **commercial**: minimal, apple-product, luxury, corporate, saas, editorial, clean-ui
- **cinematic**: cinematic-trailer, scifi-cinematic, fantasy-cinematic, horror, dark-atmospheric, documentary
- **digital**: cyberpunk, futuristic-hud, holographic, glitch-art, digital-tech, retro-futurism
- **retro**: vhs, crt, eighties, nineties, y2k, pixel-art, eight-bit, sixteen-bit, arcade
- **illustration**: comic-book, manga, anime, hand-drawn, doodle, paper-cutout, stop-motion, childrens
- **information**: infographic, data-viz, technical, blueprint, scientific, whiteboard, documentary-map, timeline
- **abstract**: generative, geometric, liquid, organic, particle, gradient-abstract, experimental

## Motion languages (10)
smooth (default), cinematic, snappy, elastic, mechanical, organic, glitch, energetic, calm, stop-motion. Each defines easing per role (enter/exit/move/emphasis/camera), durations, stagger, overshoot, pacing (average shot length), camera behaviour (push/drift/shake/handheld), preferred/avoided transitions and signature channels (glitch jolts, organic jitter, stepped time, blur). Combine: the primary owns timing and easing, secondaries add their signature channels.

## Templates (13)
cinematic-trailer, product-ad, product-demo, explainer, kinetic-typography, infographic, logo-reveal, social-short, documentary, tech-news, music-visualizer, lyric-video, ui-promo. They define structure (beats, shares, energy curve, transition intents), never a fixed look.

## Extending
```bash
python3 scripts/extend.py new-style vaporwave --name "Vaporwave" --family retro --from eighties --alias "vapor wave"
python3 scripts/extend.py new-motion floaty --from calm --alias "dreamy motion"
python3 scripts/extend.py new-template podcast-clip --from social-short --alias "podcast clip"
python3 scripts/extend.py new-preset swirlIn          # engine/extensions/swirlIn.js  -> s.anim(n, 'swirlIn', at)
python3 scripts/extend.py new-transition splitOpen    # engine/extensions/splitOpen.js -> C.transition(a, b, {type:'splitOpen'})
python3 scripts/extend.py lint                        # must report 0 errors
```
- **Visual style**: edit the copied JSON: palette (bg, bg2, surface, fg, muted, accent 1-3, line), fonts (`"Family:weight"` - bundled in engine/fonts; add woff2 + @font-face in fonts.css for new families), type (case, tracking, lead, display_scale), texture overlays (`grain:.08`, `scanlines`, `vhs`, `crt`, `halftone`, `paper`, `vignette`, `letterbox`, `film`, `lightleak`, `hud`, `chromatic`), default background, radius/stroke/glow, preferred/avoided transitions, sound (music genre, bpm, key, sfx palette), camera notes, assets, do/don't, motion_default. Add aliases so natural language routes to it.
- **Motion language**: ease per role (`outExpo`, `bezier(a,b,c,d)`, `spring(k,d)`, `steps(n)`, `back(s)`), dur, stagger, dist, overshoot, blur/jitter/step_fps/glitch channels, camera, transitions, enter/exit presets, pacing, principles.
- **Template**: beats (`id, share, purpose, visual, camera, animation, typography, transition, audio, energy, intent`); shares sum to 1.
- **Animation primitive / transition / background**: a JS file in `engine/extensions/`; use the per-frame state (`st.x, st.y, st.s, st.o, st.blur, ...`) - never set styles directly - so it stays seekable.

## Examples
`examples/prompts.md` lists representative prompts. `examples/projects/` has 8 finished test projects (minimal product ad, cyberpunk cinematic with Three.js, kinetic typography 1:1, infographic, anime game trailer, VHS glitch teaser, luxury logo reveal, vertical social short) with their storyboards and compositions; `python3 scripts/render.py examples/projects/<name>` reproduces each MP4 + QC report in its `out/` folder (renders are not shipped inside the skill).

## Known limitations
- No bundled text-to-speech: voice-over needs a recorded file; captions are always generated on screen.
- Generated music is functional, loop-based synth music, not composition-grade; supply a track (`audio.file`) for hero pieces.
- WebGL runs on software GL in headless Chromium: 3D scenes render slowly (~1-3 fps); keep them simple.
- Visual quality is judged by the model looking at contact sheets; automated QC covers technical hygiene, not taste.
- Styles use bundled OFL fonts (17 families); new fonts must be added as files (no network fetch at render time).
- Existing video footage is composited with FFmpeg rather than inside the engine (frames must be seekable).
