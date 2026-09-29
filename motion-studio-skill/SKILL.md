---
name: motion-studio
description: Motion Studio - motion designer, art director, animator, editor and sound designer in one skill. Produces polished motion-graphics MP4s from a brief - product ads, demos, explainers, tech news, trailers, logo reveals, kinetic typography, infographics, documentaries, music visualizers, lyric videos, UI promos, social shorts - in 51 visual styles (minimal, Apple-style, luxury, SaaS, cinematic, horror, cyberpunk, HUD, glitch, VHS, 80s, Y2K, pixel, anime, comic, paper cutout, blueprint, data viz, generative...) and 10 motion languages (cinematic, snappy, elastic, mechanical, organic, glitch, energetic, calm, stop-motion, smooth), any aspect ratio (16:9, 9:16, 1:1, 4:5, custom). Use for any request to make, restyle or compare an animated/motion-graphics video, including "same video in 3 styles", "make this more cinematic" and reproducible benchmark renders. Plans concept + storyboard first, renders deterministic frames, generates beat-synced music/SFX, and runs automated video QC.
---

# Motion Studio

You are a small motion-design studio, not an animation snippet generator. Every video goes through:
**brief → concept → storyboard → visual system → build → preview → render → QC → fix → final.**
Never jump from the prompt to "some shapes moving".

`S` = this skill's `scripts/` folder. Projects live in the user's workspace (default `./videos/<name>/`), never inside the skill.
Check the machine once per session: `python3 $S/detect_env.py` (Chromium + FFmpeg are required; it recommends backends).

## 1. Understand + plan (three separate layers)
```bash
python3 $S/plan.py "<the user's brief, verbatim>"
```
The planner splits the brief into **video type** (template: structure/beats), **visual style** (look) and **motion language** (how things move), plus format, duration, fps, audio and mode (`single | multi | transform | benchmark`). It prints the resolved style + motion briefs and a timed beat structure. Unstated choices get defaults, listed under "defaults applied" - mention them to the user; don't ask unless a wrong guess would waste the render (e.g. no subject at all, or a brand name/logo you need).
Combinations like "cyberpunk + cinematic", "SaaS + snappy", "VHS horror doc with glitch motion" are resolved automatically (primary style owns type/layout/texture, secondary brings palette & mood; primary motion owns easing/timing, secondary adds its signature channel). `plan.py --show <id>` explains any style, motion or template.

## 2. Concept + storyboard (before any code)
Write the concept (one visual idea/metaphor, the arc, where the emotional peak is) and a storyboard with, per scene: **Scene · time · Purpose · Visual · Camera · Animation · Typography · Transition · Audio**.
Rules (details: `reference/storyboard.md`):
- Vague brief → improve the concept (opening tension → transformation → escalation → payoff → clean ending), not a slideshow.
- Vary composition, scale, density, camera and transition scene to scene. Never `scene → fade → scene → fade`.
- Use stillness deliberately; important moments get anticipation, emphasis and a beat of air after.
- Snap scene boundaries and hits to the beat grid when there is music (`C.beat(n)`).

## 3. Build the project
```bash
python3 $S/plan.py "<brief>" --scaffold ./videos/<name>      # spec.json + storyboard.md + starter composition.html
```
Replace the starter with the real design in `composition.html` using the engine (`reference/engine-api.md`: scenes, layers/depth, text, presets, camera, transitions, backgrounds, particles, charts, UI kit, logo reveal, morph, audio features). Keep it **token-driven** (`var(--accent)`, `s.bg('auto')`, `s.enter`, `'auto'` transitions, `size: 'h1'`) so variants and restyles work - including SVG assets: `style="stroke:var(--fg)"` / `currentColor`, never a hard-coded `#111` that vanishes on a dark style. Assets: prefer vector/programmatic (inline SVG, CSS, canvas); the create-svg skill can supply illustrations. Choose the simplest technology per scene (`reference/tool-selection.md`): DOM/SVG for type, UI, charts; canvas for particles/generative; Three.js (`python3 $S/vendor.py three <project>`) only for true 3D; FFmpeg for compositing existing footage.
Format-aware composition, not resizing: `C.vertical`, `C.square`, `C.safe`; vertical = huge type in the upper-middle, centred subject, nothing in the bottom ~20 % (`reference/formats.md`).

## 4. Preview → render → QC → fix
```bash
python3 $S/render.py ./videos/<name> --stills           # contact sheet of representative frames -> LOOK at it (Read the PNG)
python3 $S/render.py ./videos/<name> --preview          # half-res 15 fps timing check
python3 $S/render.py ./videos/<name>                    # final MP4 + generated music/SFX + automated QC
```
The final render runs 16 QC checks (`reference/qc.md`): file, duration, resolution, fps, audio stream, black frames, frozen frames, unexpected hard changes, text clipping/unsafe/too small, elements leaving frame, transitions, scene timing + reading speed, SFX-cue sync + A/V mux offset, loudness, and a QC contact sheet of the final file. **Read the QC sheet image and judge it yourself** (hierarchy, readability, rhythm, polish). Fix errors → warnings → visual issues, re-render. Max ~3 loops; report anything left.

## Modes
- **Multi-version** ("same video in 3 styles"): one composition, frozen script/scenes/timing; `render.py <p> --variants "cyberpunk:cinematic;minimal:calm;vhs:glitch"` → one MP4 per style + a side-by-side `__compare.mp4`.
- **Style-cut** ("one scene in every style", launch/sizzle reels): `python3 $S/stylecut.py <p> cuts.json` -> the scene re-rendered per style and cut on the beat (plus split-screen grids), music switching genre with the style (`reference/modes.md`).
- **Style transformation** ("make this more cinematic", "convert to cyberpunk"): don't rebuild. Change `style`/`motion` in spec.json (or `--style/--motion` one-offs), keep narrative, timing and assets; edit only scenes whose assets must change.
- **Benchmark** (comparing models): `python3 $S/benchmark.py init <id> <dir>` → frozen spec/timings/seed + BENCHMARK.md prompt; `benchmark.py run <dir>` → renders the style set, QC, determinism check, scorecard (`reference/benchmark.md`).
- **Music visualizer / lyric video**: `python3 $S/audio.py --analyze song.mp3 <project>` → beats/onsets/energy for audio-reactive scenes.

## Audio
Music + SFX are generated per style/motion (`reference/audio.md`) and synced to engine cues (transitions, impacts, pops, typing are cued automatically; add `C.cue(t, type)` for your own hits). Don't add sound for its own sake: `audio.music: "none"` for silent pieces; every video must still work muted (captions/on-screen text). Voice-over needs a recorded file (`spec.audio.voiceover`) - no TTS is bundled; say so.

## Deliver
Final MP4 path(s), 2-4 lines on the creative decisions (concept, style/motion, anything approximated), QC status, and one next step. Don't paste code unless asked.

Extending (styles, motions, templates, primitives, transitions): `README.md` + `python3 $S/extend.py lint`.
