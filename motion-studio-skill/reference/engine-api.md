# Engine API (engine/ms.js)

A composition is one `composition.html` that loads `/__spec.js` (the resolved spec: style + motion tokens, format, bpm, seed) and `/engine/ms.js`, then calls `MS.boot(C => { ... })`. `render.py` serves the project folder, so `assets/...` and `vendor/...` paths work.

**Determinism.** Every frame is rebuilt from time `t` alone: element state is reset each frame and re-accumulated from tweens, so frames render in any order, in parallel, reproducibly. Never use CSS animations/transitions, `setTimeout`, `requestAnimationFrame`, `Date`, or unseeded randomness (`Math.random` is already seeded; prefer `MS.rng(seed)` / `MS.hash(n)` / `MS.noise1(x)`).

```html
<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/engine/ms.css"></head><body>
<script src="/__spec.js"></script><script src="/engine/ms.js"></script>
<script>
MS.boot(C => {
  const b = C.beat(1);                                        // seconds per beat at spec.bpm
  C.scene('hook', 0, 4 * b, s => {
    s.bg('mesh');
    const t = s.text('Building software is changing.', { size: 'h1', y: .45, split: 'words' });
    s.anim(t, 'wordReveal', .2);
    s.push(.06);
  }, { energy: .4, purpose: 'establish the problem' });
  C.scene('next', 4 * b, 6 * b, s => { /* ... */ }, { energy: .8 });
  C.transition('hook', 'next', { type: 'auto', intent: 'impact' });
  C.cue(4 * b, 'impact');
});
</script></body></html>
```

## Composition `C`
| member | meaning |
|---|---|
| `C.W, C.H, C.fps, C.duration, C.u` | size; `u` = 1 % of the short side (use for all sizes) |
| `C.vertical, C.square, C.safe {x,y,w,h}` | format flags; title/UI safe area in px |
| `C.uiScale` | 1 / 1.2 / 1.6 (landscape/square/vertical) - UI kit auto-scales |
| `C.theme`, `C.motion` | resolved style + motion tokens (`C.motion.dur.enter`, `C.theme.palette.accent` ...) |
| `C.scene(id, start, dur, build, opts)` | opts: `energy` 0..1 (drives music), `purpose`, `hold: true` (declared stillness) / `'black'`, `bg`, `focusBlur` |
| `C.transition(a, b, {type, dur, dir, intent, at, cue, color, shape})` | `type:'auto'` picks from style+motion preferences; `intent`: impact, reveal, escalate, calm, continue, end, transform |
| `C.cue(t, type, {gain, dur})` | audio event at absolute time (see audio.md) |
| `C.beat(n)`, `C.bar(n)`, `C.snap(t, div)` | beat grid |
| `C.overlay(type, opts)` | extra global overlay (grain, scanlines, vignette, letterbox, chromatic, vhs, crt, halftone, paper, hud, lightleak, film) - style textures are added automatically |
| `C.every(fn(t, C))` | global per-frame hook |
| `C.audio.level(t) / band(t,i) / onsetNear(t) / beatPhase(t)` | audio features (after `audio.py --analyze`) |

## Scene `s` (inside the build function)
Layout coordinates `x, y` are **0..1 of the safe area** (or of the frame with `space:'frame'`); `anchor`: center, left, right, top, bottom, top-left ...
| method | notes |
|---|---|
| `s.bg(type, opts)` | `auto` (style default in a quiet, text-friendly form - e.g. horizon without the sun, line kept low; name the type for the hero version) solid gradient radial mesh grid dots halftone stripes rays speedlines stars flow bokeh skyline horizon paper blueprint aurora |
| `s.hud` | screen-space layer, not moved by the camera: captions, lower thirds, HUD (`layer: s.hud`) |
| `s.layer(depth, name)` | parallax plane: camera moves it `depth`x (bg .25, main 1, foreground 1.5+); sorted back→front by depth |
| `s.text(str, o)` | `size`: display h1 h2 h3 body caption micro or a number (×u); `font`: display/body/mono; `split`: chars/words/lines; `wrap`,`maxWidth`, `color`, `tracking`, `case`, `glow`, `stroke`+`hollow`, `css`. Auto-fits width; registered for QC |
| `s.el(html, o)`, `s.svg(markup, o)`, `s.img(src, o)`, `s.shape(kind, o)`, `s.group(o)` | `o.w/h` (0..1 of safe area or px), `o.size`, `o.layer`, `o.z` ; shapes: circle rect pill triangle diamond hex star |
| `s.anim(node, preset, at, o)` | local time `at`; `o.dur/ease/from/dist/cue` |
| `s.enter(node, at)` / `s.exit(node, at)` | the motion language's own entrance/exit - use these by default |
| `s.tween(node, at, dur, ease, fn(e, st, p, k, node))` | custom animation: add to state `st` (x y z s sx sy r rx ry skx o blur clip track filter bright) |
| `s.every(node, fn(lt, st, node))` | continuous per-frame behaviour |
| `s.particles({type, at, x, y, colors, count, speed, size, gravity})` | burst sparks confetti dust snow rain embers bubbles flow (analytic, seekable) |
| `s.caption(str, at, dur)` | subtitle-style line in the lower safe area |
| `s.morphPath(pathEl, [d1,d2,...], [t1,t2,...])`, `s.textPath(str, d, o)` | shape morph; text along a path |

