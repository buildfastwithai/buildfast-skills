# Modes: multi-version, style transformation, style-cut, benchmark

## Multi-version ("the same video in 3 styles")
Same script, scene structure, timing and message; different visual language, colours, typography, transitions, motion language and asset treatment.
1. `plan.py "<brief> in 3 styles"` → picks named styles, or contrasting families when unnamed (listed under variants).
2. Build ONE composition that is token-driven: colours via `var(--...)`, sizes via roles, entrances via `s.enter`, transitions `type:'auto'` with an `intent`, backgrounds via `s.bg('auto')` where the style should decide. Per-style branches are allowed where an asset must change (`C.theme.id`), but keep scene ids and timings identical.
3. `render.py <p> --variants "minimal:calm;cyberpunk:cinematic;vhs:glitch"` → `out/NAME__<style>-<motion>.mp4` per variant + `out/NAME__compare.mp4` (side by side, labelled). Check the comparison: same beats at the same moments, each clearly its own style.

## Style transformation ("make this more cinematic", "convert this to cyberpunk")
Modify, don't rebuild. Preserve narrative, timing and important assets.
- Motion change ("more cinematic", "snappier"): set `"motion": "cinematic"` (or add it: `"snappy+cinematic"`).
- Look change ("cyberpunk"): set `"style"`, or blend (`"minimal+cyberpunk"` keeps minimal layout, borrows cyberpunk palette/mood).
- Try first as a one-off: `render.py <p> --style cyberpunk --motion cinematic --stills`, then commit to spec.json.
- Only then edit scenes whose assets clash with the new style (e.g. photographic textures in pixel art); report what changed.

## Style-cut ("one scene, every style" - launch reels, sizzle cuts, "show me all the looks")
The same scene re-rendered in many style/motion combinations and spliced frame-accurately on the beat grid, so the choreography keeps going while the whole look changes on every cut. Grid cuts tile several styles at once (split screen); the music can follow each style's genre on one tempo + key, quantized to the beat, with a DJ beat-roll build (`"audio": "roll"`).
1. Build the scene token-driven (as for multi-version); keep continuous motion in `s.every`/`s.tween` with explicit eases so it is identical in every style; let entrances use `s.enter` so each motion language shows.
2. Write `cuts.json` (`{"cuts": [{"t0","t1","style","motion"?} | {"t0","t1","grid":[...],"cols","audio":"roll"}], "audio_quant": 0.5, "music": "follow"}`) - contiguous, on the beat grid; no motion = the style's own motion language. Accelerating cut lengths (bar -> beat -> 1/2 -> 1/4 beat) read as a build.
   Re-score any other window without touching its picture: `{"t0":0,"t1":3,"audio_only":true,"music_style":"corporate","level":.4,"end":"tapestop"}` (e.g. cheesy stock music that grinds to a halt when the real video starts).
3. `stylecut.py <p> cuts.json` -> base render + one browser per style for only its frames -> `out/NAME__stylecut.mp4` + QC. The composition can read `window.MS_SPEC.stylecut.cuts` (e.g. a "STYLE 07/28" HUD with `C.theme.name`).

## Benchmark (comparing models)
`benchmark.py list | init <id> <dir> | run <dir> | compare <dirs...>` - frozen briefs in benchmarks/standard.json (duration, fps, format, seed, bpm, scene timings, required text, 3 style/motion variants). The model under test only writes composition.html. `run` renders every variant with `--benchmark` (frame/audio hashes), QCs them, re-renders sample frames in fresh browsers to prove determinism, and scores: QC errors/warnings, timing adherence, required text present, transition variety, determinism. Visual quality still needs review of `__compare.mp4` and QC sheets. Details: benchmark.md.
