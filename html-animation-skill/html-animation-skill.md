---
name: canvas-documentary
description: Build a cinematic narrative animation as one self-contained HTML canvas file — a life cycle, a process, a story told in chapters with camera work, procedural art, generated sound, and playback controls.
---

# Canvas documentary

For requests like "animate the life of X", "tell the story of Y like a nature documentary", "a cinematic animated explainer of Z". The deliverable is **one `.html` file**: no libraries, no external assets, no network at runtime. Canvas 2D is almost always the right choice over Three.js — a hand-drawn 2D look reads as art direction, while an under-budgeted 3D scene reads as a broken video game.

## 1. Write the script before any code

Outline chapters first, each with a roman numeral, a title, a subtitle (the stage plus its real-world timing), a duration in seconds, and 3–5 narration captions with `[startSec, endSec, text]`. 6–10 chapters, 12–20s each, ~2 minutes total.

Rules that make it feel like a documentary rather than a slideshow:
- **One dramatic beat per chapter**, and name it: the hatch, the strike, the emergence, the near-miss.
- **Vary the light.** Dusk, underwater, night, dawn, overcast. If two neighbouring chapters share a palette, change one.
- **Narration states facts, never describes the picture.** "Her saliva stops the blood from clotting" — not "she is feeding now." Research the real biology/physics; specifics are what sell it.
- **End on a turn**, not a summary — the cycle restarting, the next thing beginning.

## 2. Architecture

A classic `<script>` (not a module), so top-level functions land on `window` — this is what makes headless testing possible in step 6.

```
utilities      clamp lerp sstep ease frac hash nz(noise) rgba spline vel heading
canvas/camera  setCam(x,y,z) layer(f) screen() resize() with DPR + a fixed 1600x900 design space
draw helpers   grad rgrad pathEl dot line glow — all in world units
world data     initData(): every random placement seeded once, never per frame
creatures      drawThing(x, y, angle, scale, opts)
environments   reusable backdrops (pond, underwater, sky) parameterised by colour and horizon
scenes         one function per chapter: sName(localTime, dt)
SCENES[]       the script as data: {num, name, sub, dur, draw, chord, scale, caps}
audio          one procedural engine driven by a `mix` object
playback/UI    timeline, transport, keyboard, the rAF loop
```

**Scene contract.** Each scene function receives `lt` (0..dur) and is fully deterministic in `lt` — no accumulated state. That makes seeking free, which you need for both the scrubber and testing. It sets the camera, draws back-to-front, and writes into the global `mix`. The frame loop resets `mix` to defaults each frame, so scenes only declare what they want to hear.

**Keyframes as data.** One Hermite spline through `[t, x, y, ...extra]` rows drives every motion path; repeated rows mean a hold. Derive facing from velocity rather than authoring it:

```js
const [x,y] = spline(KEYS, lt);
const [vx,vy] = vel(KEYS, lt);
const h = heading(vx, vy, prevDir);   // {dir: ±1, pitch}
```

Animate a creature in one place — the draw function — and let paths stay pure position. Extra spline channels (a 0..1 `landed` flag, a `hang` amount) blend poses continuously.

## 3. Making it look drawn, not plotted

- **Pose interpolation.** Author 2–3 keyframe poses per articulated part (fly / stand / dead) as arrays of joint offsets, then `lerp` between them by a 0..1 parameter. Add a small per-joint `sin(t*k + j)` twitch scaled by distance from the body — that jitter is most of the life.
- **Depth inside a subject.** Draw the far-side limbs and wings in a dimmer colour with a small positional offset, then the body, then the near side. Cheap, and it reads as volume.
- **Motion blur for fast cycles.** A wing beating at 60 Hz can't be drawn once per frame. Draw 3–6 translucent ghost copies fanned across the stroke arc, plus one opaque copy at the true phase.
- **Parallax by camera, not by layer lists.** `layer(f)` re-derives the transform at a fraction of the current zoom/pan, so background plates drift correctly for free.
- **Volumetrics beat outlines.** God rays, silt motes, bokeh discs, surface caustics, breath plumes — a few dozen additive shapes do more for atmosphere than any amount of detail on the subject.
- **Grade every frame.** Vignette, film grain (a 160×160 noise pattern offset randomly each frame, `overlay` at ~6%), and per-scene fades. A `saturation` composite pass gives you instant slow-motion or grief.
- **Silhouette first.** If the subject doesn't read as a black shape against the sky, more rendering won't save it.

