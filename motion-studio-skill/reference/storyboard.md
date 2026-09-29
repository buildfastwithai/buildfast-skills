# Concept, storyboard and temporal storytelling

## 1. Concept first (one paragraph)
Name the visual idea (a metaphor, a transformation, a contrast), the arc and where the peak is. A vague brief gets a stronger concept, e.g. "a cool video about AI agents":
- Opening: a human doing repetitive tasks by hand (slow, cluttered, desaturated)
- Transformation: tasks start moving on their own (first automation, a small surprise)
- Escalation: many agents in parallel (density, speed, music builds)
- Payoff: the whole workflow runs itself (clean, bright, still)
- Ending: product/title reveal, held long enough to read and screenshot

## 2. Storyboard (every scene)
```text
Scene 03  0:06.0-0:08.5
Purpose:     the product arrives (reveal)
Visual:      hero UI card, light sweep, blurred background cards
Camera:      slow push 6 %, rack focus from bg to card
Animation:   card springs up, rows stagger in 40 ms apart
Typography:  "Meet Relay." display, 2 words, centred upper third
Transition:  in: radial from the button tap (match position); out: whip left
Audio:       impact on 6.0, shimmer on the sweep, music lifts to energy .8
```
`plan.py --scaffold` writes a storyboard.md skeleton from the template beats; replace every TODO with real decisions.

## 3. Shot list
Derive a shot list (scene id, start/end snapped to beats, assets needed, preset/camera/transition per shot) - this becomes the `C.scene(...)` calls 1:1.

## 4. Temporal storytelling rules
- **Anticipation → action → reaction**: a small counter-move or build before the big move; a settle/overshoot or camera shake after it.
- **Rhythm**: cut and hit on the beat grid (`C.beat`). Vary shot lengths (short-short-long) instead of equal slides.
- **Hierarchy in time**: one focal animation at a time; supporting elements stagger after it.
- **Emphasis**: important moments get the biggest scale change, a sound cue, and ≥ 1 beat of stillness after.
- **Pauses**: use a deliberate still or silent beat before the payoff (trailers: silence before the title). Declare holds (`hold: true`) so QC knows they are intentional.
- **Don't animate everything**: backgrounds drift slowly, only the subject moves decisively.
- **Readability**: ≤ ~3 words/second of on-screen text for display lines; ≥ 1.2 s on screen for any line people must read; ≤ 4.5 words/s overall (QC checks).

## 5. Variation (never scene → fade → scene → fade)
Change at least two of these between neighbouring scenes: composition (centre/left/right/grid), scale (macro/wide), density (1 element vs many), camera (static/push/pan/orbit/shake), typography (size, weight, case, split), transition type, colour/inversion, pace. Use visual callbacks (the ending echoes the opening), match cuts (same shape/position across the cut) and masks/morphs as connective tissue.

## 6. Templates are structure, not layout
templates/*.json give beats with purpose, share of duration, energy and transition intent. Scale them to the requested duration (plan.py does) and then design freely.
