# Audio Recipes for Three.js Games

Use audio to clarify action and state. The game must remain understandable when muted.

## Activation and lifecycle

Browsers require a user gesture before audio can start. Make the first Start/Continue action unlock audio, then resume the audio context on later interactions if it becomes suspended.

The audio system should expose:

- master, music, ambience, and effects gain;
- mute state;
- a one-time unlock method;
- pause/resume behavior;
- cleanup for sources and event listeners.

Persist user volume and mute choices. Do not auto-play loud audio on page load.

## Three.js audio graph

Attach one listener to the active camera:

```js
const listener = new THREE.AudioListener();
camera.add(listener);

const music = new THREE.Audio(listener);
const source = new THREE.PositionalAudio(listener);
worldObject.add(source);
```

Use `THREE.Audio` for non-spatial music, menus, and UI. Use `THREE.PositionalAudio` for sources whose direction and distance matter, such as engines, machinery, enemies, or environmental landmarks.

Tune positional rolloff in the real game scale. An incorrect reference distance can make a sound disappear immediately or remain full-volume across the whole map.

## Feedback hierarchy

Prioritize:

1. player action confirmation;
2. danger, damage, and failure;
3. reward, collection, and completion;
4. state changes such as countdown, pause, or low time;
5. ambience and decorative detail.

Each important event needs a distinct envelope and frequency footprint. Do not make every success a bright chime or every impact the same noise burst.

## Synthesized effects

Web Audio can create small original effects without asset files:

- **Pickup:** short sine or triangle rise, fast decay.
- **Impact:** noise transient plus a pitched body that falls quickly.
- **Jump/boost:** filtered noise with a rising oscillator.
- **Warning:** alternating two-note pulse with a restrained duty cycle.
- **Completion:** layered arpeggio with a longer release.

Randomize pitch and playback rate within a narrow range for repeated footsteps, impacts, or shots. Excessive variation makes feedback ambiguous.

## Layered impacts

A convincing impact often uses:

1. a 5–20 ms transient for immediacy;
2. a short pitched body for size/material;
3. a filtered noise tail for debris or space.

Scale layers from collision energy, but clamp volume. Map material to filtering and pitch: wood is midrange and hollow, metal is brighter with a ringing tail, stone is low and noisy.

## Music and ambience

Keep music adaptive at the level the scope supports:

- crossfade calm and pressure loops;
- add a percussion or bass layer as danger rises;
- filter or duck music during pause and dialogue;
- lower music slightly during critical effect sounds.

Loop boundaries must be clean. If seamless assets are unavailable, use deliberate fades instead of audible clicks.

For ambience, use a few meaningful layers tied to location or game state. Avoid a single loud loop that masks all feedback.

## Accessibility and comfort

- Provide mute and volume controls before or immediately after the first audio gesture.
- Never encode critical information in audio alone.
- Avoid unexpected high-volume peaks.
- Pause or reduce sound when the tab is hidden.
- Respect the user's persisted settings.
- Provide captions or visual signals for important spoken or directional information.

## Verification

Test:

- first interaction unlocks audio without console errors;
- mute, unmute, and sliders work during play;
- pause/resume does not duplicate music or sources;
- restarting a run does not stack listeners;
- positional audio follows the correct object and camera;
- rapid repeated events are rate-limited or pooled;
- hidden-tab and focus-loss behavior is sane;
- the entire loop remains playable with audio disabled.