## 4. Sound, generated

Web Audio only. Build one graph at first user gesture — persistent oscillators and noise sources running into gain nodes that scenes fade via `setTargetAtTime`. Never create a node per frame.

- Beds: filtered noise for wind / water / rain; a chord pad of 4 detuned oscillators through a slowly-swept lowpass.
- Subject: a bandpass-filtered saw pair with vibrato. Modulate its frequency by story state — heavier means lower, slow motion detunes down and closes the master lowpass.
- One-shots on probability per frame: `if (Math.random() < mix.crickets * dt * 2.4) cricket()`. Crickets are a burst of ~4 short 4kHz sine blips; frogs are a falling saw through a lowpass; bubbles are a rising sine.
- Score: give each chapter a `chord` and a pentatonic `scale`; glide the pad to the chord on chapter change and pluck a random scale note every 1.5–4s. That alone makes eight scenes feel like one film.
- A short synthesised convolution reverb (3s of decaying noise) glues everything.

## 5. Playback and interaction

Transport: play/pause, restart, scrubbable timeline segmented by chapter with hover tooltips, speed toggle, captions toggle, mute, fullscreen. Keyboard: `Space`, `←/→`, `1`–`9`, `R`, `M`, `C`, `F`. Auto-hide the UI after ~3s idle; letterbox bars.

Interaction should be *diegetic* — it belongs to the world, not to a control panel. Have the subject bank away from the cursor, click the water for ripples, click the air for a swat the subject flinches from. One shared evasion vector smoothed toward the target keeps it from twitching.

## 6. Build and verify

**Write in parts.** A finished file runs 60–90KB, past a single tool call's output limit. Write `p1.html` (head/CSS/body/controls + opening `<script>`), then `p2.js`…`pN.js`, then `cat` them together and append the closing tags. Keep the split at architectural seams so each part is independently readable.

**Check syntax without a browser** — extract the script and `node --check` it.

**Then actually watch it.** Headless Playwright (Chromium at `/opt/pw-browsers/chromium`; never run `playwright install`):

```js
await p.click('#bBegin');
await p.evaluate(t => seek(t), 88.4);      // works because seek() is a top-level function
await p.screenshot({path: 'beat.png'});
```

Listen for `pageerror` and `console` errors throughout — the rAF loop should `try/catch` and log, so a bad frame surfaces instead of freezing the film. Then:

1. Screenshot **every named story beat** and look at each one. Compute absolute times from the cumulative chapter durations — getting that arithmetic wrong sends you to the wrong moment and you'll "fix" a scene that was fine.
2. Sweep the whole runtime in 2s steps at desktop and phone viewport, confirming zero errors and no horizontal scroll.
3. Sample pixels with PIL when judging a colour — a dark frame next to a black letterbox looks brighter than it is.

**Failures this catches every time:**
- *Two subjects overlapping at the climax.* Draw order fixed at authoring time hides the hero behind the predator exactly when it matters. Draw the hero last during the beat, and open the gap in the keyframes.
- *A punch-in missing.* Wide framing kills a small-subject moment; multiply zoom by the beat's own 0..1 envelope.
- *Environment lighting that ignores the chapter.* A daylight-tinted underwater plate under a night sky. Tint shared environments per scene.
- *Fade windows swallowing a beat*, or captions colliding with the transport bar.

## 7. Delivery

Write the file where the user asked; otherwise send it and offer to publish it as an artifact. In the reply, walk the chapters in one line each, then note the craft that isn't visible from a still — procedural bodies, the audio graph, the interaction — and state what the verification run actually covered.