### Animation presets (`s.anim`)
fadeIn fadeOut fadeUp slideIn slideOut scaleIn scaleOut pop spring blurIn blurOut slam maskReveal wipeIn wipeOut tracking float pulse spin shakeEl drawPath countUp typewriter stagger wordReveal charReveal lineReveal decode glitchText rgbSplit rotateIn flipIn perspectiveIn dropIn moveTo highlight underline strike none.
Durations/easing default to the motion language (`s.M.dur`, `s.M.ease`), and signature channels apply automatically (glitch jolts, organic jitter, stepped time, blur).
Easing names: linear in out inOut inQuad outQuad inOutQuad inCubic outCubic inOutCubic inQuart outQuart inOutQuart outQuint inSine outSine inOutSine inExpo outExpo inOutExpo outCirc inBack outBack outBackStrong outElastic outBounce ease easeIn easeOut easeInOut cinematic smooth snap anticipate, plus `bezier(a,b,c,d)`, `spring(k,d)`, `steps(n)`, `back(s)`, `elastic(a,p)`. Unknown names fall back to `out` with a console warning.
`MS.kinetic(s, phrases, {moves, hold, size})` - a sequence of phrases, one move each, on the beat grid.

### Camera (per scene)
`s.push(amount)`, `s.pull()`, `s.pan(dx, dy)`, `s.orbit(deg)`, `s.camera([{t, x, y, zoom, rot, rx, ry, ease}])`, `s.shake(at, dur, amp)`, `s.handheld(amp)`, `s.drift()`, `s.focus([{t, depth, dur}])` (rack focus; blur = |layer depth − focus|). Details: camera.md.

### Transitions
cut match fade dissolve blur whip push zoom radial iris wipe mask slice flash glitch distortion shape morph particles. Details + selection: transitions.md.

## Kits
- **Charts**: `MS.chart.bar(s, [{label,value}], {x,y,w,h,at,highlight,prefix,suffix})`, `line(s, values|[series], {labels,min,max,at,dur})`, `donut(s, value%, {r,width,at})`, `counter(s, {to,from,at,dur,prefix,suffix,decimals})`, `timeline(s, [{year,text}], {at,step})`, `map(s, [{x,y,label}], {at,dur})` (stylised, non-geographic).
- **UI**: `MS.ui.window`, `card({title,text,icon,at})`, `toast`, `button`, `cursor(s, [{t,x,y,click}])`, `code(s, lines, {at,cps})`, `chat(s, [{who,text,at}])`, `progress({at,dur})`. All scale with `C.uiScale`.
- **Logo**: `MS.logo.reveal(s, svgMarkup, {at, draw, size, stroke, shine})` - stroke draw → fill → shine sweep, with riser/chime cues.
- **Lyrics**: `MS.lyrics(s, [{t, text, end}])`.
- **Canvas**: `MS.canvasLayer(s, (g, W, H, lt) => {...}, {res, depth})` for generative/procedural drawing.
- **Three.js**: `python3 scripts/vendor.py <project> three`, then in a `<script type="module">` import `/vendor/three.module.js`, create the renderer with `preserveDrawingBuffer: true`, add its canvas to a layer and render inside `s.every(null, lt => ...)` (see examples/projects/02-cyberpunk-cinematic).

## Extending
Put new presets/transitions/backgrounds in `engine/extensions/<name>.js` (`MS.presets.x = (s, n, at, o) => ...`, `MS.transitions.x = (C, tr, p, o) => ...`); they are appended to ms.js automatically. `python3 scripts/extend.py new-preset <name>` writes a stub.
