# Tool selection

Run `python3 scripts/detect_env.py` once. Then choose the **simplest technology that achieves the look**, per scene:

| need | use | why |
|---|---|---|
| kinetic type, UI, cards, charts, logo reveals, 2.5D parallax | engine DOM + SVG (default) | crisp text, real fonts, fast, fully deterministic |
| particles, generative/flow fields, noise, audio-reactive drawing | engine canvas (`s.particles`, `MS.canvasLayer`) | thousands of marks per frame |
| true 3D (cities, products, tunnels, orbiting objects) | Three.js via `vendor.py <project> three` inside the same composition | real perspective/lighting; keep scenes light (instancing) because headless Chromium uses software GL |
| photoreal 3D | Blender (`blender -b ... -a`) if installed, then composite with FFmpeg | only when truly needed; say so if Blender is missing |
| compositing existing footage/screen recordings, captions over video, concatenation | FFmpeg (and `<video>` is avoided: frames must be seekable) | exact, fast |
| a repo that already uses Remotion | follow the repo (Remotion + React) instead of this engine | respect existing conventions |
| data from CSV/JSON | load into `spec.vars` or `assets/*.json` and read it in the composition | data drives geometry |

Installing: optional browser libraries go into the project via `vendor.py` (npm pack, no global installs). If something required is missing and can't be installed safely (e.g. no network), fall back to the nearest capability and tell the user what changed.
Performance: 1080p DOM scenes render at ~5-15 fps with 2 workers; WebGL scenes at ~1-3 fps (software GL). Use `--preview` for timing and `--stills` for design; do one final render at the end.
