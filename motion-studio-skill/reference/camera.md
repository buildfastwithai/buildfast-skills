# Camera

The camera is per scene and moves layers by their depth (parallax): `s.layer(.3)` background moves little, `s.layer(1.6)` foreground moves a lot. The main layer is depth 1.
| move | call | use for |
|---|---|---|
| push / pull (dolly) | `s.push(.06)`, `s.pull(.06)` | building importance / release |
| pan | `s.pan(.08, 0)` | revealing across a wide layout, timelines |
| zoom punch | `s.camera([{t:0,zoom:1},{t:.15,zoom:1.08,ease:'outExpo'},{t:.6,zoom:1}])` | beat hits (energetic) |
| orbit (2.5D) | `s.orbit(14)` | product/hero objects on layers |
| parallax | layers at different depths + any move | depth in flat art |
| shake | `s.shake(at, dur, amp)` (adds an impact cue) | impacts, slams |
| handheld | `s.handheld(amp)` | documentary, horror, found footage, energy |
| rack focus | `s.focus([{t:0,depth:.3},{t:1.2,depth:1,dur:.8}])` | shifting attention between planes |
| perspective change | `s.camera([{t:0, rx: 12, ry: -8}, {t: 3, rx: 0, ry: 0}])` | tilted UI planes settling |
| true 3D | Three.js camera (vendor.py three) | flythroughs, 3D objects |

Motion languages set defaults (`s.M.camera`: push, drift, shake, handheld). The camera must serve the scene: calm and luxury barely move, energetic cuts on punches, mechanical moves in straight lines, glitch jolts. Don't move the camera during dense reading moments.
