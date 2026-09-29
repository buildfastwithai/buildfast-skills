# Example prompts

Run any of these through `python3 scripts/plan.py "<prompt>"` to see how they are routed (type / style / motion / format / duration / mode).

## Simple (defaults inferred)
- Create a 30 second cinematic video explaining how AI agents work.
- Create a 20-second advertisement for an AI coding tool.
- Make a logo reveal for my bakery "Crumb & Co".
- Animate these quarterly numbers: revenue 1.2M, 1.5M, 2.1M, 2.8M.

## Layered (style + motion + type are separate)
- Create a cyberpunk product advertisement with cinematic motion.
- Make an anime-style AI trailer with energetic motion.
- Create a minimal SaaS advertisement with snappy motion.
- Make a VHS horror documentary with glitch motion.
- Create a futuristic blueprint animation with mechanical motion.
- Make this infographic feel like an Apple product commercial.
- Luxury + cinematic logo reveal for a perfume house, 7 seconds.
- Paper cutout explainer of how composting works, elastic motion, 45 seconds.

## Explicit spec
```
A launch video for Relay, our meeting-notes app.
Duration: 30s   Style: Cyberpunk   Motion: Cinematic   Format: 9:16   Music: Yes   Voiceover: No
```

## Formats
- 15 second vertical short (TikTok/Reels) about three ways to use AI agents, big captions.
- Square 1:1 kinetic typography of the quote "Simplicity is the ultimate sophistication."
- 4:5 Instagram product teaser, minimal + calm.

## Multi-version
- Create the same video in 3 different styles.
- Make our 10 second product teaser in minimal, cyberpunk and paper cutout styles so we can compare.

## Style transformation (existing project)
- Make this video feel more cinematic.
- Convert this animation into a cyberpunk style.
- Same video, but snappier and in 9:16.

## Specialised types
- A 40 second documentary about the history of the bicycle with a map and a timeline.
- A tech news short: "OpenModel 3 released" - three facts, sources on screen. (facts must come from the user or research)
- A music visualizer for assets/track.mp3, organic motion, liquid style.
- A lyric video for these timed lines: ...
- UI promo of our onboarding flow: cursor clicks through 3 screens, toast at the end.

## Benchmark
- Generate the same motion graphics benchmark in three different styles.  → `scripts/benchmark.py init agent-explainer ./bench/run1`

## Test projects in this folder (all rendered and QC'd)
| # | project | brief |
|---|---|---|
| 01 | minimal-product-ad | 15 s minimal product advertisement for Lumen, a smart desk lamp, calm motion |
| 02 | cyberpunk-cinematic | 14 s cyberpunk cinematic teaser for a city called Neon District (Three.js flythrough) |
| 03 | kinetic-typography | 13.5 s kinetic typography, experimental style, snappy motion, square 1:1 |
| 04 | infographic | 16 s infographic data animation of quarterly product metrics (sample data), snappy |
| 05 | anime-game-trailer | 17 s anime-style game trailer for Skyrunner, energetic motion, 140 bpm |
| 06 | vhs-glitch | 13 s VHS horror found-footage teaser "The Signal", glitch motion |
| 07 | logo-reveal | 7 s luxury + cinematic logo reveal for Aurelia |
| 08 | vertical-social | 15 s vertical 9:16 SaaS short about AI agents doing your to-do list, snappy |

Also exercised during development: `render.py 01-minimal-product-ad --variants "minimal:calm;cyberpunk:cinematic;paper-cutout:elastic"` (multi-version + compare grid), `render.py 04-infographic --style apple-product --motion cinematic` (style transformation, timing unchanged), `benchmark.py init agent-explainer` + `run` (3 styles, determinism check, scorecard), `extend.py new-preset/new-transition` stubs used in a test composition, and `audio.py --analyze` on a 112 BPM track (detected 112.5).
