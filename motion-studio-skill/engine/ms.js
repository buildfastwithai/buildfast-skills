/* Motion Studio engine (ms.js) — deterministic, seekable motion graphics in the browser.
 *
 * Every frame is a pure function of time: render(t) rebuilds the visual state from scratch,
 * so frames can be rendered in any order, in parallel, and reproducibly (benchmark mode).
 * Nothing uses CSS animations, Date or unseeded Math.random.
 *
 * A composition:
 *   MS.boot(C => {
 *     C.scene("hook", 0, 3.5, s => {
 *       s.bg("mesh");
 *       const t = s.text("Building software is changing.", {size:"h1", y:.5});
 *       s.enter(t, .3, {split:"words"});
 *       s.push(.06);                                   // camera
 *     }, {energy:.4});
 *     C.transition("hook", "next", {type:"auto"});
 *     C.cue(3.5, "impact");
 *   });
 * Full API: reference/engine-api.md
 */
(function () {
  'use strict';
  const MS = { version: '1.0.0', presets: {}, transitions: {}, overlays: {}, backgrounds: {}, chart: {}, ui: {}, logo: {} };
  const SPEC = window.MS_SPEC || {};
  const RENDER = !!window.__MS_RENDER;

  // ------------------------------------------------------------------ math & determinism
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const seg = (t, a, b) => clamp((t - a) / (b - a));
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function hash(n) { let x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
  function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; }
  function noise2(x, y) { return noise1(x + noise1(y * 1.7) * 3.1 + y * 57.3); }
  function fbm(x, o = 3) { let s = 0, a = .5, f = 1; for (let i = 0; i < o; i++) { s += a * noise1(x * f + i * 19.1); a *= .5; f *= 2; } return s; }
  const SEED = (SPEC.seed == null ? 1234 : SPEC.seed) >>> 0;
  Math.random = mulberry32(SEED ^ 0x9e3779b9);           // determinism: no unseeded randomness
  Date.now = () => 0; if (window.performance) performance.now = () => 0;
  MS.rng = seed => mulberry32((seed >>> 0) ^ SEED);
  Object.assign(MS, { clamp, lerp, seg, noise1, noise2, fbm, hash });

  // ------------------------------------------------------------------ easing
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = t => ((ax * t + bx) * t + cx) * t, sy = t => ((ay * t + by) * t + cy) * t, dx = t => (3 * ax * t + 2 * bx) * t + cx;
    return p => { if (p <= 0) return 0; if (p >= 1) return 1; let t = p; for (let i = 0; i < 8; i++) { const e = sx(t) - p, d = dx(t); if (Math.abs(e) < 1e-6 || !d) break; t -= e / d; }
      let lo = 0, hi = 1; for (let i = 0; i < 20 && Math.abs(sx(t) - p) > 1e-5; i++) { if (sx(t) < p) lo = t; else hi = t; t = (lo + hi) / 2; } return sy(t); };
  }
  function spring(k = 170, c = 14, m = 1) {
    const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m)), wd = w0 * Math.sqrt(Math.max(1e-6, 1 - z * z));
    const f = t => z < 1 ? 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t)) : 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    return p => p >= 1 ? 1 : f(p * 1.0) + (1 - f(1.0)) * p;       // exact 1 at p=1
  }
  const steps = n => p => p >= 1 ? 1 : Math.floor(p * n) / n;
  const back = (s = 1.70158) => p => { p -= 1; return p * p * ((s + 1) * p + s) + 1; };
  const elastic = (a = 1, per = .35) => p => p <= 0 ? 0 : p >= 1 ? 1 : a * Math.pow(2, -10 * p) * Math.sin((p - per / 4) * (2 * Math.PI) / per) + 1;
  const bounce = p => { const n = 7.5625, d = 2.75; if (p < 1 / d) return n * p * p; if (p < 2 / d) return n * (p -= 1.5 / d) * p + .75; if (p < 2.5 / d) return n * (p -= 2.25 / d) * p + .9375; return n * (p -= 2.625 / d) * p + .984375; };
  const NAMED = {
    linear: p => p, in: p => p * p * p, out: p => 1 - Math.pow(1 - p, 3), inOut: p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2,
    inQuad: p => p * p, outQuad: p => 1 - (1 - p) * (1 - p), outQuart: p => 1 - Math.pow(1 - p, 4), outQuint: p => 1 - Math.pow(1 - p, 5),
    inExpo: p => p === 0 ? 0 : Math.pow(2, 10 * p - 10), outExpo: p => p === 1 ? 1 : 1 - Math.pow(2, -10 * p),
    inOutExpo: p => p === 0 ? 0 : p === 1 ? 1 : p < .5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2,
    inOutSine: p => -(Math.cos(Math.PI * p) - 1) / 2, outSine: p => Math.sin(p * Math.PI / 2), outCirc: p => Math.sqrt(1 - Math.pow(p - 1, 2)),
    outBack: back(), outBackStrong: back(2.6), outElastic: elastic(), outBounce: bounce,
    inOutQuad: p => p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2, inCubic: p => p * p * p, outCubic: p => 1 - Math.pow(1 - p, 3), inOutCubic: p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2,
    inQuart: p => p * p * p * p, inOutQuart: p => p < .5 ? 8 * p * p * p * p : 1 - Math.pow(-2 * p + 2, 4) / 2, inSine: p => 1 - Math.cos(p * Math.PI / 2), inBack: p => 2.70158 * p * p * p - 1.70158 * p * p,
    ease: bezier(.25, .1, .25, 1), easeIn: bezier(.42, 0, 1, 1), easeOut: bezier(0, 0, .58, 1), easeInOut: bezier(.42, 0, .58, 1),
    cinematic: bezier(.7, 0, .2, 1), smooth: bezier(.45, 0, .2, 1), snap: bezier(.2, 1, .3, 1), anticipate: bezier(.6, -.35, .3, 1.35),
  };
  MS.ease = function (e) {
    if (typeof e === 'function') return e; if (!e) return NAMED.out;
    if (NAMED[e]) return NAMED[e];
    const m = String(e).match(/^(\w+)\(([^)]*)\)$/);
    if (m) { const a = m[2].split(',').map(Number);
      if (m[1] === 'bezier' || m[1] === 'cubic-bezier') return bezier(...a);
      if (m[1] === 'spring') return spring(...a); if (m[1] === 'steps') return steps(a[0]);
      if (m[1] === 'back') return back(a[0]); if (m[1] === 'elastic') return elastic(a[0], a[1]); }
    console.warn('unknown easing', e); return NAMED.out;
  };
  MS.easings = NAMED;

  // ------------------------------------------------------------------ composition
  const DEF_MOTION = { id: 'default', ease: { enter: 'outQuart', exit: 'in', move: 'smooth', emphasis: 'outBack', camera: 'inOutSine' },
    dur: { enter: .6, exit: .4, move: .8, emphasis: .5, hold: 1 }, stagger: { chars: .025, words: .07, lines: .12, items: .09 },
    dist: 5, overshoot: 1.1, blur: 0, jitter: 0, step_fps: 0, glitch: 0, camera: { push: .05, drift: .15, shake: 0, handheld: 0 },
    transitions: { prefer: ['dissolve', 'wipe', 'zoom'], dur: .6 }, enter: 'fadeUp', exit: 'fadeOut' };
  const DEF_STYLE = { id: 'default', palette: { bg: '#0b0b10', bg2: '#16161f', surface: '#1b1b26', fg: '#f4f2ee', muted: '#9a9aae', accent: '#ff3d7f', accent2: '#3de0ff', accent3: '#ffd23d', line: '#ffffff1f' },
    fonts: { display: 'Inter:800', body: 'Inter:400', mono: 'JetBrains Mono:400' }, type: { case: 'none', tracking: -.01, lead: 1.02 },
    radius: 18, stroke: 2, shadow: '0 30px 80px rgba(0,0,0,.45)', glow: 0, texture: [], background: 'solid', transitions: {} };

  function fontCss(f) { const [fam, w = '400', st] = String(f).split(':'); return { family: `'${fam}'`, weight: w.replace('i', ''), style: /i$/.test(w) || st === 'italic' ? 'italic' : 'normal', raw: fam }; }

  class Composition {
    constructor(spec) {
      this.spec = spec; this.W = spec.width || 1920; this.H = spec.height || 1080; this.fps = spec.fps || 30; this.duration = spec.duration || 10;
      this.u = Math.min(this.W, this.H) / 100; this.vertical = this.H > this.W * 1.1; this.square = !this.vertical && this.W < this.H * 1.15;
      this.uiScale = spec.ui_scale || (this.vertical ? 1.6 : this.square ? 1.2 : 1);   // UI kits read larger on phones: recompose, don't just resize
      this.theme = deepMerge(DEF_STYLE, spec.style || {}); this.motion = deepMerge(DEF_MOTION, spec.motion || {});
      this.bpm = spec.bpm || (spec.audio && spec.audio.bpm) || 120; this.vars = spec.vars || {};
      const sf = spec.safe || (this.vertical ? { x: .07, y: .13, w: .86, h: .67 } : { x: .06, y: .08, w: .88, h: .84 });
      this.safe = { x: sf.x * this.W, y: sf.y * this.H, w: sf.w * this.W, h: sf.h * this.H };
      this.minTextPx = spec.min_text_px || Math.round(2.2 * this.u);
      this.scenes = []; this.transitions = []; this.cues = []; this.overlays = []; this.globalFns = []; this.texts = [];
      this.rand = MS.rng(1);
      this.stage = document.createElement('div'); this.stage.id = 'ms-stage';
      Object.assign(this.stage.style, { width: this.W + 'px', height: this.H + 'px' });
      document.body.appendChild(this.stage);
      this.applyTheme();
      this.defs = svgEl('svg', { width: 0, height: 0, style: 'position:absolute' });
      this.defs.innerHTML = `<defs>
        <filter id="ms-rgb" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">
          <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r"/><feOffset in="r" dx="0" dy="0" result="ro"/>
          <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" result="gb"/><feOffset in="gb" dx="0" dy="0" result="gbo"/>
          <feBlend in="ro" in2="gbo" mode="screen"/></filter>
        <filter id="ms-disp" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.002 0.08" numOctaves="1" seed="1" result="n"/>
          <feDisplacementMap in="SourceGraphic" in2="n" scale="0" xChannelSelector="R" yChannelSelector="G"/></filter>
        <filter id="ms-warp" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="3" result="n"/>
          <feDisplacementMap in="SourceGraphic" in2="n" scale="0" xChannelSelector="R" yChannelSelector="G"/></filter></defs>`;
      document.body.appendChild(this.defs);
      this.overlayRoot = div('ms-overlay'); this.overlayRoot.style.zIndex = 50; this.stage.appendChild(this.overlayRoot);
      this.flash = div('ms-overlay'); this.flash.style.zIndex = 60; this.flash.style.opacity = 0; this.stage.appendChild(this.flash);
      this.fx = div('ms-overlay'); this.fx.style.zIndex = 55; this.stage.appendChild(this.fx);    // transition overlays
      this.audio = makeAudio(spec.__features);
    }
    applyTheme() {
      const T = this.theme, P = T.palette, st = this.stage.style, u = this.u;
      for (const k in P) st.setProperty('--' + k, P[k]);
      const fd = fontCss(T.fonts.display), fb = fontCss(T.fonts.body), fm = fontCss(T.fonts.mono || 'JetBrains Mono:400');
      st.setProperty('--font-display', `${fd.family}, ${T.fonts.fallback || 'sans-serif'}`); st.setProperty('--font-body', `${fb.family}, sans-serif`); st.setProperty('--font-mono', `${fm.family}, monospace`);
      st.setProperty('--w-display', fd.weight); st.setProperty('--w-body', fb.weight); st.setProperty('--u', u + 'px');
      st.setProperty('--radius', (T.radius * u / 10.8) + 'px'); st.setProperty('--stroke', T.stroke + 'px'); st.setProperty('--shadow', T.shadow || 'none');
      if (!P.surface) st.setProperty('--surface', P.bg2); if (!P.line) st.setProperty('--line', '#ffffff1f');
      this.fonts = { display: fd, body: fb, mono: fm };
    }
    // --- structure
    scene(id, start, dur, build, opts = {}) {
      const s = new Scene(this, id, start, dur, opts); this.scenes.push(s);
      s.root.style.display = 'block';                       // laid out while building (text fitting, line splitting, path lengths)
      if (build) { const r = build(s); if (r && r.then) throw new Error('scene builders must be synchronous'); }
      s.root.style.display = 'none';
      return s;
    }
    sceneById(id) { const s = this.scenes.find(x => x.id === id); if (!s) throw new Error('no scene ' + id); return s; }
    transition(a, b, opts = {}) {
      const A = this.sceneById(a), B = this.sceneById(b);
      let type = opts.type || 'auto'; if (type === 'auto') type = this.autoTransition(this.transitions.length, opts.intent);
      const dur = opts.dur != null ? opts.dur : (type === 'cut' || type === 'match' ? 0 : (TRANS_DUR[type] || this.motion.transitions.dur || .6));
      const tr = { a: A, b: B, at: opts.at != null ? opts.at : B.start, dur, type, opts };
      this.transitions.push(tr);
      const cueType = opts.cue !== undefined ? opts.cue : TRANS_CUE[type];
      if (cueType) this.cue(tr.at - (type === 'flash' || type === 'glitch' || type === 'shape' ? 0 : dur * .5), cueType, { auto: true, dur });
      return tr;
    }
    autoTransition(i, intent) {
      const pref = (this.theme.transitions && this.theme.transitions.prefer) || [], mpref = this.motion.transitions.prefer || [];
      const avoid = new Set([...(this.theme.transitions.avoid || []), ...(this.motion.transitions.avoid || [])]);
      let pool = mpref.filter(x => pref.includes(x)); if (pool.length < 2) pool = [...new Set([...mpref, ...pref])];
      pool = pool.filter(x => !avoid.has(x) && MS.transitions[x]); if (!pool.length) pool = ['dissolve'];
      if (intent && INTENT[intent]) { const hit = INTENT[intent].find(x => pool.includes(x) || (MS.transitions[x] && !avoid.has(x))); if (hit) return hit; }
      return pool[i % pool.length];
    }
    cue(t, type, opts = {}) { this.cues.push(Object.assign({ t: +t.toFixed(4), type }, opts)); }
    beat(n = 1) { return n * 60 / this.bpm; }
    bar(n = 1) { return this.beat(4 * n); }
    snap(t, div = 1) { const b = this.beat(1) / div; return Math.round(t / b) * b; }
    overlay(type, opts = {}) { if (!MS.overlays[type]) { console.warn('unknown overlay', type); return; } this.overlays.push(MS.overlays[type](this, opts)); }
    every(fn) { this.globalFns.push(fn); }
    finalize() {
      this.scenes.sort((a, b) => a.start - b.start);
      if (this.spec.overlays !== false) for (const tx of (this.theme.texture || [])) { const [k, v] = String(tx).split(':'); if (MS.overlays[k] && !this.overlays.some(o => o.type === k)) this.overlay(k, v ? { amount: +v } : {}); }
    }
    // --- per-frame
    render(t) {
      t = clamp(t, 0, this.duration - 1e-6); this.t = t; this.frame = Math.round(t * this.fps);
      const active = new Map();
      for (const s of this.scenes) if (t >= s.start && t < s.end) active.set(s, true);
      const trs = this.transitions.filter(tr => t >= tr.at - tr.dur / 2 && t < tr.at + tr.dur / 2 && tr.dur > 0);
      for (const tr of trs) { active.set(tr.a, true); active.set(tr.b, true); }
      for (const s of this.scenes) { const on = active.has(s); s.root.style.display = on ? 'block' : 'none'; if (on) { s.resetRoot(); s.update(t - s.start); } }
      this.fx.innerHTML = ''; this.flash.style.opacity = 0; this.stage.style.filter = ''; this.stage.style.background = ''; this.stage.style.transform = this.devScale || '';
      for (const tr of trs) { const p = clamp((t - (tr.at - tr.dur / 2)) / tr.dur); (MS.transitions[tr.type] || MS.transitions.dissolve)(this, tr, p, tr.opts); }
      for (const o of this.overlays) o.update(t);
      for (const fn of this.globalFns) fn(t, this);
    }
    meta() {
      return { engine: MS.version, width: this.W, height: this.H, fps: this.fps, duration: this.duration, bpm: this.bpm, seed: SEED,
        scenes: this.scenes.map(s => ({ id: s.id, start: s.start, end: s.end, energy: s.opts.energy, purpose: s.opts.purpose || '', hold: s.opts.hold || null })),
        transitions: this.transitions.map(tr => ({ from: tr.a.id, to: tr.b.id, at: tr.at, dur: tr.dur, type: tr.type })),
        cues: this.cues.slice().sort((a, b) => a.t - b.t), texts: this.texts.length,
        textList: this.texts.map(n => { const sc = n.closest && n.closest('.ms-scene'); const tx = String(n.dataset && n.dataset.label || n.textContent || '').trim(); return { scene: sc ? sc.dataset.scene : '', words: tx.split(/\s+/).filter(Boolean).length, text: tx.slice(0, 80) }; }), safe: this.safe, minTextPx: this.minTextPx,
        style: this.theme.id, motion: this.motion.id };
    }
    audit(t) {
      const dt = 1.5 / this.fps; this.render(Math.min(this.duration - 1e-6, t + dt));        // where is each text a moment later?
      const later = new Map(); for (const n of this.texts) if (n.isConnected) { const r = inkRect(n); later.set(n, [r.left, r.top, r.width]); }
      this.render(t); const issues = [], sr = this.stage.getBoundingClientRect(), sc = sr.width / this.W;
      for (const n of this.texts) {
        if (!n.isConnected || !visible(n, this.stage)) continue;
        const box = n.getBoundingClientRect(), r = inkRect(n); if (r.width < 1 || r.height < 1) continue;   // judge the glyphs, not the (auto-fit) text box
        const x0 = (r.left - sr.left) / sc, y0 = (r.top - sr.top) / sc, x1 = (r.right - sr.left) / sc, y1 = (r.bottom - sr.top) / sc;
        const label = (n.dataset.label || n.textContent).slice(0, 40), scale = box.height / Math.max(1, n.offsetHeight);
        const px = minFont(n) * scale;
        const L = later.get(n), moving = L && (Math.abs(L[0] - r.left) + Math.abs(L[1] - r.top) > 1.5 || Math.abs(L[2] - r.width) > 1.5);
        const rest = !moving && scale > .95 && scale < 1.05 && opacityOf(n, this.stage) > .95;   // only judge settled text (entrances may start off-frame)
        if (x0 < -2 || y0 < -2 || x1 > this.W + 2 || y1 > this.H + 2) issues.push({ t, kind: 'offframe', severity: rest ? 'error' : 'info', text: label, box: [x0, y0, x1, y1].map(Math.round) });
        else if (rest && !n.dataset.free && (x0 < this.safe.x - 2 || y0 < this.safe.y - 2 || x1 > this.safe.x + this.safe.w + 2 || y1 > this.safe.y + this.safe.h + 2))
          issues.push({ t, kind: 'unsafe', severity: 'warn', text: label, box: [x0, y0, x1, y1].map(Math.round) });
        if (rest && px < this.minTextPx) issues.push({ t, kind: 'small-text', severity: 'warn', text: label, px: Math.round(px), min: this.minTextPx });
        if (n.scrollWidth > n.clientWidth + 3 && getComputedStyle(n).overflow !== 'visible') issues.push({ t, kind: 'overflow', severity: 'error', text: label });
      }
      return issues;
    }
  }
  const AUTO_BG = { horizon: { sunY: .82, sun: false } };                       // keep the horizon line below typical text positions
  const TRANS_DUR = { cut: 0, match: 0, fade: .8, dissolve: .6, whip: .45, zoom: .6, radial: .7, wipe: .6, mask: .7, glitch: .35, distortion: .7, particles: .9, flash: .3, shape: .8, morph: .9, push: .6, slice: .7, blur: .6, iris: .7 };
  const TRANS_CUE = { whip: 'whoosh', zoom: 'whoosh', push: 'swoosh', wipe: 'swoosh', glitch: 'glitch', distortion: 'glitch', flash: 'impact', shape: 'swoosh', morph: 'shimmer', particles: 'shimmer', radial: 'swoosh', slice: 'swoosh' };
  const INTENT = { impact: ['flash', 'glitch', 'whip', 'cut'], reveal: ['radial', 'mask', 'iris', 'shape', 'wipe'], escalate: ['whip', 'zoom', 'push', 'glitch'],
    calm: ['dissolve', 'fade', 'blur'], continue: ['match', 'cut', 'push'], end: ['fade', 'dissolve', 'iris'], transform: ['morph', 'shape', 'particles', 'distortion'] };

  function deepMerge(a, b) { const o = Array.isArray(a) ? a.slice() : Object.assign({}, a); for (const k in b) { if (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a && typeof a[k] === 'object' && !Array.isArray(a[k])) o[k] = deepMerge(a[k], b[k]); else o[k] = b[k]; } return o; }
  function div(cls, parent) { const d = document.createElement('div'); if (cls) d.className = cls; if (parent) parent.appendChild(d); return d; }
  function svgEl(tag, attrs = {}, parent) { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
  function opacityOf(n, stop) { let o = 1; for (let e = n; e && e !== stop; e = e.parentElement) o *= +getComputedStyle(e).opacity; return o; }
  function inkRect(n) {                                   // bounding box of the rendered text itself (transforms included)
    const rg = document.createRange(); rg.selectNodeContents(n); const b = rg.getBoundingClientRect();
    return b.width > 0 && b.height > 0 ? b : n.getBoundingClientRect();
  }
  function minFont(el) {                                  // smallest font actually rendered inside el (containers like UI cards hold several sizes)
    let m = Infinity; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let tn;
    while ((tn = w.nextNode())) if (tn.textContent.trim()) m = Math.min(m, parseFloat(getComputedStyle(tn.parentElement).fontSize));
    return m === Infinity ? parseFloat(getComputedStyle(el).fontSize) : m; }
  function visible(n, stop) { for (let e = n; e && e !== stop; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; } return opacityOf(n, stop) > .4; }
  MS.util = { div, svgEl, deepMerge, fontCss };

  // ------------------------------------------------------------------ scene
  const ANCHORS = { center: [.5, .5], left: [0, .5], right: [1, .5], top: [.5, 0], bottom: [.5, 1], 'top-left': [0, 0], 'top-right': [1, 0], 'bottom-left': [0, 1], 'bottom-right': [1, 1] };
  class Scene {
    constructor(C, id, start, dur, opts) {
      this.C = C; this.id = id; this.start = start; this.dur = dur; this.end = start + dur; this.opts = opts; this.M = C.motion;
      this.root = div('ms-scene'); this.root.dataset.scene = id; C.stage.insertBefore(this.root, C.overlayRoot);
      if (opts.bg !== undefined) this.root.style.setProperty('--scene-bg', opts.bg); else this.root.style.setProperty('--scene-bg', 'var(--bg)');
      this.rig = div('ms-rig', this.root); this.layers = []; this.tweens = []; this.nodes = new Set(); this.camKeys = null; this.camFns = []; this.fns = [];
      this.main = this.layer(1, 'main'); this.rng = MS.rng(hashStr(id));
      this.hud = div('ms-layer', this.root); this.hud.dataset.name = 'hud'; this.hud.style.zIndex = 5;   // screen space: not moved by the camera (captions, HUD, lower thirds)
    }
    resetRoot() { const s = this.root.style; s.opacity = 1; s.transform = ''; s.clipPath = ''; s.filter = ''; s.zIndex = ''; s.visibility = 'visible'; }
    layer(depth = 1, name) { const l = div('ms-layer', this.rig); l.dataset.depth = depth; l.depth = depth; if (name) l.dataset.name = name;
      this.layers.push(l); this.layers.sort((a, b) => a.depth - b.depth); for (const x of this.layers) this.rig.appendChild(x); return l; }
    // --- element state (reset every frame, then accumulated by tweens)
    track(n) { if (!n.__st) { n.__base = n.__base || ''; } this.nodes.add(n); return n; }
    place(n, o = {}) {
      const C = this.C, sp = o.space === 'frame' ? { x: 0, y: 0, w: C.W, h: C.H } : C.safe;
      const px = sp.x + (o.x == null ? .5 : o.x) * sp.w, py = sp.y + (o.y == null ? .5 : o.y) * sp.h;
      const a = ANCHORS[o.anchor || 'center'] || o.anchor;
      n.style.position = 'absolute'; n.style.left = px + 'px'; n.style.top = py + 'px';
      if (o.w != null) n.style.width = (o.w <= 1.5 ? o.w * sp.w : o.w) + 'px'; if (o.h != null) n.style.height = (o.h <= 1.5 ? o.h * sp.h : o.h) + 'px';
      n.__base = `translate(${-a[0] * 100}%,${-a[1] * 100}%)`; n.style.transformOrigin = o.origin || `${a[0] * 100}% ${a[1] * 100}%`;
      if (o.z != null) n.style.zIndex = o.z;
      (o.layer || this.main).appendChild(n); this.track(n); return n;
    }
    el(html, o = {}) { const t = document.createElement('template'); t.innerHTML = String(html).trim(); const n = t.content.firstElementChild; if (o.cls) n.classList.add(...o.cls.split(' ')); if (o.style) n.style.cssText += o.style; return this.place(n, o); }
    group(o = {}) { const g = div('ms-abs'); return this.place(g, o); }
    svg(markup, o = {}) { markup = uniqIds(/^\s*<svg/.test(markup) ? markup : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${o.viewBox || '0 0 100 100'}">${markup}</svg>`); const n = this.el(markup, o);
      if (o.size) { n.style.width = (o.size <= 1.5 ? o.size * this.C.safe.h : o.size) + 'px'; n.style.height = 'auto'; } n.style.overflow = 'visible'; return n; }
    img(src, o = {}) { const n = this.el(`<img src="${src}">`, o); if (o.size) n.style.width = (o.size <= 1.5 ? o.size * this.C.safe.h : o.size) + 'px'; return n; }
    shape(kind, o = {}) {
      const u = this.C.u, sz = (o.size || 20) * u, col = o.color || 'var(--accent)';
      let n;
      if (kind === 'circle' || kind === 'rect' || kind === 'pill') { n = div('ms-abs'); Object.assign(n.style, { width: (o.w || o.size || 20) * u + 'px', height: (o.h || o.size || 20) * u + 'px', background: o.fill === false ? 'none' : col,
        border: o.stroke ? `${o.stroke}px solid ${o.strokeColor || col}` : 'none', borderRadius: kind === 'circle' || kind === 'pill' ? '9999px' : (o.radius != null ? o.radius * u + 'px' : 'var(--radius)') }); }
      else { const pts = { triangle: '50,4 96,92 4,92', diamond: '50,2 98,50 50,98 2,50', hex: '25,6 75,6 98,50 75,94 25,94 2,50', star: starPts(5, 48, 20) }[kind] || kind;
        n = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); n.setAttribute('viewBox', '0 0 100 100'); n.style.width = n.style.height = sz + 'px'; n.style.overflow = 'visible';
        n.innerHTML = `<polygon points="${pts}" fill="${o.fill === false ? 'none' : col}" stroke="${o.stroke ? (o.strokeColor || col) : 'none'}" stroke-width="${o.stroke || 0}" vector-effect="non-scaling-stroke"/>`; }
      return this.place(n, o);
    }
    text(str, o = {}) {
      const C = this.C, T = C.theme, u = C.u, n = div('ms-text');
      const role = o.font || (typeof o.size === 'number' ? (o.size >= 5 ? 'display' : 'body') : ['display', 'h1', 'h2'].includes(o.size || 'h1') ? 'display' : 'body');
      const f = C.fonts[role] || C.fonts.body, sizes = { display: 13, h1: 8.5, h2: 6, h3: 4.6, body: 3.6, caption: 2.9, micro: 2.3 };
      let px = typeof o.size === 'number' ? o.size * u : (sizes[o.size || 'h1'] || 8.5) * u * (role === 'display' ? (T.type.display_scale || 1) : 1);
      n.style.fontFamily = `${f.family}, sans-serif`; n.style.fontWeight = o.weight || f.weight; n.style.fontStyle = o.italic ? 'italic' : f.style;
      n.style.fontSize = px + 'px'; n.style.color = o.color || 'var(--fg)'; n.style.textAlign = o.align || 'center';
      n.style.lineHeight = o.lead || (role === 'display' ? T.type.lead || 1.02 : 1.3);
      const tr = o.tracking != null ? o.tracking : (role === 'display' ? T.type.tracking || 0 : 0); n.style.letterSpacing = tr + 'em';
      const caseT = o.case || (role === 'display' ? T.type.case : 'none'); if (caseT === 'upper') str = String(str).toUpperCase(); if (caseT === 'lower') str = String(str).toLowerCase();
      if (o.glow || (role === 'display' && T.glow && o.glow !== false)) { const g = o.glow || T.glow; n.style.textShadow = `0 0 ${.8 * g}em ${o.glowColor || 'var(--accent)'}`; }
      if (o.stroke) { n.style.webkitTextStroke = `${o.stroke}px ${o.strokeColor || 'var(--fg)'}`; if (o.hollow) n.style.color = 'transparent'; }
      if (o.css) n.style.cssText += o.css;
      // room left by the anchor: left-anchored text at x can only use (1 - x) of the safe width, centred text 2*min(x, 1-x)
      const ax = o.x != null ? o.x : .5, an = o.anchor || 'center', room = o.space === 'frame' ? 1 : /left/.test(an) ? 1 - ax : /right/.test(an) ? ax : 2 * Math.min(ax, 1 - ax);
      const maxW = Math.min(o.maxWidth || (o.wrap ? .9 : 1), Math.max(.2, room)) * C.safe.w; n.dataset.label = str;
      if (o.wrap) { n.classList.add('wrap'); n.style.width = maxW + 'px'; }
      n.__split = o.split || null; this.fillText(n, str, o.split);
      this.place(n, o); C.texts.push(n);
      if (o.fit !== false && !o.wrap) fitText(n, maxW * .95 /* headroom for camera push-ins */, px, o.minSize ? o.minSize * u : C.minTextPx);
      if (o.split === 'lines') splitLines(n);
      return n;
    }
    fillText(n, str, split) {
      n.innerHTML = '';
      if (split === 'chars') { for (const ch of str) { if (ch === '\n') { n.appendChild(document.createElement('br')); continue; } const c = document.createElement('span'); c.className = 'c'; c.textContent = ch; n.appendChild(c); } }
      else if (split === 'words' || split === 'lines') { str.split(/(\s+)/).forEach(w => { if (!w) return; if (/^\s+$/.test(w)) { if (w.includes('\n')) n.appendChild(document.createElement('br')); else n.appendChild(document.createTextNode(' ')); return; } const s = document.createElement('span'); s.className = 'w'; s.textContent = w; n.appendChild(s); }); }
      else n.textContent = str;
    }
    parts(n) { return n.querySelectorAll(n.__split === 'chars' ? '.c' : n.__split === 'lines' ? '.ln > span' : '.w'); }
    // --- tweens
    tween(node, at, dur, ease, fn, o = {}) { if (node) this.track(node); this.tweens.push({ node, at, dur: Math.max(dur, 1e-4), ease: MS.ease(ease), fn, step: o.step != null ? o.step : this.M.step_fps }); return this; }
    every(node, fn) { if (node) this.track(node); this.fns.push({ node, fn }); return this; }
    anim(node, preset, at = 0, o = {}) { const P = MS.presets[preset]; if (!P) throw new Error('unknown preset ' + preset); P(this, node, at, o); if (o.cue) this.C.cue(this.start + at + (o.cueOffset || 0), o.cue); return this; }
    enter(node, at = 0, o = {}) { return this.anim(node, o.preset || this.M.enter, at, o); }
    exit(node, at, o = {}) { return this.anim(node, o.preset || this.M.exit, at == null ? this.dur - (this.M.dur.exit || .4) : at, o); }
    // --- camera
    camera(keys, o = {}) { this.camKeys = keys.slice().sort((a, b) => a.t - b.t); this.camEase = MS.ease(o.ease || this.M.ease.camera); return this; }
    push(amount, o = {}) { const a = amount != null ? amount : this.M.camera.push; return this.camera([{ t: o.from || 0, zoom: 1 }, { t: o.to || this.dur, zoom: 1 + a }], o); }
    pull(amount, o = {}) { const a = amount != null ? amount : this.M.camera.push; return this.camera([{ t: 0, zoom: 1 + a }, { t: this.dur, zoom: 1 }], o); }
    pan(dx = .05, dy = 0, o = {}) { return this.camera([{ t: 0, x: -dx / 2, y: -dy / 2 }, { t: this.dur, x: dx / 2, y: dy / 2 }], o); }
    orbit(deg = 14, o = {}) { return this.camera([{ t: 0, ry: -deg / 2, zoom: o.zoom || 1 }, { t: this.dur, ry: deg / 2, zoom: (o.zoom || 1) * (1 + (o.push || 0)) }], o); }
    shake(at, dur = .5, amp = 1.2) { this.camFns.push((lt, cam) => { const k = lt - at; if (k < 0 || k > dur) return; const d = Math.pow(1 - k / dur, 2) * amp * this.C.u; cam.sx += noise1(k * 38 + 1) * d; cam.sy += noise1(k * 41 + 9) * d; cam.rot += noise1(k * 29 + 4) * d * .05; }); this.C.cue(this.start + at, 'impact', { auto: true, gain: .8 }); return this; }
    handheld(amp) { const a = (amp != null ? amp : (this.M.camera.handheld || .35)) * this.C.u; this.camFns.push((lt, cam) => { cam.sx += fbm(lt * .8 + 3) * a; cam.sy += fbm(lt * .7 + 11) * a; cam.rot += fbm(lt * .5 + 7) * .15 * (a / this.C.u); }); return this; }
    drift(amount) { const a = amount != null ? amount : this.M.camera.drift; this.camFns.push((lt, cam) => { cam.x += Math.sin(lt * .31 + 1) * .01 * a; cam.y += Math.sin(lt * .23 + 2) * .008 * a; }); return this; }
    focus(keys) { this.focusKeys = keys; return this; }                   // rack focus: [{t, depth}] ; blur = |layerDepth - focus| * focusBlur
    camAt(lt) {
      const cam = { x: 0, y: 0, zoom: 1, rot: 0, rx: 0, ry: 0, sx: 0, sy: 0 };
      if (this.camKeys) { const K = this.camKeys; for (const prop of ['x', 'y', 'zoom', 'rot', 'rx', 'ry']) { const ks = K.filter(k => k[prop] != null); if (!ks.length) continue;
          if (lt <= ks[0].t) cam[prop] = ks[0][prop]; else if (lt >= ks[ks.length - 1].t) cam[prop] = ks[ks.length - 1][prop];
          else for (let i = 0; i < ks.length - 1; i++) if (lt >= ks[i].t && lt < ks[i + 1].t) { const e = MS.ease(ks[i + 1].ease || this.camEase); cam[prop] = lerp(ks[i][prop], ks[i + 1][prop], e((lt - ks[i].t) / (ks[i + 1].t - ks[i].t))); } } }
      for (const f of this.camFns) f(lt, cam);
      return cam;
    }
    // --- sugar
    bg(type = 'auto', o = {}) {   // 'auto' = the style's background in its quiet, content-friendly form (hero set-ups: call the type by name)
      if (type === 'auto') { type = this.C.theme.background || 'solid'; o = Object.assign({}, AUTO_BG[type] || {}, o); } const B = MS.backgrounds[type]; if (!B) throw new Error('unknown background ' + type); return B(this, o); }
    particles(o = {}) { return makeParticles(this, o); }
    caption(str, at, dur, o = {}) { const n = this.text(str, Object.assign({ size: 'body', y: this.C.vertical ? .92 : .93, font: 'body', weight: 600, layer: this.hud }, o)); this.anim(n, 'fadeUp', at, { dur: .25 }); this.anim(n, 'fadeOut', at + dur, { dur: .2 }); return n; }
    // --- per frame
    update(lt) {
      for (const n of this.nodes) n.__st = { x: 0, y: 0, z: 0, s: 1, sx: 1, sy: 1, r: 0, rx: 0, ry: 0, skx: 0, o: 1, blur: 0, clip: null, track: null, filter: '', bright: 1 };
      for (const tw of this.tweens) {
        let k = lt - tw.at; if (tw.step > 0) k = Math.floor(k * tw.step) / tw.step;
        const p = clamp(k / tw.dur); tw.fn(tw.ease(p), tw.node ? tw.node.__st : null, p, k, tw.node);
      }
      for (const f of this.fns) f.fn(lt, f.node ? f.node.__st : null, f.node);
      for (const n of this.nodes) applyState(n);
      const cam = this.camAt(lt), W = this.C.W, H = this.C.H;
      let fb = null; if (this.focusKeys) { const ks = this.focusKeys; fb = ks[0].depth; for (let i = 0; i < ks.length; i++) if (lt >= ks[i].t) fb = i + 1 < ks.length ? lerp(ks[i].depth, ks[i + 1].depth, NAMED.inOut(seg(lt, ks[i].t, ks[i].t + (ks[i].dur || .8)))) : ks[i].depth; }
      for (const l of this.layers) { const d = l.depth;
        l.style.transform = `translate(${-cam.x * W * d}px,${-cam.y * H * d}px) scale(${1 + (cam.zoom - 1) * d})`;
        l.style.filter = fb == null ? '' : `blur(${(Math.abs(d - fb) * (this.opts.focusBlur || 1.2) * this.C.u).toFixed(2)}px)`; }
      this.rig.style.transform = `perspective(${this.C.W * 1.2}px) translate(${cam.sx}px,${cam.sy}px) rotateX(${cam.rx}deg) rotateY(${cam.ry}deg) rotate(${cam.rot}deg)`;
    }
  }
  let UID = 0;
  function uniqIds(m) {                                     // the same SVG may be placed many times: keep gradient/filter/clip ids unique
    const ids = [...m.matchAll(/\bid="([^"]+)"/g)].map(x => x[1]); if (!ids.length) return m; const k = '-u' + (++UID);
    for (const id of ids) { const e = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); m = m.replace(new RegExp(`id="${e}"`, 'g'), `id="${id}${k}"`).replace(new RegExp(`url\\(#${e}\\)`, 'g'), `url(#${id}${k})`).replace(new RegExp(`href="#${e}"`, 'g'), `href="#${id}${k}"`); }
    return m; }
  MS.uniqIds = uniqIds;
  function hashStr(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  function starPts(n, R, r) { const p = []; for (let i = 0; i < n * 2; i++) { const a = -Math.PI / 2 + i * Math.PI / n, rr = i % 2 ? r : R; p.push((50 + rr * Math.cos(a)).toFixed(1) + ',' + (50 + rr * Math.sin(a)).toFixed(1)); } return p.join(' '); }
  function applyState(n) {
    const s = n.__st; if (!s) return;
    n.style.transform = `${n.__base} translate3d(${s.x.toFixed(2)}px,${s.y.toFixed(2)}px,${s.z}px) rotate(${s.r}deg) rotateX(${s.rx}deg) rotateY(${s.ry}deg) skewX(${s.skx}deg) scale(${(s.s * s.sx).toFixed(4)},${(s.s * s.sy).toFixed(4)})`;
    n.style.opacity = clamp(s.o).toFixed(4);
    const f = (s.blur > .05 ? `blur(${s.blur.toFixed(2)}px) ` : '') + (s.bright !== 1 ? `brightness(${s.bright}) ` : '') + s.filter; n.style.filter = f.trim();
    n.style.clipPath = s.clip || ''; if (s.track != null) n.style.letterSpacing = s.track + 'em';
    n.style.visibility = s.o <= 0.001 ? 'hidden' : 'visible';
  }
  function fitText(n, maxW, px, minPx) { let size = px; for (let i = 0; i < 40 && n.scrollWidth > maxW && size > minPx; i++) { size *= .95; n.style.fontSize = size + 'px'; } if (n.scrollWidth > maxW) n.dataset.overflow = '1'; }
  function splitLines(n) {
    const words = [...n.querySelectorAll('.w')], lines = []; let top = null;
    for (const w of words) { const tp = w.offsetTop; if (top === null || Math.abs(tp - top) > 2) { lines.push([]); top = tp; } lines[lines.length - 1].push(w); }
    n.innerHTML = ''; for (const ln of lines) { const L = document.createElement('span'); L.className = 'ln'; const inner = document.createElement('span'); inner.style.display = 'inline-block';
      ln.forEach((w, i) => { inner.appendChild(w); if (i < ln.length - 1) inner.appendChild(document.createTextNode(' ')); }); L.appendChild(inner); n.appendChild(L); }
  }
  MS.Scene = Scene;

  // ------------------------------------------------------------------ presets (animation primitives)
  const P = MS.presets;
  const U = s => s.C.u;
  const D = (s, o, k) => o.dur != null ? o.dur : s.M.dur[k];
  const E = (s, o, k) => o.ease || s.M.ease[k];
  function dirVec(d) { return { up: [0, 1], bottom: [0, 1], down: [0, -1], top: [0, -1], left: [-1, 0], right: [1, 0] }[d || 'bottom'] || [0, 1]; }
  function glitchy(s, node, at, dur) {                                          // motion-language glitch: discontinuous offsets during entrances
    const g = s.M.glitch || 0; if (!g) return; const r = MS.rng(hashStr(at + node.textContent));
    s.tween(node, at, dur + .15, 'linear', (e, st, p, k) => { const f = Math.floor(k * 24); if (k < 0 || p >= 1 || hash(f + at * 99) > .35 * g + .15) return;
      st.x += (hash(f * 3.1 + 7) - .5) * 5 * U(s) * g; st.skx += (hash(f * 5.3) - .5) * 20 * g; st.filter += ` drop-shadow(${3 * g}px 0 0 #ff0040) drop-shadow(${-3 * g}px 0 0 #00e5ff)`; });
  }
  function jitterAt(s, node, at) { const j = s.M.jitter || 0; return j ? at + (hash(hashStr(node.textContent || '') % 997) - .5) * j * .25 : at; }
  P.fadeIn = (s, n, at, o) => s.tween(n, at, D(s, o, 'enter'), E(s, o, 'enter'), (e, st) => { st.o *= e; });
  P.fadeOut = (s, n, at, o) => s.tween(n, at, D(s, o, 'exit'), E(s, o, 'exit'), (e, st) => { st.o *= 1 - e; });
  P.fadeUp = (s, n, at, o) => { at = jitterAt(s, n, at); const d = (o.dist || s.M.dist) * U(s), v = dirVec(o.from);
    s.tween(n, at, D(s, o, 'enter'), E(s, o, 'enter'), (e, st) => { st.o *= Math.min(1, e * 1.6); st.x += v[0] * d * (1 - e); st.y += v[1] * d * (1 - e); if (s.M.blur) st.blur += s.M.blur * (1 - e) * U(s) * .3; }); glitchy(s, n, at, D(s, o, 'enter')); };
  P.slideIn = (s, n, at, o) => { const v = dirVec(o.from || 'left'), d = (o.dist || 30) * U(s);
    s.tween(n, at, D(s, o, 'enter'), E(s, o, 'enter'), (e, st) => { st.x += v[0] * d * (1 - e); st.y += v[1] * d * (1 - e); st.o *= Math.min(1, e * 3); }); glitchy(s, n, at, D(s, o, 'enter')); };
  P.slideOut = (s, n, at, o) => { const v = dirVec(o.to || 'left'), d = (o.dist || 30) * U(s);
    s.tween(n, at, D(s, o, 'exit'), E(s, o, 'exit'), (e, st) => { st.x -= v[0] * d * e; st.y -= v[1] * d * e; st.o *= 1 - Math.max(0, e * 1.5 - .5); }); };
  P.scaleIn = (s, n, at, o) => { const f = o.from != null ? o.from : .82; s.tween(n, at, D(s, o, 'enter'), E(s, o, 'enter'), (e, st) => { st.s *= lerp(f, 1, e); st.o *= Math.min(1, e * 2); }); glitchy(s, n, at, D(s, o, 'enter')); };
  P.scaleOut = (s, n, at, o) => { const f = o.to != null ? o.to : 1.15; s.tween(n, at, D(s, o, 'exit'), E(s, o, 'exit'), (e, st) => { st.s *= lerp(1, f, e); st.o *= 1 - e; }); };
  P.pop = (s, n, at, o) => { s.tween(n, at, D(s, o, 'emphasis'), o.ease || s.M.ease.emphasis, (e, st) => { st.s *= Math.max(0, e); }); s.tween(n, at, .08, 'linear', (e, st) => { st.o *= e; }); glitchy(s, n, at, .3); };
  P.spring = (s, n, at, o) => { const d = (o.dist || s.M.dist * 2) * U(s), v = dirVec(o.from); s.tween(n, at, o.dur || .9, o.ease || 'spring(160,11)', (e, st) => { st.x += v[0] * d * (1 - e); st.y += v[1] * d * (1 - e); st.s *= lerp(.9, 1, e); }); s.tween(n, at, .12, 'linear', (e, st) => { st.o *= e; }); };
  P.blurIn = (s, n, at, o) => s.tween(n, at, o.dur || Math.min(1.1, D(s, o, 'enter')), E(s, o, 'enter'), (e, st) => { st.o *= e; st.blur += (1 - e) * (o.amount || 2.2) * U(s); st.s *= lerp(o.from || 1.06, 1, e); });
  P.blurOut = (s, n, at, o) => s.tween(n, at, D(s, o, 'exit'), E(s, o, 'exit'), (e, st) => { st.o *= 1 - e; st.blur += e * 3 * U(s); });
  P.slam = (s, n, at, o) => { s.tween(n, at, o.dur || .32, o.ease || 'outExpo', (e, st) => { st.s *= lerp(o.from || 2.6, 1, e); st.blur += (1 - e) * 1.5 * U(s); st.o *= Math.min(1, e * 4); });
    if (o.shake !== false) s.shake(at + (o.dur || .32) * .8, .4, o.amp || 1.1); };
  P.maskReveal = (s, n, at, o) => { const v = dirVec(o.from || 'bottom'); s.tween(n, at, D(s, o, 'enter') * 1.2, E(s, o, 'enter'), (e, st) => {
    const r = ((1 - e) * 100).toFixed(2); st.clip = v[1] > 0 ? `inset(${r}% 0 0 0)` : v[1] < 0 ? `inset(0 0 ${r}% 0)` : v[0] < 0 ? `inset(0 ${r}% 0 0)` : `inset(0 0 0 ${r}%)`;
    st.y += v[1] * (1 - e) * 1.5 * U(s); }); };
  P.wipeIn = (s, n, at, o) => s.tween(n, at, D(s, o, 'enter') * 1.2, E(s, o, 'enter'), (e, st) => { st.clip = `inset(0 ${((1 - e) * 100).toFixed(2)}% 0 0)`; });
  P.wipeOut = (s, n, at, o) => s.tween(n, at, D(s, o, 'exit'), E(s, o, 'exit'), (e, st) => { st.clip = `inset(0 0 0 ${(e * 100).toFixed(2)}%)`; });
  P.tracking = (s, n, at, o) => { const a = o.from != null ? o.from : .6, b = o.to != null ? o.to : parseFloat(n.style.letterSpacing) || 0; s.tween(n, at, o.dur || 1.6, o.ease || s.M.ease.move, (e, st) => { st.track = lerp(a, b, e); st.o *= Math.min(1, e * 2.5); }); };
  P.float = (s, n, at, o) => s.every(n, (lt, st) => { const k = Math.max(0, lt - at); st.y += Math.sin(k * (o.speed || 1.1) + (o.phase || 0)) * (o.amp || 1) * U(s); st.r += Math.sin(k * .7 + 1) * (o.rot || 0); });
  P.pulse = (s, n, at, o) => s.every(n, (lt, st) => { const k = Math.max(0, lt - at); st.s *= 1 + Math.sin(k * Math.PI * 2 * (o.freq || s.C.bpm / 60)) * (o.amp || .03); });
  P.spin = (s, n, at, o) => s.every(n, (lt, st) => { st.r += Math.max(0, lt - at) * (o.speed || 30); });
  P.shakeEl = (s, n, at, o) => s.tween(n, at, o.dur || .4, 'linear', (e, st, p, k) => { if (k < 0 || p >= 1) return; const a = (1 - p) * (o.amp || 1) * U(s); st.x += noise1(k * 40 + 2) * a; st.y += noise1(k * 43 + 5) * a; });
  P.drawPath = (s, n, at, o) => { const els = [...n.querySelectorAll('path,line,polyline,polygon,circle,ellipse,rect')].filter(e => e.getAttribute('stroke') !== 'none' || o.all);
    els.forEach((el, i) => { let L = 0; try { L = el.getTotalLength(); } catch (e) { L = 1000; } el.style.strokeDasharray = L; const t0 = at + i * (o.stagger != null ? o.stagger : .05);
      s.tween(null, t0, o.dur || 1.2, o.ease || s.M.ease.move, e => { el.style.strokeDashoffset = (L * (1 - e)).toFixed(2); el.style.strokeOpacity = e > .002 ? '' : 0; }); }); s.track(n); };   // hide round-cap dots of undrawn paths
  P.countUp = (s, n, at, o) => { const a = o.from || 0, b = o.to != null ? o.to : parseFloat(n.textContent), dec = o.decimals || 0, fmt = o.format || (v => (o.prefix || '') + v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (o.suffix || ''));
    s.tween(n, at, o.dur || 1.4, o.ease || 'outExpo', e => { n.textContent = fmt(lerp(a, b, e)); }); };
  function ensureSplit(s, n, kind) { if (n.__split === kind || (kind === 'words' && n.__split)) return; n.__split = kind; s.fillText(n, n.dataset.label, kind); }
  MS.ensureSplit = ensureSplit;
  P.typewriter = (s, n, at, o) => { ensureSplit(s, n, 'chars'); const cs = s.parts(n), cps = o.cps || 28, caret = o.caret !== false;
    cs.forEach((c, i) => { s.track(c); s.tween(c, at + i / cps, .001, 'linear', (e, st) => { st.o *= e; c.style.display = e > 0 ? 'inline-block' : 'none'; }); });
    if (caret) { const cr = document.createElement('span'); cr.textContent = '▌'; cr.style.cssText = 'display:inline-block;color:var(--accent);margin-left:.05em'; n.appendChild(cr); s.track(cr);
      const end = at + cs.length / cps; s.every(cr, (lt, st) => { st.o *= lt < at ? 0 : (lt < end ? 1 : (Math.floor((lt - end) * 2.2) % 2 ? 0 : 1)) * (o.caretHold != null && lt > end + o.caretHold ? 0 : 1); }); }
    if (o.cue !== false) for (let i = 0; i < cs.length; i += 2) s.C.cue(s.start + at + i / cps, 'type', { auto: true, gain: .5 }); };
  P.stagger = (s, n, at, o) => { ensureSplit(s, n, o.by || 'words'); const parts = s.parts(n), each = o.each || 'fadeUp', gap = o.stagger != null ? o.stagger : s.M.stagger[n.__split === 'chars' ? 'chars' : n.__split === 'lines' ? 'lines' : 'words'];
    parts.forEach((c, i) => { const k = o.order === 'random' ? hash(i * 7.7 + at) * parts.length : o.order === 'center' ? Math.abs(i - (parts.length - 1) / 2) : i; P[each](s, c, at + k * gap, Object.assign({}, o, { cue: null })); }); };
  P.wordReveal = (s, n, at, o) => P.stagger(s, n, at, Object.assign({ each: o.each || 'fadeUp' }, o));
  P.charReveal = (s, n, at, o) => P.stagger(s, n, at, Object.assign({ each: o.each || 'fadeUp', dist: 2, by: 'chars' }, o));
  P.lineReveal = (s, n, at, o) => { const lines = n.querySelectorAll('.ln > span'); lines.forEach((l, i) => { s.track(l); s.tween(l, at + i * (o.stagger || s.M.stagger.lines), D(s, o, 'enter') * 1.3, E(s, o, 'enter'), (e, st) => { st.y += (1 - e) * 110 / 100 * l.offsetHeight; }); }); };
  const GLYPHS = '!<>-_\\/[]{}—=+*^?#_ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
  P.decode = (s, n, at, o) => { ensureSplit(s, n, 'chars'); const cs = s.parts(n), dur = o.dur || .9, spread = o.spread || .5;
    cs.forEach((c, i) => { const real = c.textContent, t0 = at + (i / Math.max(1, cs.length)) * spread; s.track(c);
      s.tween(c, at, t0 + dur - at, 'linear', (e, st, p, k) => { const lt = at + k; if (lt < t0) { st.o *= 0; return; } if (lt >= t0 + dur * .6 || real === ' ') { c.textContent = real; return; }
        c.textContent = GLYPHS[Math.floor(hash(i * 13.1 + Math.floor(lt * 30)) * GLYPHS.length)]; st.filter += ' opacity(.8)'; }); });
    if (o.cue !== false) s.C.cue(s.start + at, 'glitch', { auto: true, gain: .4 }); };
  P.glitchText = (s, n, at, o) => { const dur = o.dur || .6, amt = o.amount || 1; s.tween(n, at, dur, 'linear', (e, st, p, k) => { if (k < 0 || p >= 1) return; const f = Math.floor(k * 30);
    if (hash(f + 3.3) > .45) { st.x += (hash(f * 1.7) - .5) * 4 * U(s) * amt; st.skx += (hash(f * 2.3) - .5) * 30 * amt; }
    st.filter += ` drop-shadow(${(4 * amt * (1 - p)).toFixed(1)}px 0 0 #ff2050) drop-shadow(${(-4 * amt * (1 - p)).toFixed(1)}px 0 0 #20e0ff)`;
    if (hash(f * 9.1) > .8) st.clip = `inset(${(hash(f) * 60).toFixed(0)}% 0 ${(hash(f + 1) * 30).toFixed(0)}% 0)`; });
    if (o.cue !== false) s.C.cue(s.start + at, 'glitch', { auto: true }); };
  P.rgbSplit = (s, n, at, o) => s.every(n, (lt, st) => { if (lt < at) return; const a = (o.amount || 3) * (1 + .6 * Math.sin(lt * 9)); st.filter += ` drop-shadow(${a}px 0 0 #ff2050cc) drop-shadow(${-a}px 0 0 #20e0ffcc)`; });
  P.rotateIn = (s, n, at, o) => s.tween(n, at, D(s, o, 'enter'), E(s, o, 'enter'), (e, st) => { st.r += (o.deg || -12) * (1 - e); st.o *= Math.min(1, e * 2); st.s *= lerp(.9, 1, e); });
  P.flipIn = (s, n, at, o) => s.tween(n, at, D(s, o, 'enter') * 1.3, E(s, o, 'enter'), (e, st) => { st.rx += (o.deg || 80) * (1 - e); st.o *= Math.min(1, e * 2); });
  P.perspectiveIn = (s, n, at, o) => s.tween(n, at, D(s, o, 'enter') * 1.6, E(s, o, 'enter'), (e, st) => { st.ry += (o.deg || -35) * (1 - e); st.z += -40 * U(s) * (1 - e); st.o *= e; });
  P.dropIn = (s, n, at, o) => { s.tween(n, at, o.dur || .8, 'outBounce', (e, st) => { st.y -= (1 - e) * (o.dist || 40) * U(s); }); s.tween(n, at, .1, 'linear', (e, st) => { st.o *= e; }); };
  P.moveTo = (s, n, at, o) => s.tween(n, at, D(s, o, 'move'), E(s, o, 'move'), (e, st) => { st.x += (o.dx || 0) * U(s) * e; st.y += (o.dy || 0) * U(s) * e; st.s *= lerp(1, o.scale || 1, e); st.r += (o.rot || 0) * e; });
  P.highlight = (s, n, at, o) => { const bar = div('ms-abs'); bar.style.cssText = `left:-.08em;right:-.08em;top:${o.top || 58}%;bottom:${o.bottom || 6}%;background:${o.color || 'var(--accent)'};z-index:-1;transform-origin:0 50%`; n.style.position = n.style.position || 'absolute'; n.appendChild(bar); s.track(bar); s.tween(bar, at, o.dur || .5, E(s, o, 'move'), (e, st) => { st.sx *= e; }); };
  P.underline = (s, n, at, o) => P.highlight(s, n, at, Object.assign({ top: 96, bottom: -8 }, o));
  P.strike = (s, n, at, o) => P.highlight(s, n, at, Object.assign({ top: 48, bottom: 44, color: o.color || 'var(--accent)' }, o));
  P.none = () => { };
  // kinetic typography: a sequence of phrases, each with its own move, on the beat grid
  MS.kinetic = function (s, phrases, o = {}) {
    const moves = o.moves || ['slam', 'slideIn', 'scaleIn', 'maskReveal', 'rotateIn', 'tracking', 'decode'];
    const out = []; let t = o.at || 0;
    phrases.forEach((ph, i) => { const p = typeof ph === 'string' ? { text: ph } : ph, hold = p.hold || o.hold || s.C.beat(2), mv = p.move || moves[i % moves.length];
      const n = s.text(p.text, Object.assign({ size: p.size || o.size || 'display', split: mv === 'decode' ? 'chars' : p.split, y: p.y != null ? p.y : .5, color: p.color }, o.textOpts || {}, p.opts || {}));
      s.anim(n, mv, t, Object.assign({ from: p.from }, p.animOpts || {})); if (p.cue !== false) s.C.cue(s.start + t, p.cue || (mv === 'slam' ? 'impact' : 'tick'), { auto: true, gain: .7 });
      if (i < phrases.length - 1 || o.exitLast) s.anim(n, p.exit || o.exit || 'scaleOut', t + hold - .15, { dur: .15 });
      out.push({ node: n, at: t }); t += hold; });
    return out;
  };

  // ------------------------------------------------------------------ transitions
  const TR = MS.transitions;
  function both(tr) { return [tr.a.root.style, tr.b.root.style]; }
  TR.cut = (C, tr, p) => { const [a, b] = both(tr); if (p < .5) b.visibility = 'hidden'; else a.visibility = 'hidden'; };
  TR.match = TR.cut;
  TR.fade = (C, tr, p, o) => { const [a, b] = both(tr); a.opacity = 1 - seg(p, 0, .5); b.opacity = seg(p, .5, 1); tr.b.root.style.zIndex = 2; C.stage.style.background = o.through || '#000'; };
  TR.dissolve = (C, tr, p) => { const [, b] = both(tr); b.opacity = NAMED.inOutSine(p); b.zIndex = 2; };
  TR.blur = (C, tr, p) => { const [a, b] = both(tr); const e = NAMED.inOutSine(p); b.opacity = e; b.zIndex = 2; a.filter = `blur(${e * 2 * C.u}px)`; b.filter = `blur(${(1 - e) * 2 * C.u}px)`; };
  TR.whip = (C, tr, p, o) => { const [a, b] = both(tr); const d = (o.dir || 'left') === 'left' ? -1 : 1, e = NAMED.inOutExpo(p), W = C.W, bl = Math.sin(p * Math.PI) * 3.2 * C.u;
    a.transform = `translateX(${d * e * W}px) scaleX(${1 + Math.sin(p * Math.PI) * .15})`; b.transform = `translateX(${d * (e - 1) * W}px) scaleX(${1 + Math.sin(p * Math.PI) * .15})`; a.filter = b.filter = `blur(${bl}px)`; b.zIndex = 2; };
  TR.push = (C, tr, p, o) => { const [a, b] = both(tr); const e = MS.ease(C.motion.ease.move)(p), v = (o.dir || 'up') === 'up' ? [0, -1] : o.dir === 'down' ? [0, 1] : o.dir === 'right' ? [1, 0] : [-1, 0];
    a.transform = `translate(${v[0] * e * C.W}px,${v[1] * e * C.H}px)`; b.transform = `translate(${v[0] * (e - 1) * C.W}px,${v[1] * (e - 1) * C.H}px)`; };
  TR.zoom = (C, tr, p) => { const [a, b] = both(tr); const e = NAMED.inOutExpo(p); a.transform = `scale(${1 + e * 2.2})`; a.opacity = 1 - seg(p, .35, .6); a.filter = `blur(${e * 2 * C.u}px)`;
    b.transform = `scale(${lerp(.55, 1, NAMED.outExpo(seg(p, .35, 1)))})`; b.opacity = seg(p, .35, .6); b.zIndex = 2; };
  TR.radial = (C, tr, p, o) => { const [, b] = both(tr); const e = MS.ease(C.motion.ease.move)(p), R = Math.hypot(C.W, C.H); b.clipPath = `circle(${(e * R).toFixed(1)}px at ${(o.x != null ? o.x : .5) * 100}% ${(o.y != null ? o.y : .5) * 100}%)`; b.zIndex = 2; };
  TR.iris = (C, tr, p) => { const [a, b] = both(tr); const R = Math.hypot(C.W, C.H) / 2;
    if (p < .5) a.clipPath = `circle(${((1 - NAMED.in(p * 2)) * R).toFixed(1)}px at 50% 50%)`; else { a.visibility = 'hidden'; b.clipPath = `circle(${(NAMED.out((p - .5) * 2) * R).toFixed(1)}px at 50% 50%)`; } C.stage.style.background = '#000'; };
  TR.wipe = (C, tr, p, o) => { const [, b] = both(tr); const e = MS.ease(C.motion.ease.move)(p), dir = o.dir || 'right'; b.zIndex = 2;
    b.clipPath = dir === 'right' ? `inset(0 ${(100 - e * 100).toFixed(2)}% 0 0)` : dir === 'left' ? `inset(0 0 0 ${(100 - e * 100).toFixed(2)}%)` : dir === 'down' ? `inset(0 0 ${(100 - e * 100).toFixed(2)}% 0)` : `inset(${(100 - e * 100).toFixed(2)}% 0 0 0)`;
    if (o.edge !== false && p > 0 && p < 1) { const bar = div('ms-abs', C.fx); const horiz = dir === 'right' || dir === 'left'; const pos = dir === 'right' ? e : dir === 'left' ? 1 - e : dir === 'down' ? e : 1 - e;
      bar.style.cssText = horiz ? `left:${pos * C.W - C.u * .5}px;top:0;width:${C.u}px;height:100%;background:var(--accent);box-shadow:0 0 ${3 * C.u}px var(--accent)` : `top:${pos * C.H - C.u * .5}px;left:0;height:${C.u}px;width:100%;background:var(--accent);box-shadow:0 0 ${3 * C.u}px var(--accent)`; } };
  TR.mask = (C, tr, p, o) => { const [, b] = both(tr); const e = MS.ease(C.motion.ease.move)(p) * 1.5; b.zIndex = 2;
    b.clipPath = `polygon(0 0, ${(e * 100).toFixed(2)}% 0, ${((e - .5) * 100).toFixed(2)}% 100%, 0 100%)`; };
  TR.slice = (C, tr, p, o) => { const [, b] = both(tr); const n = o.n || 7, H = C.H, W = C.W; let d = ''; b.zIndex = 2;
    for (let i = 0; i < n; i++) { const e = MS.ease(C.motion.ease.move)(seg(p, i / n * .5, i / n * .5 + .5)), y0 = i * H / n, y1 = (i + 1) * H / n + 1, x = i % 2 ? W * (1 - e) : 0, w = W * e; d += `M${x} ${y0}H${x + w}V${y1}H${x}Z`; }
    b.clipPath = `path('${d}')`; };
  TR.flash = (C, tr, p, o) => { TR.cut(C, tr, p); C.flash.style.background = o.color || '#fff'; C.flash.style.opacity = Math.max(0, 1 - Math.abs(p - .5) * 2.4); };
  TR.glitch = (C, tr, p, o) => { const [a, b] = both(tr); const f = Math.floor(p * 14), show = hash(f + 1.7) > p ? 'a' : 'b';
    (show === 'a' ? b : a).visibility = 'hidden'; const amt = Math.sin(p * Math.PI) * (o.amount || 1);
    setRGB(C, (hash(f * 3) - .5) * 30 * amt, (hash(f * 5) - .5) * 8 * amt); setDisp(C, 'ms-disp', 60 * amt * (hash(f * 7) > .3 ? 1 : 0), f);
    C.stage.style.filter = 'url(#ms-rgb) url(#ms-disp)'; if (hash(f * 11) > .7) { C.flash.style.background = 'var(--accent)'; C.flash.style.opacity = .12; } };
  TR.distortion = (C, tr, p) => { const [a, b] = both(tr); b.opacity = NAMED.inOutSine(p); b.zIndex = 2; setDisp(C, 'ms-warp', Math.sin(p * Math.PI) * 14 * C.u, 3); a.filter = b.filter = 'url(#ms-warp)'; };
  TR.shape = (C, tr, p, o) => { const [a, b] = both(tr); const sh = div('ms-abs', C.fx), R = Math.hypot(C.W, C.H), kind = o.shape || 'circle', col = o.color || 'var(--accent)';
    const e = p < .5 ? NAMED.inOutExpo(p * 2) : 1 - NAMED.inOutExpo((p - .5) * 2); if (p < .5) b.visibility = 'hidden'; else a.visibility = 'hidden';
    const s = e * R * 1.1; sh.style.cssText = `left:${C.W / 2 - s / 2}px;top:${C.H / 2 - s / 2}px;width:${s}px;height:${s}px;background:${col};border-radius:${kind === 'circle' ? '50%' : kind === 'square' ? '4%' : '0'};transform:rotate(${kind === 'diamond' ? 45 + p * 90 : p * 90}deg)`; };
  TR.morph = (C, tr, p, o) => { const [a, b] = both(tr); if (p < .5) b.visibility = 'hidden'; else a.visibility = 'hidden';
    const e = p < .5 ? NAMED.inOutExpo(p * 2) : 1 - NAMED.inOutExpo((p - .5) * 2), W = C.W, H = C.H, cx = W / 2, cy = H / 2, r = C.u * 6 + e * Math.hypot(W, H) * .55;
    const k = NAMED.inOut(Math.min(1, e * 1.4)), svg = svgEl('svg', { width: W, height: H, style: 'position:absolute;left:0;top:0' }, C.fx);
    const circ = n => { const pts = []; for (let i = 0; i < n; i++) { const t = i / n * Math.PI * 2; pts.push([cx + Math.cos(t) * r, cy + Math.sin(t) * r]); } return pts; };
    const blob = circ(64).map(([x, y], i) => { const t = i / 64 * Math.PI * 2, w = 1 + .18 * Math.sin(t * 3 + p * 6) * (1 - k); return [cx + (x - cx) * w, cy + (y - cy) * w]; });
    svgEl('path', { d: 'M' + blob.map(q => q.map(v => v.toFixed(1)).join(' ')).join('L') + 'Z', fill: o.color || 'var(--accent)' }, svg); };
  TR.particles = (C, tr, p, o) => { const [a, b] = both(tr); a.opacity = 1 - seg(p, .1, .6); b.opacity = seg(p, .4, .9); b.zIndex = 2;
    const cv = document.createElement('canvas'); cv.width = C.W / 2; cv.height = C.H / 2; cv.className = 'ms-canvas'; cv.style.width = C.W + 'px'; cv.style.height = C.H + 'px'; C.fx.appendChild(cv);
    const g = cv.getContext('2d'), col = getComputedStyle(C.stage).getPropertyValue('--accent').trim() || '#fff', n = 900, k = Math.sin(p * Math.PI);
    g.fillStyle = col; for (let i = 0; i < n; i++) { const x0 = hash(i) * cv.width, y0 = hash(i + .5) * cv.height, ang = hash(i * 3.3) * 6.283, sp = 40 + hash(i * 7.1) * 260;
      const x = x0 + Math.cos(ang) * sp * p + (hash(i * 9) - .5) * 40 * p, y = y0 + Math.sin(ang) * sp * p - 60 * p * p; g.globalAlpha = k * (.4 + .6 * hash(i * 2.2)); g.fillRect(x, y, 2 + hash(i * 5) * 3, 2 + hash(i * 5) * 3); } };
  function setRGB(C, dx, dy) { const offs = C.defs.querySelectorAll('#ms-rgb feOffset'); offs[0].setAttribute('dx', dx); offs[0].setAttribute('dy', dy); offs[1].setAttribute('dx', -dx); offs[1].setAttribute('dy', -dy); }
  function setDisp(C, id, scale, seed) { const f = C.defs.querySelector('#' + id); f.querySelector('feDisplacementMap').setAttribute('scale', scale); f.querySelector('feTurbulence').setAttribute('seed', 1 + (seed % 50)); }
  MS.fx = { setRGB, setDisp };

  // ------------------------------------------------------------------ backgrounds
  const BG = MS.backgrounds;
  function bgLayer(s, o, depth = .25) { const l = s.layer(o.depth != null ? o.depth : depth, 'bg'); return l; }
  BG.solid = (s, o) => { const l = bgLayer(s, o); l.style.background = o.color || 'var(--bg)'; return l; };
  BG.gradient = (s, o) => { const l = bgLayer(s, o); l.style.background = `linear-gradient(${o.angle || 160}deg, ${o.from || 'var(--bg2)'}, ${o.to || 'var(--bg)'})`; l.style.inset = '-10%'; return l; };
  BG.radial = (s, o) => { const l = bgLayer(s, o); l.style.background = `radial-gradient(ellipse at ${o.at || '50% 40%'}, ${o.from || 'var(--bg2)'} 0%, ${o.to || 'var(--bg)'} ${o.size || 70}%)`; l.style.inset = '-10%'; return l; };
  BG.mesh = (s, o) => { const l = bgLayer(s, o); l.style.inset = '-15%'; l.style.background = o.base || 'var(--bg)'; const cols = o.colors || ['var(--accent)', 'var(--accent2)', 'var(--accent3)', 'var(--bg2)'];
    const blobs = cols.map((c, i) => { const b = div('ms-abs', l); b.style.cssText = `width:${60 + i * 8}%;height:${60 + i * 8}%;border-radius:50%;background:radial-gradient(closest-side, ${c} 0%, transparent 100%);opacity:${o.opacity || .55}`; return b; });
    s.every(null, lt => { blobs.forEach((b, i) => { const sp = o.speed || .12; b.style.left = (20 + 30 * Math.sin(lt * sp + i * 2.1)) + '%'; b.style.top = (10 + 25 * Math.cos(lt * sp * .8 + i * 1.3)) + '%'; b.style.transform = 'translate(-30%,-20%)'; }); }); return l; };
  BG.grid = (s, o) => { const l = bgLayer(s, o, o.depth || .6), g = (o.size || 6) * s.C.u, c = o.color || 'var(--line)';
    l.style.inset = '-20%'; l.style.backgroundImage = `linear-gradient(${c} 1px, transparent 1px), linear-gradient(90deg, ${c} 1px, transparent 1px)`; l.style.backgroundSize = `${g}px ${g}px`;
    if (o.floor) { l.style.transform = 'perspective(600px) rotateX(62deg)'; l.style.top = '45%'; l.style.transformOrigin = '50% 0'; }
    if (o.scroll) s.every(null, lt => { l.style.backgroundPosition = `0 ${(lt * o.scroll * s.C.u) % g}px`; }); return l; };
  BG.dots = (s, o) => { const l = bgLayer(s, o, .5), g = (o.size || 4) * s.C.u; l.style.inset = '-20%'; l.style.backgroundImage = `radial-gradient(${o.color || 'var(--line)'} ${o.r || 1.4}px, transparent ${(o.r || 1.4) + .6}px)`; l.style.backgroundSize = `${g}px ${g}px`; return l; };
  BG.halftone = (s, o) => { const l = bgLayer(s, o, .4); l.style.inset = '-20%'; l.style.backgroundImage = `radial-gradient(${o.color || 'rgba(0,0,0,.18)'} 30%, transparent 32%)`; l.style.backgroundSize = `${(o.size || 1.4) * s.C.u}px ${(o.size || 1.4) * s.C.u}px`; return l; };
  BG.stripes = (s, o) => { const l = bgLayer(s, o, .4), w = (o.size || 3) * s.C.u; l.style.inset = '-30%'; l.style.background = `repeating-linear-gradient(${o.angle || -45}deg, ${o.a || 'var(--bg)'} 0 ${w}px, ${o.b || 'var(--bg2)'} ${w}px ${2 * w}px)`;
    if (o.scroll) s.every(null, lt => { l.style.backgroundPosition = `${lt * o.scroll * s.C.u}px 0`; }); return l; };
  BG.rays = (s, o) => { const l = bgLayer(s, o, .3); l.style.inset = '-60%'; l.style.background = `repeating-conic-gradient(from 0deg at 50% 50%, ${o.a || 'var(--accent)'} 0deg ${o.w || 6}deg, ${o.b || 'var(--accent2)'} ${o.w || 6}deg ${2 * (o.w || 6)}deg)`;
    s.every(null, lt => { l.style.transform = `rotate(${lt * (o.speed || 8)}deg)`; }); return l; };
  BG.speedlines = (s, o) => canvasBg(s, o, (g, W, H, lt) => { g.fillStyle = o.bg || getVar(s, '--bg'); g.fillRect(0, 0, W, H); g.strokeStyle = o.color || getVar(s, '--fg'); const cx = W * (o.x || .5), cy = H * (o.y || .5), n = o.n || 140;
    for (let i = 0; i < n; i++) { const a = hash(i * 1.3) * 6.283, f = Math.floor(lt * 20), on = hash(i + f * .37) > .35; if (!on) continue; const r0 = (.18 + hash(i * 3.1 + f) * .25) * Math.max(W, H), r1 = r0 + (.2 + hash(i * 5.7) * .6) * Math.max(W, H);
      g.lineWidth = 1 + hash(i * 2.2) * (o.width || 5); g.globalAlpha = .35 + .5 * hash(i * 8.8 + f); g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); g.stroke(); } g.globalAlpha = 1; });
  BG.stars = (s, o) => canvasBg(s, o, (g, W, H, lt) => { g.clearRect(0, 0, W, H); if (o.fill !== false) { g.fillStyle = o.bg || getVar(s, '--bg'); g.fillRect(0, 0, W, H); } const n = o.n || 500, warp = o.warp || 0;
    for (let i = 0; i < n; i++) { let z = (hash(i * 7.3) - lt * warp * .15) % 1; if (z <= 0) z += 1; const x = (hash(i) - .5) * W / z * .5 + W / 2, y = (hash(i + 9) - .5) * H / z * .5 + H / 2; const r = (1 - z) * 2.2 + .3;
      g.globalAlpha = (1 - z) * (.6 + .4 * Math.sin(lt * 3 + i)); g.fillStyle = o.color || '#fff'; if (warp) { g.strokeStyle = g.fillStyle; g.lineWidth = r; const dx = (x - W / 2) * warp * .05, dy = (y - H / 2) * warp * .05; g.beginPath(); g.moveTo(x, y); g.lineTo(x - dx, y - dy); g.stroke(); } else g.fillRect(x, y, r, r); } g.globalAlpha = 1; });
  BG.flow = (s, o) => canvasBg(s, o, (g, W, H, lt) => { g.fillStyle = o.bg || getVar(s, '--bg'); g.fillRect(0, 0, W, H); const n = o.n || 70, cols = [getVar(s, '--accent'), getVar(s, '--accent2'), getVar(s, '--accent3')];
    g.lineWidth = o.width || 2; for (let i = 0; i < n; i++) { g.strokeStyle = cols[i % 3]; g.globalAlpha = .15 + .35 * hash(i * 4.4); g.beginPath(); const y0 = (i / n) * H * 1.2 - H * .1;
      for (let x = -20; x <= W + 20; x += 24) { const y = y0 + Math.sin(x * .004 + lt * (o.speed || .6) + i * .3) * 40 + fbm(x * .003 + i + lt * .2) * 90; if (x < 0) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke(); } g.globalAlpha = 1; });
  BG.bokeh = (s, o) => canvasBg(s, o, (g, W, H, lt) => { g.clearRect(0, 0, W, H); const n = o.n || 40; for (let i = 0; i < n; i++) { const x = (hash(i) * W + lt * (10 + hash(i * 3) * 30)) % (W + 200) - 100, y = hash(i + 4) * H + Math.sin(lt * .5 + i) * 20, r = (4 + hash(i * 6) * 12) * s.C.u * .5;
    const gr = g.createRadialGradient(x, y, 0, x, y, r); const c = [getVar(s, '--accent'), getVar(s, '--accent2'), getVar(s, '--accent3')][i % 3]; gr.addColorStop(0, c); gr.addColorStop(1, 'transparent'); g.globalAlpha = .18 + .2 * hash(i * 9); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); } g.globalAlpha = 1; }, .5);
  BG.skyline = (s, o) => { const l = bgLayer(s, o, o.depth || .4), W = s.C.W * 1.3, H = s.C.H, n = o.n || 38, r = MS.rng(o.seed || 7); let x = -s.C.W * .15, pts = `M${x} ${H}`; const base = H * (o.base || .78);
    while (x < W) { const w = (2 + r() * 6) * s.C.u, h = (6 + r() * (o.height || 30)) * s.C.u; pts += `L${x} ${base - h}L${x + w} ${base - h}`; x += w; } pts += `L${x} ${H}Z`;
    l.innerHTML = `<svg width="${W}" height="${H}" style="position:absolute;left:0;top:0"><path d="${pts}" fill="${o.color || 'var(--bg2)'}"/></svg>`; return l; };
  BG.horizon = (s, o) => { const l = bgLayer(s, o, .3), C = s.C, hy = (o.sunY || .56) * 100; l.style.background = `linear-gradient(180deg, ${o.top || 'var(--bg)'} 0%, ${o.mid || 'var(--bg2)'} ${hy - .5}%, ${o.glowColor || 'var(--accent)'} ${hy}%, ${o.floor || 'var(--bg)'} ${hy + 6}%, ${o.floor || 'var(--bg)'} 100%)`;
    const sun = div('ms-abs', l), sz = 36 * (o.sun === false ? 0 : o.sun || 1); sun.style.cssText = `left:50%;top:${(o.sunY || .56) * 100}%;width:${sz * C.u}px;height:${sz * C.u}px;transform:translate(-50%,-100%);border-radius:50%;background:linear-gradient(${o.sunTop || 'var(--accent3)'}, ${o.sunBottom || 'var(--accent)'});
      -webkit-mask:repeating-linear-gradient(180deg,#000 0 ${2.2 * C.u}px, transparent ${2.2 * C.u}px ${2.8 * C.u}px)`;
    const fl = s.bg('grid', { floor: true, depth: .5, color: o.gridColor || 'var(--accent2)', size: 8, scroll: o.scroll != null ? o.scroll : 8 }); fl.style.top = hy + '%'; fl.style.opacity = o.gridOpacity || .55;
    fl.style.webkitMaskImage = 'linear-gradient(180deg, transparent 0%, #000 25%)'; return l; };
  BG.paper = (s, o) => { const l = bgLayer(s, o, .2); l.style.background = o.color || 'var(--bg)'; l.innerHTML = `<svg width="100%" height="100%" style="position:absolute;inset:0;opacity:${o.amount || .35};mix-blend-mode:multiply"><filter id="pp${s.id}"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="4"/><feColorMatrix values="0 0 0 0 .45  0 0 0 0 .4  0 0 0 0 .33  0 0 0 .5 0"/></filter><rect width="100%" height="100%" filter="url(#pp${s.id})"/></svg>`; return l; };
  BG.blueprint = (s, o) => { const l = bgLayer(s, o, .6), u = s.C.u; l.style.inset = '-20%'; l.style.background = `linear-gradient(var(--line) 1.5px, transparent 1.5px) 0 0/${10 * u}px ${10 * u}px, linear-gradient(90deg, var(--line) 1.5px, transparent 1.5px) 0 0/${10 * u}px ${10 * u}px, linear-gradient(var(--line) .5px, transparent .5px) 0 0/${2 * u}px ${2 * u}px, linear-gradient(90deg, var(--line) .5px, transparent .5px) 0 0/${2 * u}px ${2 * u}px, var(--bg)`; return l; };
  BG.aurora = (s, o) => canvasBg(s, o, (g, W, H, lt) => { g.fillStyle = getVar(s, '--bg'); g.fillRect(0, 0, W, H); const cols = [getVar(s, '--accent'), getVar(s, '--accent2'), getVar(s, '--accent3')];
    g.globalCompositeOperation = 'lighter'; for (let b = 0; b < 3; b++) { g.fillStyle = cols[b]; g.globalAlpha = .09; for (let x = 0; x < W; x += 6) { const y = H * (.35 + b * .08) + fbm(x * .002 + b * 4 + lt * .15) * H * .25, h = H * (.18 + .12 * fbm(x * .004 + lt * .2 + b)); g.fillRect(x, y - h, 6, h * 2); } }
    g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1; });
  function getVar(s, v) { return getComputedStyle(s.C.stage).getPropertyValue(v).trim(); }
  function canvasBg(s, o, draw, depth = .25) { const l = bgLayer(s, o, depth), cv = document.createElement('canvas'), sc = o.res || .5; cv.width = s.C.W * sc; cv.height = s.C.H * sc; cv.className = 'ms-canvas';
    cv.style.width = s.C.W + 'px'; cv.style.height = s.C.H + 'px'; l.appendChild(cv); const g = cv.getContext('2d'); g.scale(sc, sc); s.every(null, lt => draw(g, s.C.W, s.C.H, lt)); return l; }
  MS.canvasLayer = (s, draw, o = {}) => canvasBg(s, o, draw, o.depth != null ? o.depth : 1);

  // ------------------------------------------------------------------ particles (analytic → seekable)
  function makeParticles(s, o) {
    const C = s.C, l = o.layer || s.layer(o.depth != null ? o.depth : 1.1, 'particles'), cv = document.createElement('canvas'), sc = o.res || .5;
    cv.width = C.W * sc; cv.height = C.H * sc; cv.className = 'ms-canvas'; cv.style.width = C.W + 'px'; cv.style.height = C.H + 'px'; l.appendChild(cv);
    const g = cv.getContext('2d'); g.scale(sc, sc);
    const type = o.type || 'dust', n = o.count || { burst: 160, sparks: 120, dust: 120, snow: 200, rain: 260, confetti: 140, embers: 90, bubbles: 40, flow: 300 }[type] || 120;
    const cols = (o.colors || [o.color || 'var(--accent)', 'var(--accent2)', 'var(--fg)']).map(c => c.startsWith('var(') ? getComputedStyle(C.stage).getPropertyValue(c.slice(4, -1)).trim() : c);
    const at = o.at || 0, ox = (o.x != null ? o.x : .5) * C.W, oy = (o.y != null ? o.y : .5) * C.H, seed = hashStr(s.id + type + at), U2 = C.u, sz = o.size || 1;
    if (o.cue !== false && (type === 'burst' || type === 'sparks' || type === 'confetti')) C.cue(s.start + at, type === 'confetti' ? 'pop' : 'impact', { auto: true, gain: .5 });
    s.every(null, lt => { g.clearRect(0, 0, C.W, C.H); const k = lt - at; if (k < 0 && ['burst', 'sparks', 'confetti'].includes(type)) return;
      for (let i = 0; i < n; i++) { const h1 = hash(seed + i * 1.13), h2 = hash(seed + i * 2.71), h3 = hash(seed + i * 3.37), h4 = hash(seed + i * 5.19); let x, y, a = 1, r = (1 + h3 * 2.5) * sz * U2 * .35;
        g.fillStyle = cols[i % cols.length];
        if (type === 'burst' || type === 'sparks' || type === 'confetti') { const life = (o.life || 1.4) * (.5 + h4); if (k > life) continue; const ang = h1 * 6.283, sp = (o.speed || 60) * U2 * (.3 + h2) * (type === 'sparks' ? 1.6 : 1), drag = 1 - Math.exp(-k * 2.2);
          x = ox + Math.cos(ang) * sp * drag / 2.2; y = oy + Math.sin(ang) * sp * drag / 2.2 + (o.gravity != null ? o.gravity : type === 'confetti' ? 30 : 8) * U2 * k * k; a = 1 - k / life;
          if (type === 'sparks') { g.strokeStyle = g.fillStyle; g.globalAlpha = a; g.lineWidth = r * .6; g.beginPath(); g.moveTo(x, y); g.lineTo(x - Math.cos(ang) * r * 6 * (1 - drag + .2), y - Math.sin(ang) * r * 6 * (1 - drag + .2)); g.stroke(); continue; }
          if (type === 'confetti') { g.save(); g.translate(x, y); g.rotate(k * (4 + h3 * 8) + i); g.globalAlpha = a; g.fillRect(-r, -r * .5, r * 2, r); g.restore(); continue; } }
        else if (type === 'snow' || type === 'dust' || type === 'embers' || type === 'bubbles') { const sp = (o.speed || (type === 'snow' ? 6 : type === 'embers' ? -7 : type === 'bubbles' ? -5 : 1.2)) * U2 * (.4 + h2);
          x = (h1 * C.W + Math.sin(lt * (.4 + h3) + i) * 3 * U2 + lt * (o.wind || 0) * U2) % C.W; y = ((h2 * C.H + lt * sp) % C.H + C.H) % C.H; a = (type === 'dust' ? .25 : .7) * (.4 + .6 * h4) * (type === 'embers' ? (.5 + .5 * Math.sin(lt * 5 + i)) : 1);
          if (type === 'bubbles') { g.strokeStyle = g.fillStyle; g.lineWidth = 1.5; g.globalAlpha = a; g.beginPath(); g.arc(x, y, r * 3, 0, 7); g.stroke(); continue; } }
        else if (type === 'rain') { const sp = 120 * U2 * (.6 + h2); x = (h1 * C.W * 1.2 - lt * 10 * U2) % (C.W * 1.2); if (x < 0) x += C.W * 1.2; y = (h2 * C.H + lt * sp) % C.H; g.strokeStyle = g.fillStyle; g.globalAlpha = .35 * h4 + .15; g.lineWidth = 1.2; g.beginPath(); g.moveTo(x, y); g.lineTo(x - U2 * .6, y + U2 * 3.5); g.stroke(); continue; }
        else if (type === 'flow') { const base = h1 * 40, px = (h2 * C.W + lt * 12 * U2 * (.5 + h3)) % C.W; x = px; y = h4 * C.H + fbm(px * .004 + base) * 16 * U2 + Math.sin(lt + base) * 2 * U2; a = .5; }
        else continue;
        g.globalAlpha = Math.max(0, Math.min(1, a)) * (o.opacity || 1); g.beginPath(); g.arc(x, y, r, 0, 6.283); g.fill(); }
      g.globalAlpha = 1; });
    return l;
  }

  // ------------------------------------------------------------------ overlays (style textures)
  const OV = MS.overlays;
  function ovDiv(C, css) { const d = div('ms-overlay', C.overlayRoot); d.style.cssText += css; return d; }
  OV.grain = (C, o) => {                      // 6 pre-baked noise tiles, cycled + offset per frame (deterministic and cheap)
    const T = 256, tiles = []; for (let k = 0; k < 6; k++) { const cv = document.createElement('canvas'); cv.width = cv.height = T; const g = cv.getContext('2d'), img = g.createImageData(T, T), rr = MS.rng(k * 7919 + 1);
      for (let i = 0; i < img.data.length; i += 4) { const v = rr() * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; } g.putImageData(img, 0, 0); tiles.push(cv.toDataURL()); }
    const d = ovDiv(C, `mix-blend-mode:overlay;opacity:${o.amount || .12};background-size:${T * (o.scale || 1.5)}px;image-rendering:pixelated`);
    return { type: 'grain', update(t) { const f = Math.round(t * C.fps / (o.hold || 2)); d.style.backgroundImage = `url(${tiles[f % 6]})`; d.style.backgroundPosition = `${Math.floor(hash(f) * T)}px ${Math.floor(hash(f + .5) * T)}px`; } }; };
  OV.scanlines = (C, o) => { const px = (o.size || .3) * C.u; ovDiv(C, `background:repeating-linear-gradient(0deg, rgba(0,0,0,${o.amount || .25}) 0 ${px}px, transparent ${px}px ${px * 2.2}px)`); return { type: 'scanlines', update() { } }; };
  OV.vignette = (C, o) => { ovDiv(C, `background:radial-gradient(ellipse at center, transparent ${o.inner || 55}%, rgba(0,0,0,${o.amount || .55}) 100%)`); return { type: 'vignette', update() { } }; };
  OV.letterbox = (C, o) => { const ratio = o.ratio || 2.39, h = Math.max(0, (C.H - C.W / ratio) / 2); const a = ovDiv(C, `top:0;bottom:auto;height:${h}px;background:#000`), b = ovDiv(C, `top:auto;bottom:0;height:${h}px;background:#000`);
    return { type: 'letterbox', update(t) { const k = o.animate ? NAMED.inOutSine(seg(t, o.from || 0, (o.from || 0) + .8)) : 1; a.style.height = b.style.height = h * k + 'px'; } }; };
  OV.chromatic = (C, o) => ({ type: 'chromatic', update(t) { setRGB(C, (o.amount || 1.5) * (1 + .5 * Math.sin(t * 7)), 0); C.stage.style.filter = (C.stage.style.filter + ' url(#ms-rgb)').trim(); } });
  OV.vhs = (C, o) => { const band = ovDiv(C, 'height:8%;top:0;background:linear-gradient(transparent, rgba(255,255,255,.07), transparent);mix-blend-mode:screen');
    const label = ovDiv(C, `inset:auto;left:${C.safe.x}px;top:${C.safe.y}px;font:${4.2 * C.u}px/1 'VT323',monospace;color:#f2f2f2;text-shadow:2px 0 #ff0050,-2px 0 #00e0ff;white-space:pre`);
    const ts = ovDiv(C, `inset:auto;right:${C.W - C.safe.x - C.safe.w}px;bottom:${C.H - C.safe.y - C.safe.h}px;font:${4.2 * C.u}px/1 'VT323',monospace;color:#f2f2f2;text-shadow:2px 0 #ff0050,-2px 0 #00e0ff;text-align:right;white-space:pre`);
    const g = OV.grain(C, { amount: o.amount || .16 }); ovDiv(C, 'background:repeating-linear-gradient(0deg, rgba(0,0,0,.22) 0 2px, transparent 2px 4px)');
    return { type: 'vhs', update(t) { g.update(t); const f = Math.floor(t * C.fps); band.style.top = ((t * 23) % 120 - 10) + '%';
      setRGB(C, (o.chroma || 2.5) + Math.sin(t * 13) * .8, 0); C.stage.style.filter = (C.stage.style.filter + ' url(#ms-rgb) saturate(1.25) contrast(1.05)').trim();
      C.stage.style.transform = (C.devScale || '') + ` translateX(${(hash(f * .7) > .93 ? (hash(f) - .5) * 1.2 * C.u : 0).toFixed(1)}px)`;
      if (o.label !== false) label.textContent = (o.labelText || 'PLAY ▶') + (Math.floor(t * 2) % 2 ? '' : ''); const s = Math.floor(t + (o.start || 0)); ts.textContent = o.stamp !== false ? `${o.date || 'JUN 14 1994'}\n${o.clock || ''}${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` : ''; } }; };
  OV.crt = (C, o) => { ovDiv(C, `background:repeating-linear-gradient(0deg, rgba(0,0,0,.28) 0 ${.25 * C.u}px, transparent ${.25 * C.u}px ${.5 * C.u}px)`); ovDiv(C, 'background:radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,.75) 100%);border-radius:3%/5%;box-shadow:inset 0 0 8vmin rgba(0,0,0,.8)');
    return { type: 'crt', update(t) { C.stage.style.filter = (C.stage.style.filter + ` brightness(${1 + .03 * Math.sin(t * 60)}) contrast(1.1)`).trim(); } }; };
  OV.halftone = (C, o) => { ovDiv(C, `background-image:radial-gradient(rgba(0,0,0,${o.amount || .15}) 30%, transparent 32%);background-size:${(o.size || 1) * C.u}px ${(o.size || 1) * C.u}px;mix-blend-mode:multiply`); return { type: 'halftone', update() { } }; };
  OV.paper = (C, o) => { const d = ovDiv(C, 'mix-blend-mode:multiply'); d.innerHTML = `<svg width="100%" height="100%"><filter id="ov-paper"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .45  0 0 0 0 .38  0 0 0 ${o.amount || .35} 0"/></filter><rect width="100%" height="100%" filter="url(#ov-paper)"/></svg>`; return { type: 'paper', update() { } }; };
  OV.hud = (C, o) => { const u = C.u, d = ovDiv(C, ''); const c = o.color || 'var(--accent)', L = 5 * u, w = .35 * u, sf = C.safe;
    d.innerHTML = [[sf.x, sf.y, '1 0 0 1'], [sf.x + sf.w, sf.y, '-1 0 0 1'], [sf.x, sf.y + sf.h, '1 0 0 -1'], [sf.x + sf.w, sf.y + sf.h, '-1 0 0 -1']].map(([x, y, m]) => `<div style="position:absolute;left:${x}px;top:${y}px;width:${L}px;height:${L}px;border-left:${w}px solid ${c};border-top:${w}px solid ${c};transform:matrix(${m.split(' ').join(',')},0,0);transform-origin:0 0;opacity:.8"></div>`).join('');
    const tick = ovDiv(C, `inset:auto;left:${sf.x + L * 1.4}px;top:${sf.y - 0.4 * u}px;font:${2.2 * u}px/1 var(--font-mono);color:${c};letter-spacing:.2em;opacity:.8`);
    return { type: 'hud', update(t) { tick.textContent = `REC ● ${t.toFixed(2).padStart(6, '0')}  //  SYS ${String(Math.floor(hash(Math.floor(t * 8)) * 9999)).padStart(4, '0')}`; } }; };
  OV.lightleak = (C, o) => { const d = ovDiv(C, 'mix-blend-mode:screen'); return { type: 'lightleak', update(t) { d.style.background = `radial-gradient(ellipse at ${50 + 40 * Math.sin(t * .3)}% ${30 + 20 * Math.cos(t * .23)}%, rgba(255,150,60,${(o.amount || .25) * (.6 + .4 * Math.sin(t * .7))}) 0%, transparent 55%)`; } }; };
  OV.film = (C, o) => { const g = OV.grain(C, { amount: o.amount || .1 }), d = ovDiv(C, ''); return { type: 'film', update(t) { g.update(t); const f = Math.floor(t * 12); let h = '';
    for (let i = 0; i < 3; i++) if (hash(f * 3 + i) > .6) h += `<div style="position:absolute;left:${hash(f + i * 7) * 100}%;top:0;width:1px;height:100%;background:rgba(255,255,255,.15)"></div>`;
    for (let i = 0; i < 6; i++) if (hash(f * 5 + i) > .7) h += `<div style="position:absolute;left:${hash(f + i * 3) * 100}%;top:${hash(f * 2 + i) * 100}%;width:${2 + hash(i + f) * 4}px;height:${2 + hash(i * 2 + f) * 3}px;border-radius:50%;background:rgba(0,0,0,.5)"></div>`; d.innerHTML = h; } }; };
  OV.pixelate = (C, o) => ({ type: 'pixelate', update() { } });            // pixel look comes from style tokens (font, stepped motion, crispEdges art)

  // ------------------------------------------------------------------ morph, text on path, charts, UI, logo
  MS.morph = function (dA, dB, n = 160) {                                          // resample two paths to n points and interpolate
    const sample = d => { const p = svgEl('path', { d }, MS._tmpSvg || (MS._tmpSvg = svgEl('svg', { width: 0, height: 0, style: 'position:absolute' }, document.body))); const L = p.getTotalLength(), pts = [];
      for (let i = 0; i < n; i++) { const q = p.getPointAtLength(L * i / n); pts.push([q.x, q.y]); } p.remove(); return pts; };
    const A = sample(dA), B = sample(dB); let best = 0, bd = 1e18;                    // rotate B to best match A (less twisting)
    for (let k = 0; k < n; k += 2) { let d = 0; for (let i = 0; i < n; i += 8) { const b = B[(i + k) % n]; d += (A[i][0] - b[0]) ** 2 + (A[i][1] - b[1]) ** 2; } if (d < bd) { bd = d; best = k; } }
    const B2 = A.map((_, i) => B[(i + best) % n]);
    return p => 'M' + A.map((a, i) => (lerp(a[0], B2[i][0], p)).toFixed(2) + ' ' + (lerp(a[1], B2[i][1], p)).toFixed(2)).join('L') + 'Z';
  };
  Scene.prototype.morphPath = function (pathEl, shapes, times, o = {}) { const fns = []; for (let i = 0; i < shapes.length - 1; i++) fns.push(MS.morph(shapes[i], shapes[i + 1], o.points || 160));
    this.every(null, lt => { let d = shapes[0]; for (let i = 0; i < fns.length; i++) { if (lt >= times[i]) d = fns[i](MS.ease(o.ease || this.M.ease.move)(seg(lt, times[i], times[i] + (o.dur || .8)))); } pathEl.setAttribute('d', d); }); return this; };
  Scene.prototype.textPath = function (str, d, o = {}) { const id = 'tp' + hashStr(this.id + str); const u = this.C.u;
    const n = this.svg(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="${o.viewBox || `0 0 ${this.C.W} ${this.C.H}`}" style="width:${this.C.W}px;height:${this.C.H}px"><path id="${id}" d="${d}" fill="none" stroke="${o.showPath ? 'var(--line)' : 'none'}"/><text font-family="var(--font-display)" font-weight="var(--w-display)" font-size="${(o.size || 6) * u}" fill="${o.color || 'var(--fg)'}"><textPath href="#${id}" startOffset="0%">${str}</textPath></text></svg>`, { space: 'frame', x: 0, y: 0, anchor: 'top-left' });
    const tp = n.querySelector('textPath'); this.tween(null, o.at || 0, o.dur || 4, o.ease || 'linear', e => { tp.setAttribute('startOffset', lerp(o.from != null ? o.from : 100, o.to != null ? o.to : 0, e) + '%'); }); this.C.texts.push(n.querySelector('text')); return n; };

  const CH = MS.chart;
  CH.bar = function (s, data, o = {}) {
    const C = s.C, u = C.u, g = s.group({ x: o.x != null ? o.x : .5, y: o.y != null ? o.y : .55, w: o.w || .8, h: o.h || .6, anchor: 'center' }), W = parseFloat(g.style.width), H = parseFloat(g.style.height);
    const max = o.max || Math.max(...data.map(d => d.value)) * 1.1, n = data.length, gap = (o.gap || .28), bw = W / n * (1 - gap), at = o.at || 0;
    data.forEach((d, i) => { const h = d.value / max * (H - 9 * u), x = i * W / n + (W / n - bw) / 2;
      const bar = div('ms-abs', g); bar.style.cssText = `left:${x}px;bottom:${6 * u}px;width:${bw}px;height:${h}px;background:${d.color || o.color || (i === o.highlight ? 'var(--accent)' : 'var(--accent2)')};border-radius:${o.radius != null ? o.radius : .6 * u}px ${o.radius != null ? o.radius : .6 * u}px 0 0;transform-origin:50% 100%`;
      const lab = div('ms-abs', g); lab.textContent = d.label; lab.style.cssText = `left:${x - bw * .3}px;width:${bw * 1.6}px;bottom:${1 * u}px;text-align:center;font:600 ${2.4 * u}px var(--font-body);color:var(--muted)`;
      const val = div('ms-abs', g); val.style.cssText = `left:${x - bw * .5}px;width:${bw * 2}px;bottom:${6.6 * u + h}px;text-align:center;font:var(--w-display) ${3.3 * u}px var(--font-display);color:var(--fg)`; val.textContent = '0';
      const t0 = at + i * (o.stagger != null ? o.stagger : s.M.stagger.items); s.track(bar); s.track(lab); s.track(val); C.texts.push(lab, val);
      s.tween(bar, t0, o.dur || .9, o.ease || s.M.ease.emphasis, (e, st) => { st.sy *= Math.max(0, e); });
      s.tween(lab, t0, .4, 'out', (e, st) => { st.o *= e; }); s.tween(val, t0, o.dur || .9, o.ease || s.M.ease.emphasis, (e, st) => { st.o *= Math.min(1, e * 3); st.y += (1 - e) * h; });
      P.countUp(s, val, t0, { to: d.value, dur: o.dur || .9, decimals: o.decimals, prefix: o.prefix, suffix: o.suffix, ease: s.M.ease.enter }); });
    const axis = div('ms-abs', g); axis.style.cssText = `left:0;right:0;bottom:${6 * u}px;height:2px;background:var(--line)`; return g; };
  CH.line = function (s, values, o = {}) {
    const C = s.C, u = C.u, g = s.group({ x: o.x != null ? o.x : .5, y: o.y != null ? o.y : .55, w: o.w || .8, h: o.h || .55 }), W = parseFloat(g.style.width), H = parseFloat(g.style.height);
    const series = Array.isArray(values[0]) ? values : [values], max = o.max || Math.max(...series.flat()) * 1.1, min = o.min || 0, at = o.at || 0;
    const svg = svgEl('svg', { width: W, height: H, style: 'position:absolute;left:0;top:0;overflow:visible' }, g);
    for (let k = 0; k <= 4; k++) svgEl('line', { x1: 0, x2: W, y1: H * k / 4, y2: H * k / 4, stroke: 'var(--line)', 'stroke-width': 1 }, svg);
    series.forEach((vals, si) => { const pts = vals.map((v, i) => [i / (vals.length - 1) * W, H - (v - min) / (max - min) * H]); const d = 'M' + pts.map(p => p.map(x => x.toFixed(1)).join(' ')).join('L'), col = (o.colors || ['var(--accent)', 'var(--accent2)', 'var(--accent3)'])[si % 3];
      if (o.area !== false && si === 0) { const ar = svgEl('path', { d: d + `L${W} ${H}L0 ${H}Z`, fill: col, opacity: .14 }, svg); s.tween(null, at + .6, .8, 'out', e => ar.setAttribute('opacity', (.14 * e).toFixed(3))); }
      const p = svgEl('path', { d, fill: 'none', stroke: col, 'stroke-width': (o.width || .7) * u, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg), L = p.getTotalLength(); p.style.strokeDasharray = L;
      s.tween(null, at + si * .2, o.dur || 1.6, o.ease || s.M.ease.move, e => { p.style.strokeDashoffset = (L * (1 - e)).toFixed(1); });
      if (o.dots !== false) pts.forEach((q, i) => { const c = svgEl('circle', { cx: q[0], cy: q[1], r: .9 * u, fill: col }, svg); const t0 = at + si * .2 + (o.dur || 1.6) * (i / (pts.length - 1)); s.tween(null, t0, .3, 'outBack', e => c.setAttribute('r', (.9 * u * e).toFixed(2))); }); });
    if (o.labels) o.labels.forEach((lb, i) => { const t = div('ms-abs', g); t.textContent = lb; t.style.cssText = `left:${i / (o.labels.length - 1) * W}px;top:${H + 1.5 * u}px;transform:translateX(-50%);font:500 ${2.3 * u}px var(--font-body);color:var(--muted)`; C.texts.push(t); });
    s.track(g); return g; };
  CH.donut = function (s, value, o = {}) { const C = s.C, u = C.u, r = (o.r || 16) * u, sw = (o.width || 3) * u, sz = 2 * r + sw * 2;
    const g = s.el(`<div style="width:${sz}px;height:${sz}px"></div>`, { x: o.x, y: o.y }), svg = svgEl('svg', { width: sz, height: sz, style: 'position:absolute;inset:0;transform:rotate(-90deg)' }, g);
    svgEl('circle', { cx: sz / 2, cy: sz / 2, r, fill: 'none', stroke: 'var(--line)', 'stroke-width': sw }, svg); const arc = svgEl('circle', { cx: sz / 2, cy: sz / 2, r, fill: 'none', stroke: o.color || 'var(--accent)', 'stroke-width': sw, 'stroke-linecap': 'round' }, svg);
    const L = 2 * Math.PI * r; arc.style.strokeDasharray = L; const lab = div('ms-abs', g); lab.style.cssText = `inset:0;display:flex;align-items:center;justify-content:center;font:var(--w-display) ${r * .5}px var(--font-display)`; C.texts.push(lab);
    s.tween(null, o.at || 0, o.dur || 1.4, o.ease || s.M.ease.move, e => { arc.style.strokeDashoffset = L * (1 - value / 100 * e); lab.textContent = Math.round(value * e) + (o.suffix != null ? o.suffix : '%'); }); return g; };
  CH.counter = function (s, o = {}) { const n = s.text(String(o.from || 0), Object.assign({ size: 'display', font: 'display' }, o)); P.countUp(s, n, o.at || 0, o); return n; };
  CH.timeline = function (s, events, o = {}) { const C = s.C, u = C.u, g = s.group({ x: .5, y: o.y != null ? o.y : .55, w: o.w || .9, h: 30 * u }), W = parseFloat(g.style.width), at = o.at || 0, step = o.step || .5;
    const line = div('ms-abs', g); line.style.cssText = `left:0;top:${15 * u}px;height:${.4 * u}px;width:${W}px;background:var(--accent);transform-origin:0 50%`; s.track(line);
    s.tween(line, at, step * events.length + .3, 'inOut', (e, st) => { st.sx *= e; });
    events.forEach((ev, i) => { const x = (i + .5) / events.length * W, t0 = at + (i + .5) * step, dot = div('ms-abs', g), yr = div('ms-abs', g), lb = div('ms-abs', g);
      dot.style.cssText = `left:${x - 1.2 * u}px;top:${15.2 * u - 1.2 * u}px;width:${2.4 * u}px;height:${2.4 * u}px;border-radius:50%;background:var(--bg);border:${.45 * u}px solid var(--accent)`;
      yr.textContent = ev.label || ev.year; yr.style.cssText = `left:${x}px;top:${(i % 2 ? 19 : 5) * u}px;transform:translateX(-50%);font:var(--w-display) ${4.4 * u}px var(--font-display);white-space:nowrap`;
      lb.textContent = ev.text || ''; lb.style.cssText = `left:${x}px;top:${(i % 2 ? 24.5 : 10.5) * u}px;transform:translateX(-50%);font:500 ${2.4 * u}px var(--font-body);color:var(--muted);white-space:nowrap`;
      [dot, yr, lb].forEach(e => s.track(e)); C.texts.push(yr, lb); P.pop(s, dot, t0, {}); P.fadeUp(s, yr, t0 + .05, { dist: 2 }); P.fadeUp(s, lb, t0 + .15, { dist: 2 }); if (o.cue !== false) C.cue(s.start + t0, 'tick', { auto: true, gain: .6 }); });
    return g; };
  CH.map = function (s, points, o = {}) {                     // stylised (non-geographic) map: procedural landmass dots + pins + route
    const C = s.C, u = C.u, W = C.W, H = C.H, svg = s.svg(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"></svg>`, { space: 'frame', x: 0, y: 0, anchor: 'top-left', layer: o.layer }), step = (o.dot || 1.6) * u, at = o.at || 0;
    let dots = ''; for (let y = step; y < H; y += step) for (let x = step; x < W; x += step) { const v = fbm(x * .0022 + (o.seed || 3)) + fbm(y * .003 + 7.7 + x * .0008); if (v > (o.land || .1)) dots += `<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${(step * .22).toFixed(1)}"/>`; }
    svg.insertAdjacentHTML('beforeend', `<g fill="var(--muted)" opacity=".45">${dots}</g>`);
    const P2 = points.map(p => [p.x * W, p.y * H]);
    let d = `M${P2[0][0]} ${P2[0][1]}`; for (let i = 1; i < P2.length; i++) { const [x0, y0] = P2[i - 1], [x1, y1] = P2[i]; d += ` Q${(x0 + x1) / 2} ${Math.min(y0, y1) - Math.abs(x1 - x0) * .25} ${x1} ${y1}`; }
    const route = svgEl('path', { d, fill: 'none', stroke: 'var(--accent)', 'stroke-width': .5 * u }, svg);
    const L = route.getTotalLength(); route.style.strokeDasharray = L; s.tween(null, at + .4, o.dur || (points.length * .8), o.ease || 'inOut', e => { route.style.strokeDashoffset = L * (1 - e); });
    points.forEach((p, i) => { const t0 = at + .4 + (o.dur || points.length * .8) * (i / Math.max(1, points.length - 1)); const pin = s.el(`<div style="width:${2.4 * u}px;height:${2.4 * u}px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 ${.8 * u}px color-mix(in srgb, var(--accent) 35%, transparent)"></div>`, { space: 'frame', x: p.x, y: p.y, layer: o.layer });
      P.pop(s, pin, t0, {}); if (p.label) { const lb = s.text(p.label, { size: 'caption', font: 'body', weight: 700, space: 'frame', x: p.x, y: p.y - .045, anchor: 'bottom', layer: o.layer }); lb.dataset.free = 1; P.fadeUp(s, lb, t0 + .1, { dist: 1.5 }); } });
    return svg; };

  const UI = MS.ui;
  UI.window = function (s, o = {}) { const C = s.C, u = C.u * (o.scale || C.uiScale), w = s.el(`<div class="ms-card" style="overflow:hidden"></div>`, { x: o.x, y: o.y, w: o.w || .6, h: o.h || .6 });
    w.innerHTML = `<div style="height:${4.2 * u}px;display:flex;align-items:center;gap:${.9 * u}px;padding:0 ${1.6 * u}px;border-bottom:1px solid var(--line)"><i style="width:${1.2 * u}px;height:${1.2 * u}px;border-radius:50%;background:#ff5f57"></i><i style="width:${1.2 * u}px;height:${1.2 * u}px;border-radius:50%;background:#febc2e"></i><i style="width:${1.2 * u}px;height:${1.2 * u}px;border-radius:50%;background:#28c840"></i><span style="margin-left:${1.4 * u}px;font:500 ${2.2 * u}px var(--font-body);color:var(--muted)">${o.title || ''}</span></div><div class="body" style="position:relative;padding:${2.2 * u}px;height:calc(100% - ${4.2 * u}px)"></div>`;
    return { el: w, body: w.querySelector('.body') }; };
  UI.card = function (s, o = {}) { const u = s.C.u * (o.scale || s.C.uiScale), c = s.el(`<div class="ms-card" style="padding:${2.4 * u}px ${2.8 * u}px;display:flex;gap:${2 * u}px;align-items:center"></div>`, { x: o.x, y: o.y, w: o.w || .34, anchor: o.anchor });
    c.innerHTML = `${o.icon ? `<div style="flex:none;width:${6 * u}px;height:${6 * u}px;border-radius:${1.6 * u}px;background:${o.iconBg || 'var(--accent)'};display:flex;align-items:center;justify-content:center;font-size:${3.2 * u}px;color:var(--bg)">${o.icon}</div>` : ''}<div><div style="font:700 ${3 * u}px var(--font-body)">${o.title || ''}</div>${o.text ? `<div style="font:400 ${2.4 * u}px var(--font-body);color:var(--muted);margin-top:${.5 * u}px">${o.text}</div>` : ''}</div>`;
    s.C.texts.push(c); if (o.at != null) s.anim(c, o.enter || 'spring', o.at, { from: o.from || 'bottom' }); return c; };
  UI.toast = (s, o = {}) => { const c = UI.card(s, Object.assign({ x: .5, y: s.C.vertical ? .08 : .1, w: s.C.vertical ? .92 : .4 }, o)); if (o.cue !== false) s.C.cue(s.start + (o.at || 0), 'notify', { auto: true }); if (o.until) s.anim(c, 'slideOut', o.until, { to: 'top', dist: 12 }); return c; };
  UI.button = (s, o = {}) => { const u = s.C.u * (o.scale || s.C.uiScale); const b = s.el(`<div style="padding:${1.8 * u}px ${4 * u}px;border-radius:999px;background:${o.color || 'var(--accent)'};color:${o.textColor || 'var(--bg)'};font:700 ${3 * u}px var(--font-body);white-space:nowrap">${o.label || 'Get started'}</div>`, { x: o.x, y: o.y }); s.C.texts.push(b); return b; };
  UI.cursor = (s, path, o = {}) => { const u = s.C.u * (o.scale || s.C.uiScale), c = s.el(`<svg width="${3.4 * u}" height="${3.4 * u}" viewBox="0 0 24 24"><path d="M3 2l7 19 2.6-7.4L20 11z" fill="${o.fill || '#fff'}" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/></svg>`, { x: path[0].x, y: path[0].y, anchor: 'top-left', z: 40, space: o.space });
    const sp = o.space === 'frame' ? { x: 0, y: 0, w: s.C.W, h: s.C.H } : s.C.safe;
    s.every(c, (lt, st) => { let x = path[0].x, y = path[0].y; for (let i = 1; i < path.length; i++) { const a = path[i - 1], b = path[i]; if (lt >= b.t) { x = b.x; y = b.y; } else if (lt > a.t) { const e = MS.ease(o.ease || 'inOut')((lt - a.t) / (b.t - a.t)); x = lerp(a.x, b.x, e); y = lerp(a.y, b.y, e); break; } else break; }
      st.x += (x - path[0].x) * sp.w; st.y += (y - path[0].y) * sp.h; const click = path.find(p => p.click && lt >= p.t && lt < p.t + .18); if (click) st.s *= .85; });
    path.filter(p => p.click).forEach(p => { const r = s.el(`<div style="width:${6 * u}px;height:${6 * u}px;border-radius:50%;border:${.5 * u}px solid var(--accent)"></div>`, { x: p.x, y: p.y, z: 39, space: o.space });
      s.tween(r, p.t, .5, 'out', (e, st, q) => { st.s *= .2 + e; st.o *= q >= 1 || q <= 0 ? 0 : 1 - e; }); s.C.cue(s.start + p.t, 'click', { auto: true }); }); return c; };
  UI.code = (s, lines, o = {}) => { const u = s.C.u * (o.scale || s.C.uiScale), box = s.el(`<div class="ms-card" style="padding:${2.4 * u}px;font:400 ${(o.size || 2.6) * u}px/1.55 var(--font-mono);white-space:pre;overflow:hidden"></div>`, { x: o.x, y: o.y, w: o.w || .6, h: o.h });
    const KW = /\b(const|let|function|return|await|async|import|from|export|if|for|class|new|def|print)\b/g; let t = o.at || 0; const cps = o.cps || 40;
    lines.forEach(line => { const row = document.createElement('div'); box.appendChild(row); const html = line.replace(/&/g, '&amp;').replace(/</g, '&lt;');
      const chars = [...line]; chars.forEach((ch, i) => { const sp = document.createElement('span'); sp.textContent = ch; row.appendChild(sp); s.track(sp); s.tween(sp, t + i / cps, .001, 'linear', (e, st) => { st.o *= e; }); });
      [...row.children].forEach(sp => { if (/[A-Za-z]/.test(sp.textContent)) sp.style.color = 'var(--fg)'; }); colorize(row, KW); t += chars.length / cps + (o.linePause || .12); });
    if (o.cue !== false) for (let k = o.at || 0; k < t; k += .09) s.C.cue(s.start + k, 'type', { auto: true, gain: .35 }); s.C.texts.push(box); box.__end = t; return box; };
  function colorize(row, KW) { const text = [...row.children].map(c => c.textContent).join(''); let m; KW.lastIndex = 0; while ((m = KW.exec(text))) for (let i = m.index; i < m.index + m[0].length; i++) row.children[i].style.color = 'var(--accent)';
    const strRe = /(["'`]).*?\1/g; while ((m = strRe.exec(text))) for (let i = m.index; i < m.index + m[0].length; i++) row.children[i].style.color = 'var(--accent3)';
    const cm = text.search(/\/\/|#/); if (cm >= 0) for (let i = cm; i < text.length; i++) row.children[i].style.color = 'var(--muted)'; }
  UI.chat = (s, msgs, o = {}) => { const u = s.C.u * (o.scale || s.C.uiScale), out = []; let y = o.y != null ? o.y : .2; msgs.forEach((m, i) => { const me = m.who === 'me';
      const b = s.el(`<div style="width:max-content;max-width:${(o.w || .6) * s.C.safe.w}px;padding:${1.6 * u}px ${2.4 * u}px;border-radius:${2.4 * u}px;font:500 ${(o.size || 2.8) * u}px/1.35 var(--font-body);background:${me ? 'var(--accent)' : 'var(--surface)'};color:${me ? 'var(--bg)' : 'var(--fg)'};white-space:normal;border:1px solid var(--line)">${m.text}</div>`, { x: me ? .98 : .02, y, anchor: me ? 'top-right' : 'top-left' });
      s.C.texts.push(b); s.anim(b, 'spring', m.at, { from: 'bottom', dist: 4 }); s.C.cue(s.start + m.at, 'pop', { auto: true, gain: .6 });
      y += m.gap != null ? m.gap : (b.offsetHeight + 2.2 * u) / s.C.safe.h; out.push(b); }); return out; };
  UI.progress = (s, o = {}) => { const u = s.C.u * (o.scale || s.C.uiScale), w = s.el(`<div style="height:${1.6 * u}px;border-radius:999px;background:var(--line);overflow:hidden"><div style="height:100%;width:100%;background:var(--accent);border-radius:999px;transform-origin:0 50%"></div></div>`, { x: o.x, y: o.y, w: o.w || .5 });
    const bar = w.firstChild; s.track(bar); s.tween(bar, o.at || 0, o.dur || 1.5, o.ease || 'inOut', (e, st) => { st.sx *= e; }); return w; };

  MS.logo.reveal = function (s, markup, o = {}) {
    const n = s.svg(markup, { x: o.x, y: o.y, size: o.size || .45 }), at = o.at || 0, draw = o.draw || 1.4, u = s.C.u;
    const shapes = [...n.querySelectorAll('path,circle,rect,polygon,ellipse,line,polyline')];
    shapes.forEach((el, i) => { const fill = el.getAttribute('fill'); el.dataset.fill = fill && fill !== 'none' ? fill : ''; if (!el.getAttribute('stroke') || el.getAttribute('stroke') === 'none') { el.setAttribute('stroke', o.stroke || 'var(--accent)'); el.setAttribute('stroke-width', o.strokeWidth || 1.5); el.dataset.addedStroke = '1'; }
      let L = 1000; try { L = el.getTotalLength(); } catch (e) { } el.style.strokeDasharray = L; const t0 = at + i * (o.stagger != null ? o.stagger : .08);
      s.tween(null, t0, draw, o.ease || s.M.ease.move, e => { el.style.strokeDashoffset = (L * (1 - e)).toFixed(2); });
      if (el.dataset.fill) s.tween(null, t0 + draw * .7, o.fillDur || .6, 'out', e => { el.style.fillOpacity = e; if (el.dataset.addedStroke) el.style.strokeOpacity = 1 - e; }); else el.style.fillOpacity = 0;
      el.style.fillOpacity = 0; });
    if (o.shine !== false) { const id = 'sh' + hashStr(s.id + at), svgRoot = n; const defs = svgEl('defs', {}, svgRoot);
      defs.innerHTML = `<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="0" gradientUnits="objectBoundingBox"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>`;
      const cp = svgEl('clipPath', { id: id + 'c' }, defs); shapes.forEach(e => cp.appendChild(e.cloneNode(true)));
      const vb = (svgRoot.getAttribute('viewBox') || '0 0 100 100').split(/\s+/).map(Number), g = svgEl('g', { 'clip-path': `url(#${id}c)` }, svgRoot);
      const band = svgEl('rect', { x: vb[0], y: vb[1] - vb[3], width: vb[2] * .22, height: vb[3] * 3, fill: `url(#${id})`, transform: `rotate(20 ${vb[0] + vb[2] / 2} ${vb[1] + vb[3] / 2})` }, g);
      const t0 = at + draw + (o.fillDur || .6) * .6; s.tween(null, t0, o.shineDur || .9, 'inOut', (e, _, p) => { band.setAttribute('x', vb[0] - vb[2] * .5 + e * vb[2] * 1.6); band.style.opacity = p <= 0 || p >= 1 ? 0 : 1; }); }
    if (o.cue !== false) { s.C.cue(s.start + at, 'riser', { auto: true, dur: draw }); s.C.cue(s.start + at + draw + .1, o.hit || 'chime', { auto: true }); }
    return n; };

  // ------------------------------------------------------------------ audio features (music visualiser / lyric sync)
  function makeAudio(F) { const A = { ok: !!F, features: F };
    A.level = t => { if (!F) return 0; const i = Math.min(F.rms.length - 1, Math.max(0, Math.round(t * F.fps))); return F.rms[i]; };
    A.band = (t, b) => { if (!F) return 0; const i = Math.min(F.bands.length - 1, Math.max(0, Math.round(t * F.fps))); return F.bands[i][b] || 0; };
    A.onsetNear = (t, w = .08) => F ? F.onsets.some(o => Math.abs(o - t) < w) : false;
    A.beatPhase = (t, bpm) => { const b = bpm || (F && F.bpm) || 120, off = (F && F.beat_offset) || 0; return (((t - off) * b / 60) % 1 + 1) % 1; };
    return A; }
  MS.lyrics = function (s, lines, o = {}) { lines.forEach((ln, i) => { const end = ln.end || (lines[i + 1] ? lines[i + 1].t : s.dur), n = s.text(ln.text, Object.assign({ size: o.size || 'h1', split: 'words', wrap: true, maxWidth: .9 }, o.textOpts || {}));
    P.wordReveal(s, n, ln.t, { each: o.each || 'fadeUp', stagger: Math.min(.12, (end - ln.t) * .5 / Math.max(1, ln.text.split(' ').length)) }); s.anim(n, 'fadeOut', end - .2, { dur: .2 }); }); };

  // ------------------------------------------------------------------ boot, dev player
  MS.boot = async function (build) {
    const spec = window.MS_SPEC || {};
    if (spec.audio && spec.audio.features_url) { try { spec.__features = await (await fetch(spec.audio.features_url)).json(); } catch (e) { console.warn('features not loaded', e); } }
    const C = new Composition(spec); MS.C = C;
    const fams = new Set(); for (const k of ['display', 'body', 'mono']) fams.add(C.fonts[k]);
    await Promise.all([...fams].map(f => document.fonts.load(`${f.style} ${f.weight} 40px ${f.family}`).catch(() => null)).concat((spec.preload_fonts || []).map(f => document.fonts.load(f))));
    await document.fonts.ready;
    await build(C);
    C.finalize();
    const missing = [...fams].filter(f => !document.fonts.check(`${f.style} ${f.weight} 40px ${f.family}`)).map(f => f.raw);
    window.__ms = { ready: true, render: t => C.render(t), meta: () => Object.assign(C.meta(), { missingFonts: missing }), audit: t => C.audit(t) };
    C.render(0);
    if (!RENDER) devPlayer(C);
  };
  function devPlayer(C) {
    const bar = div('', document.body); bar.id = 'ms-dev'; bar.innerHTML = `<button id="msp">▶</button><input id="mss" type="range" min="0" max="${C.duration}" step="${1 / C.fps}" value="0"><span id="mst">0.00</span>`;
    const fit = () => { const k = Math.min(innerWidth / C.W, (innerHeight - 44) / C.H); C.devScale = `scale(${k})`; C.stage.style.transform = C.devScale; }; fit(); addEventListener('resize', fit);
    let playing = false, t0 = 0, last = 0; const sl = bar.querySelector('#mss'), lab = bar.querySelector('#mst');
    const go = t => { C.render(t); sl.value = t; lab.textContent = t.toFixed(2) + ' / ' + C.duration.toFixed(2); };
    sl.oninput = () => { playing = false; go(+sl.value); };
    bar.querySelector('#msp').onclick = () => { playing = !playing; t0 = +sl.value; last = null; if (playing) requestAnimationFrame(loop); };
    function loop(ts) { if (!playing) return; if (last == null) last = ts; const t = t0 + (ts - last) / 1000; if (t >= C.duration) { playing = false; return; } go(t); requestAnimationFrame(loop); }
    addEventListener('keydown', e => { if (e.code === 'Space') bar.querySelector('#msp').click(); });
  }
  window.MS = MS;
})();
