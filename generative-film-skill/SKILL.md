---
name: generative-film
description: Make an original, unconventional animated MP4 video with its own synthesised soundtrack: every frame drawn in code, beat-synced. Use when asked for a creative, unique or "crazy" video on any topic.
---

# Generative Film

Produces a 45–120 s, 1920×1080, 30 fps MP4 in which **every frame is drawn in code** (pycairo + Pillow) and **every note is synthesised** (numpy/scipy). There's no stock footage, no AI imagery and no licensed music. The reference film is *SŪTRA* (Indian civilisation, 87 s). It's styled like a risograph print proof, and a red thread runs through ten chapters on a 96 BPM beat grid.

The quality comes from three things. Follow all three:
1. **An idea per chapter, not a picture per chapter.** Each scene *shows a mechanism* (a city grid being walked, a recitation braid, a fractal growing, a trajectory being flown). Don't illustrate a noun.
2. **One grid for picture and sound.** Everything is timed in *beats*. Music is written first, and every cut, pop and flash lands on a musical event.
3. **A strong, specific art direction** that is not "corporate explainer": print-proof chrome, mis-registered inks, native scripts and numerals, typewriter captions and stepped wipes.

## 0 · Setup (once per session)

```bash
pip install --break-system-packages pycairo fonttools   # numpy, scipy, Pillow usually present
which ffmpeg && python3 -c "from PIL import features; print('raqm', features.check('raqm'))"
```
Raqm must be True, because it provides complex-script shaping for Devanagari, Arabic, Tamil and similar scripts. Make a work dir. If this skill's folder has `scripts/`, copy `engine.py` and `audio_kit.py` into the work dir. Otherwise write them out from **Appendix A and B** verbatim. They are tested, so don't rewrite them. Fonts download on first use from the google/fonts GitHub repo, which the sandbox allows.

Set up a task list: concept → music → scenes → test frames → render → QA → deliver.

## 1 · Concept (before any code)

**Research.** Web-search every date, number, name and claim that will appear on screen. Prefix uncertain dates with "c.". Label diagrams "schematic" or "not to scale". Keep the facts few and precise, with captions of 12 words or fewer.

**Through-line object.** Find one visual device that appears in every chapter and gives the film its title. In SŪTRA it was a red thread that walks the streets, becomes a sound wave, draws the kolam, then flies the lunar trajectory. Other examples:
- Ocean history: a single wave crest.
- Coffee: a drip.
- Computing: a single bit.
- A company: its product's core gesture.

**Title.** Pick one word, ideally in the subject's own language, and give it a dictionary-style gloss on screen: `sūtra (n.) 1. a thread 2. a rule 3. that which holds things together`.

**Chapters.** Use 6–10, each built around a *distinct visual idea*. Draw on this repertoire:
- A diagram that builds itself: a city grid, a route map, an orbit, or a family tree of scripts.
- Numbers as art: a Pascal/Sierpiński triangle, π spiralling out, binary counters, or objects in doubling series.
- Recursion or fractals: a temple of temples, or a tree of trees.
- An oscilloscope of the actual soundtrack (`wave_at(f)`), which is great for chapters about speech or music.
- One unbroken line drawing: a kolam or mirror curve, a continuous-line portrait, or a signature.
- A kinetic word collage, such as loanwords, slogans, or place names stamped in on the beat.
- A countdown in native numerals, then a launch or event, then a hit.
- A bookend: the outro strings all the chapters as beads on the through-line, then returns to the opening image.

Test each chapter: if it could be replaced by a stock photo, rethink it.

**Palette.** Use a paper colour, a night colour and 5 inks named after the culture's own materials. SŪTRA used indigo, sindoor, haldi, rani and mor (peacock). Other examples:
- Japan: sumi, shu vermilion, ai indigo, kincha gold, matcha.
- Mexico: cochineal, maize, talavera blue, jade, marigold.
- Space: vantablack, sodium orange, hydrogen-alpha red, oxygen teal.

Alternate light and dark chapters, and make the drop chapter recolour on every bar.

**Type system.** Use 4–5 families. Pick a condensed display face for hero words, native script(s) for the subject, a mono face for captions and labels, and a soft italic serif for poetic lines. Use native numerals for the running year or counter. Useful google/fonts paths (`get_font(name, path, axes)`):

| role | path | axes |
|---|---|---|
| display | `ofl/anton/Anton-Regular.ttf` | – |
| mono | `ofl/spacemono/SpaceMono-Regular.ttf`, `…-Bold.ttf` | – |
| italic serif | `ofl/fraunces/Fraunces-Italic[SOFT,WONK,opsz,wght].ttf` | `[144,380,100,1]` |
| heavy serif | `ofl/fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf` | `[144,900,100,1]` |
| Devanagari | `ofl/tirodevanagarisanskrit/TiroDevanagariSanskrit-Regular.ttf` | – |
| Arabic | `ofl/notonaskharabic/NotoNaskhArabic[wght].ttf` | `[700]` |
| Tamil / Bengali / Thai | `ofl/notosanstamil/NotoSansTamil[wdth,wght].ttf` (same pattern) | `[700,100]` (wght, wdth order = font's) |
| CJK | `ofl/notoserifjp/NotoSerifJP[wght].ttf` | `[700]` |
| Brahmi | `ofl/notosansbrahmi/NotoSansBrahmi-Regular.ttf` | – |

Check axis order with `font_axes(name)`. If a path 404s, browse `https://github.com/google/fonts/tree/main/ofl/<family>` with WebFetch.

**Unconventional devices.** Pick several:
- Print-proof HUD: registration marks, ink swatches, a "PLATE 03 / 08 · NAME" label, a chapter number in an ancient numeral system, a running year in native numerals, and a progress thread with chapter beads.
- Riso mis-registration on hero type (`riso()`).
- Halftone fills.
- Vertical giant words.
- Text set on a circle (a stamp or seal).
- Typewriter captions.
- Stepped or iris wipes in two inks.
- Glitch stutters at seams, matched by audio stutters.
- A white flash on the drop.
- Film grain.

**Never:**
- A centred title card that fades.
- Gradients, glows or lens flares as decoration.
- Emoji or clip-art.
- Drawings of copyrighted characters, logos, or real people's faces.
- National flags used as decoration.
- Stereotype imagery.

## 2 · Timeline in beats

Use 90–110 BPM. A chapter is 8–16 beats. 96 BPM × 136 beats ≈ 87 s. Write a table first, like SŪTRA's:

| beats | chapter | picture | music |
|---|---|---|---|
| 0–12 | intro | a dot pulses, stretches into a line, title letters pop one per beat | drone swell, bell on each letter, riser |
| 12–28 | 1 | city grid assembles; thread walks the streets | hand-drum groove + plucked melody |
| 28–40 | 2 (breath) | oscilloscope of the audio + word braid | drone, chant, sparse |
| 40–52 | 3 | spinning wheel, letters stamp in, lineage tree | busier drums, riser, **stutter** at 51.5 |
| 52–64 | 4 | star trails accelerate, digits spiral | pad + bell arpeggio, big riser, **flash** |
| 64–80 | **DROP** | giant hero glyph, fractal grows 4 rows/beat, palette swaps per bar | kick, clap, sub bass, hook, boom |
| 80–92 | 5 | recursive structure grows by depth | half-time; **tihai lands on 92 = cut** |
| 92–108 | 6 | one-line drawing, then word collage | soft groove, then full groove |
| 108–120 | finale | native-numeral countdown → trajectory → landing hit | bells, rumble, riser, boom |
| 120–136 | outro | beads on the thread, title returns, dot | chant + pad + melody, fade |

The energy curve goes: quiet intro → build → breath → build → **drop on the most surprising idea** → half-time → finale hit → quiet bookend.

## 3 · Music first — `audio.py`

```python
from audio_kit import *
T = Track(bpm=96, beats=136, root=138.59, scale="raga_bhairavi")  # root Hz; SCALES has many cultures
T.drone_bed(0, 132, level=lambda b: 0.16 if 12 <= b < 120 else 0.3)
T.hand_drum(12, 28)                                   # keherwa-like default pattern
T.melody(12, [(2, 4, 1), (3, 5, 1.2, 6), (4, 7, 2.2)])  # (beat, degree, dur, glide-to degree)
T.riser_into(64, 4); T.at("fx", boom(), 64, 0.55)     # into the drop
T.groove(64, 80); T.stutter(51.5)
T.tihai(92)                                           # 3× phrase landing exactly on beat 92
T.mixdown("music.wav", fade_beats=(133, 136))          # also writes env.npy / wave.npy
```
- Buses are drone, perc, kick, bass, mel, fx and pad. Use `T.at(bus, signal, beat, gain, pan)` for any one-shot.
- Instruments: `drone, pluck (buzz=0 for clean), bell, voice, pad, sub, kick, clap, hat, drum_tone, drum_bass, drum_slap, drum_muted, riser, boom, rumble`.
- Match the scale and instruments to the culture. For example: hijaz + frame drum + oud-ish pluck (`buzz=0.8`); in_sen + koto-ish pluck (`buzz=0`) + bells; dorian + drone + clean plucks.
- **Every visual event gets a sound.** Wipes get risers, drops get a boom plus flash, cuts land on tihai or kick hits, and letters popping get bells.
- Check the result:
  - Loudness: `ffmpeg -i music.wav -af ebur128=framelog=quiet -f null -` should read about −16 to −14 LUFS.
  - Spectrogram: `ffmpeg -i music.wav -lavfi showspectrumpic=s=1600x500:scale=log:fscale=log spec.png`, then Read the image and check the section shapes.

## 4 · Scenes — `film.py`

```python
from engine import *
PAPER, NIGHT, INK = hx("F1E6CF"), hx("0A0D26"), hx("14121C")
INK1, INK2, INK3 = hx("1B2A6B"), hx("EE3B1E"), hx("FFB21A")
get_font("anton", "ofl/anton/Anton-Regular.ttf")
get_font("mono", "ofl/spacemono/SpaceMono-Regular.ttf")
# precompute geometry at module level with a seeded rng (deterministic across worker processes)

def s_intro(ctx, b, f):              # b = beat (float), f = frame
    bg(ctx, NIGHT)
    riso(ctx, lambda c: text(ctx, "TITLE", "anton", 400, c, W/2, 700, ax=.5, sc=back(ph(b, 4, .5))),
         PAPER, INK2, dark=True)
    return PAPER                      # foreground colour for the HUD

def hud(ctx, b, fg): reg_marks(ctx, fg, (INK1, INK2, INK3))

SCENES = [(0, s_intro), (12, s_ch1)]                 # (start beat, fn)
run(SCENES, 136, bpm=96, name="myfilm", hud=hud,
    wipes=[(12, INK2, INK3)],                        # (beat, c1, c2[, iris_wipe])
    glitches=[(51.5, 52.15)], flashes=[(64, WHITE, .5)], fade_out=134.6)
```
Scene rules:
- **Stateless.** Every value is a function of `b`, so frames can render in any order across processes.
- **Entrances** use `back(ph(b, start, 0.4))` for pops, `eo()` for slides and `eio()` for camera moves and line draws. Stagger items by 0.2–1 beat.
- **Beat life** comes from `pulse(b)` (1→0 each beat) for bounce and ring size, `env_at(f)` for loudness and `wave_at(f)` for the oscilloscope.
- **Draw lines live.** Use `path_partial(ctx, pts, cumlen(pts), frac)` and put a glowing bead at the returned tip.
- **Composition.**
  - Keep one hero element, one supporting diagram and one caption per scene.
  - Keep 110 px margins. HUD corners and the bottom band (y ≈ 960–1040) are reserved. Captions go at y ≈ 975 starting at x ≈ 560, or in the scene's empty zone.
  - Big type is big: 300–800 px hero glyphs. Captions are 18–22 px mono.
- **Contrast.** Alternate paper and night scenes. Use `riso(..., dark=True)` on dark backgrounds.
- Use `fit_size()` for long words in collages, and `text_circle()` for seals.
- The HUD can show chapter name, plate number, native numerals via a digit map, and a progress thread. When the skill folder has `examples/sutra/film.py`, its `hud()` and scenes are the full reference; its `examples/sutra/contact_sheet.png` shows the finished look.

## 5 · Test frames → contact sheet → fix (don't skip)

```bash
python3 film.py test 2 6 10 17 25 34 45 58 66 75 86 96 104 110 114 118 125 134
```
Read `sheet.png` and check:
- Overlapping or clipped text.
- Tofu boxes or missing glyphs. Run `missing_glyphs(font, string)` for every font × string. For example, Fraunces lacks → π ∞ ṅ, and Tiro Devanagari lacks → ≈ π.
- Unreadable captions at thumbnail size.
- Blank frames at chapter starts.
- Wrong facts or typos.
- Beats where nothing moves.

Iterate until every frame could be a poster. It usually takes 2–3 rounds.

## 6 · Render, QA, deliver

- `nohup python3 film.py render > render.log 2>&1 &`, then poll with Bash `sleep` loops (timeout ≤ 590 s each). It renders in parallel across all cores. Rough speed is 2–10 fps total depending on scene complexity; SŪTRA took about 20 min on 2 cores.
- Outputs are `name_full.mp4` (CRF 18, full quality) and `name.mp4`, a two-pass re-encode kept under 29 MB so it fits the 30 MB chat upload limit.
- QA:
  - `ffprobe -count_frames` to confirm the frame count and duration.
  - `ffmpeg -i name_full.mp4 -vf "fps=1/3.5,scale=384:216,tile=5x5" -frames:v 1 final.png`, then Read it.
  - Spot-check 2–3 full-size frames, including one after compression.
- **Download:** send `name.mp4` with SendUserFile (`display: "render"`); the card lets the user play and download it. Mention the full-quality file too. If the session is linked to the user's computer, offer to save `name_full.mp4` into one of their folders via `device_commit_files`, or send it if it is under 30 MB.
- To re-render only a fixed section, run `python3 film.py chunk <f0> <f1> part.mp4` for the affected frames, then concat and mux the pieces with ffmpeg as `run()` does.

## Final message to the user
Give the film's title and one line on its concept, the chapters as a compact list, what the music is, and any approximations ("c." dates, schematics). Don't recap the steps.

---
## Appendix A — `engine.py`
```python
"""engine.py — generative print-style film toolkit (pycairo + Pillow/raqm + ffmpeg).

A film script does:   from engine import *
then defines scenes as functions  scene(ctx, b, f) -> fg_color   (b = beat, f = frame)
and calls  run(SCENES, TOTAL_BEATS, bpm=..., wipes=..., hud=...)  at the bottom.
CLI of the film script:
    python film.py test 4 12.5 30      # render PNGs at those beats + contact sheet (sheet.png)
    python film.py render              # full parallel render -> film_full.mp4 + film.mp4 (<29 MB)
"""
import math, os, sys, subprocess, shutil
import numpy as np
import cairo
from PIL import Image, ImageFont, ImageDraw

W, H, FPS = 1920, 1080, 30
PI = math.pi
BPM = 96
BEAT = 60 / BPM


def set_tempo(bpm):
    global BPM, BEAT
    BPM, BEAT = bpm, 60 / bpm


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


WHITE, BLACK = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)

# ------------------------------------------------------------------ fonts
GF = "https://raw.githubusercontent.com/google/fonts/main/"
FONT_DIR = "fonts"
FONTS = {}  # name -> (path, variation-axes list | None)


def get_font(name, src, var=None):
    """Register a font. src = local path, or a google/fonts repo path such as
    'ofl/anton/Anton-Regular.ttf' or 'ofl/fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf'.
    var = axis values in the font's axis order (see font_axes)."""
    os.makedirs(FONT_DIR, exist_ok=True)
    local = os.path.join(FONT_DIR, name + ".ttf")
    if os.path.exists(src):
        local = src
    elif not os.path.exists(local):
        url = GF + src.replace("[", "%5B").replace("]", "%5D")
        subprocess.run(["curl", "-sSfL", url, "-o", local], check=True)
    FONTS[name] = (local, var)


def font_axes(name):
    f = ImageFont.truetype(FONTS[name][0], 20)
    try:
        return [(a["name"], a["minimum"], a["maximum"]) for a in f.get_variation_axes()]
    except Exception:
        return []


def missing_glyphs(name, s):
    """Characters of s the font cannot draw — check every string before rendering."""
    from fontTools.ttLib import TTFont
    cm = TTFont(FONTS[name][0]).getBestCmap()
    return "".join(sorted({c for c in s if not c.isspace() and ord(c) not in cm}))


# ------------------------------------------------------------------ text (PIL raqm shaping -> cairo surface)
_fc, _tc = {}, {}


def font(name, size):
    k = (name, size)
    if k not in _fc:
        p, var = FONTS[name]
        f = ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
        if var:
            f.set_variation_by_axes(var)
        _fc[k] = f
    return _fc[k]


def _tsurf(txt, name, size, color, stroke=0):
    k = (txt, name, size, color, stroke)
    if k in _tc:
        return _tc[k]
    f = font(name, size)
    l, t, r, b = f.getbbox(txt, anchor="ls", stroke_width=stroke)
    p = 4
    w, h = int(r - l + 2 * p), int(b - t + 2 * p)
    img = Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = tuple(int(c * 255) for c in color) + (255,)
    if stroke:
        d.text((p - l, p - t), txt, font=f, anchor="ls", fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=col)
    else:
        d.text((p - l, p - t), txt, font=f, anchor="ls", fill=col)
    a = np.asarray(img).astype(np.float32)
    al = a[..., 3] / 255
    buf = np.empty((h, w, 4), np.uint8)  # cairo = premultiplied BGRA
    buf[..., 0] = a[..., 2] * al
    buf[..., 1] = a[..., 1] * al
    buf[..., 2] = a[..., 0] * al
    buf[..., 3] = a[..., 3]
    s = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, w, h, w * 4)
    res = (s, buf, p - l, p - t, l, t, r, b)
    if len(_tc) > 4000:
        _tc.clear()
    _tc[k] = res
    return res


def text(ctx, txt, name, size, color, x, y, ax=0.0, ay=None, alpha=1.0, rot=0.0, sc=1.0, stroke=0, op=None):
    """Draw shaped text. (x,y) is the baseline point; ax=0/0.5/1 left/centre/right;
    ay=None baseline, 0.5 = vertical centre of ink. Returns drawn width."""
    if alpha <= 0.003 or sc <= 0.001 or not txt:
        return 0
    s, buf, ox, oy, l, t, r, b = _tsurf(txt, name, size, color, stroke)
    px = l + ax * (r - l)
    py = 0 if ay is None else t + ay * (b - t)
    ctx.save()
    if op is not None:
        ctx.set_operator(op)
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    if sc != 1:
        ctx.scale(sc, sc)
    ctx.set_source_surface(s, -(ox + px), -(oy + py))
    ctx.paint_with_alpha(alpha) if alpha < 1 else ctx.paint()
    ctx.restore()
    return (r - l) * sc


def tw(txt, name, size):
    l, t, r, b = font(name, size).getbbox(txt, anchor="ls")
    return r - l


def fit_size(txt, name, max_w, max_size):
    return int(min(max_size, max_size * max_w / max(tw(txt, name, max_size), 1)))


def text_circle(ctx, txt, name, size, color, cx, cy, R, ang0, alpha=1.0):
    f = font(name, size)
    a = ang0
    for c in txt:
        w = f.getlength(c)
        a += (w / 2) / R
        if c != " ":
            text(ctx, c, name, size, color, cx + R * math.cos(a), cy + R * math.sin(a), ax=0.5, rot=a + PI / 2,
                 alpha=alpha)
        a += (w / 2) / R


def typewriter(ctx, s, name, size, color, x, y, b, t0, beats=1.2, **kw):
    n = int(len(s) * cl((b - t0) / beats))
    return text(ctx, s[:n], name, size, color, x, y, **kw)


# ------------------------------------------------------------------ timing / easing  (all in beats)
def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def eo(x):  # ease-out cubic
    x = cl(x); return 1 - (1 - x) ** 3


def eio(x):  # ease-in-out cubic
    x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back(x, c1=1.9):  # overshoot pop
    x = cl(x); c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ph(b, start, dur):  # 0..1 progress of a phase
    return cl((b - start) / dur)


def pulse(b, k=5.0):  # 1 on every beat, decaying
    return math.exp(-(b % 1) * k)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ paint helpers
def bg(ctx, c):
    ctx.set_source_rgb(*c); ctx.paint()


def rgba(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0], c[1], c[2], a)


REG = [5.0, 4.0]  # riso mis-registration offset, jittered per 3 frames by the renderer


def riso(ctx, fn, main, off, dark=False, k=1.0):
    """Two-ink print: fn(color) draws a shape; offset copy in `off` ink under the `main` ink.
    Use dark=True on dark backgrounds (screen blend) else multiply."""
    ctx.save()
    ctx.translate(REG[0] * k, REG[1] * k)
    ctx.set_operator(cairo.OPERATOR_SCREEN if dark else cairo.OPERATOR_MULTIPLY)
    fn(off)
    ctx.restore()
    fn(main)


_hp = {}


def halftone(color, step=11, r=2.8, ang=0.5):
    """Returns a repeating dot pattern usable as a cairo source (ctx.set_source(halftone(...)))."""
    k = (color, step, r, ang)
    if k not in _hp:
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, step, step)
        c = cairo.Context(s)
        c.set_source_rgb(*color); c.arc(step / 2, step / 2, r, 0, 2 * PI); c.fill()
        pat = cairo.SurfacePattern(s); pat.set_extend(cairo.EXTEND_REPEAT)
        m = cairo.Matrix(); m.rotate(ang); pat.set_matrix(m)
        _hp[k] = (pat, s)
    return _hp[k][0]


def reg_marks(ctx, fg, swatches=(), a=0.6):
    rgba(ctx, fg, a); ctx.set_line_width(1.3)
    for (x, y) in ((36, 36), (W - 36, 36), (36, H - 36), (W - 36, H - 36)):
        ctx.arc(x, y, 9, 0, 2 * PI); ctx.stroke()
        ctx.move_to(x - 17, y); ctx.line_to(x + 17, y); ctx.move_to(x, y - 17); ctx.line_to(x, y + 17); ctx.stroke()
    for i, c in enumerate(swatches):
        rgba(ctx, c); ctx.rectangle(29, H / 2 - 70 + i * 22, 14, 14); ctx.fill()


# ------------------------------------------------------------------ paths
def cumlen(pts):
    d = np.hypot(*np.diff(pts, axis=0).T)
    return np.concatenate([[0], np.cumsum(d)])


def path_partial(ctx, pts, cum, frac):
    """Adds the first `frac` of a polyline to ctx (then stroke). Returns the tip point — draw a glowing
    bead there so the line reads as being drawn live."""
    L = cum[-1] * cl(frac)
    if L <= 0:
        return None
    i = int(np.searchsorted(cum, L))
    ctx.move_to(*pts[0])
    for p in pts[1:i]:
        ctx.line_to(p[0], p[1])
    if i < len(pts):
        a, b_ = pts[i - 1], pts[i]
        seg = cum[i] - cum[i - 1]
        t = (L - cum[i - 1]) / seg if seg > 0 else 0
        e = a + (b_ - a) * t
        ctx.line_to(e[0], e[1])
        return e
    return pts[-1]


def polyline(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(p[0], p[1])


def chaikin(P, it=4, closed=True):
    for _ in range(it):
        P1 = np.roll(P, -1, axis=0)
        Q = np.empty((len(P) * 2, 2))
        Q[0::2] = 0.75 * P + 0.25 * P1
        Q[1::2] = 0.25 * P + 0.75 * P1
        P = Q
    return np.vstack([P, P[:1]]) if closed else P


def bezier(p0, p1, p2, p3, n=40):
    s = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return (1 - s) ** 3 * p0 + 3 * (1 - s) ** 2 * s * p1 + 3 * (1 - s) * s ** 2 * p2 + s ** 3 * p3


# ------------------------------------------------------------------ transitions & texture
def make_grain(seed, amount=0.13):
    r = np.random.default_rng(seed)
    g = r.normal(128, 40, (H, W))
    low = np.asarray(Image.fromarray((r.random((27, 48)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                     np.float32)
    g = np.clip(g + (low - 128) * 0.5, 0, 255)
    buf = np.empty((H, W, 4), np.uint8)
    v = (g * amount).astype(np.uint8)
    buf[..., 0] = v; buf[..., 1] = v; buf[..., 2] = v; buf[..., 3] = int(255 * amount)
    return cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, W, H, W * 4), buf


_GRAIN = []


def grain(ctx, f):
    if not _GRAIN:
        _GRAIN.extend(make_grain(s) for s in range(3))
    ctx.save(); ctx.set_operator(cairo.OPERATOR_OVERLAY)
    ctx.set_source_surface(_GRAIN[(f // 2) % 3][0], 0, 0); ctx.paint(); ctx.restore()


def step_wipe(ctx, b, B, c1, c2, step=54, zig=34):
    """Two-colour stepped wipe centred on beat B (covers the cut from B-0.5 to B+0.5)."""
    p = b - (B - 0.5)
    if p < 0 or p > 1:
        return

    def edge(X, down):
        pts = []
        for yi in range(0, H + step, step):
            off = zig * abs(((yi // step) % 10) - 5)
            pts += [(X + off, yi), (X + off, yi + step)]
        return pts if down else pts[::-1]
    for c, lag in ((c1, 0.0), (c2, 0.14)):
        q = cl((p - lag) / 0.86)
        R = -400 + (W + 800) * eio(min(q * 2, 1))
        L = -400 + (W + 800) * eio(max(q * 2 - 1, 0))
        if R - L < 1:
            continue
        polyline(ctx, edge(R, True) + edge(L, False)); ctx.close_path(); rgba(ctx, c); ctx.fill()


def iris_wipe(ctx, b, B, c1, c2, cx=W / 2, cy=H / 2):
    """Alternative: two expanding/contracting discs."""
    p = b - (B - 0.5)
    if p < 0 or p > 1:
        return
    Rm = math.hypot(W, H) / 2 + 50
    for c, lag in ((c1, 0.0), (c2, 0.14)):
        q = cl((p - lag) / 0.86)
        ro = Rm * eio(min(q * 2, 1)); ri = Rm * eio(max(q * 2 - 1, 0))
        ctx.new_path(); ctx.arc(cx, cy, ro, 0, 2 * PI); ctx.arc_negative(cx, cy, ri, 2 * PI, 0)
        rgba(ctx, c); ctx.fill()


def glitch(surf, f, bands=9, shift=160):
    arr = np.ndarray((H, W, 4), np.uint8, buffer=surf.get_data())
    r = np.random.default_rng(f)
    for _ in range(bands):
        y0 = int(r.integers(0, H - 40)); hh = int(r.integers(8, 90))
        arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(r.integers(-shift, shift)), axis=1)
    ch = int(r.integers(0, 3))
    arr[..., ch] = np.roll(arr[..., ch], 14, axis=1)
    surf.mark_dirty()


# ------------------------------------------------------------------ audio-reactive data (written by audio_kit.mixdown)
ENV = np.zeros(1)
WAVE = np.zeros((1, 512))


def load_audio_data(env="env.npy", wave="wave.npy"):
    global ENV, WAVE
    if os.path.exists(env):
        ENV = np.load(env)
    if os.path.exists(wave):
        WAVE = np.load(wave)


def env_at(f):
    return float(ENV[min(f, len(ENV) - 1)])


def wave_at(f):
    return WAVE[min(f, len(WAVE) - 1)]


# ------------------------------------------------------------------ renderer
def make_render(scenes, wipes=(), glitches=(), flashes=(), hud=None, fade_out=None, grain_on=True):
    """scenes: [(start_beat, fn)], fn(ctx, b, f) -> fg colour for the HUD.
    wipes: [(beat, c1, c2)] or [(beat, c1, c2, wipe_fn)]; glitches: [(b0, b1)];
    flashes: [(beat, colour, dur_beats)]; hud(ctx, b, fg); fade_out: beat where fade-to-black starts."""
    def render(f, surf):
        b = f / FPS / BEAT
        r = np.random.default_rng(f // 3)
        REG[0], REG[1] = 4 + 3 * r.random(), 3 + 3 * r.random()
        ctx = cairo.Context(surf)
        ctx.set_operator(cairo.OPERATOR_OVER)
        fn = scenes[0][1]
        for s, fn_ in scenes:
            if b >= s:
                fn = fn_
        fg = fn(ctx, b, f)
        ctx = cairo.Context(surf)
        for w_ in wipes:
            (w_[3] if len(w_) > 3 else step_wipe)(ctx, b, w_[0], w_[1], w_[2])
        for B, c, d in flashes:
            if B <= b < B + d:
                rgba(ctx, c, 1 - ph(b, B, d)); ctx.paint()
        if hud:
            hud(ctx, b, fg or WHITE)
        if grain_on:
            grain(ctx, f)
        if fade_out is not None and b > fade_out:
            rgba(ctx, BLACK, ph(b, fade_out, 3.0)); ctx.paint()
        surf.flush()
        for g0, g1 in glitches:
            if g0 <= b < g1:
                glitch(surf, f)
    return render


def _encode(render, a, bnd, out):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s",
                          "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", out], stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    for fr in range(a, bnd):
        render(fr, surf)
        p.stdin.write(bytes(surf.get_data()))
        if fr % 150 == 0:
            print(out, fr, flush=True)
    p.stdin.close(); p.wait()


def contact_sheet(paths, out="sheet.png", cols=3, cw=640):
    ims = [Image.open(p).convert("RGB").resize((cw, cw * H // W)) for p in paths]
    ch = cw * H // W
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols, ch * rows))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * cw, (i // cols) * ch))
    sheet.save(out)
    return out


def deliver(src, out, target_mb=29.0, audio_kbps=192):
    """Two-pass re-encode so the file fits an upload limit (SendUserFile caps at 30 MB)."""
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                         "default=nw=1:nk=1", src]).decode())
    vk = int(target_mb * 8 * 1024 * 1024 / dur / 1000 * 0.97 - audio_kbps)
    log = os.path.join(os.path.dirname(os.path.abspath(out)), "pass")
    base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c:v", "libx264", "-preset", "slow",
            "-b:v", "%dk" % vk, "-passlogfile", log]
    subprocess.run(base + ["-pass", "1", "-an", "-f", "null", "/dev/null"], check=True)
    subprocess.run(base + ["-pass", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "%dk" % audio_kbps,
                           "-movflags", "+faststart", out], check=True)
    for f in os.listdir(os.path.dirname(os.path.abspath(out))):
        if f.startswith("pass"):
            os.remove(os.path.join(os.path.dirname(os.path.abspath(out)), f))
    return out


def run(scenes, total_beats, bpm=96, audio="music.wav", name="film", workers=None, **kw):
    """CLI entry point for a film script. See module docstring."""
    set_tempo(bpm)
    load_audio_data()
    render = make_render(scenes, **kw)
    nf = int(round(total_beats * BEAT * FPS))
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    if mode == "test":
        os.makedirs("frames", exist_ok=True)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        paths = []
        for bb in map(float, sys.argv[2:]):
            fr = min(int(bb * BEAT * FPS), nf - 1)
            render(fr, surf)
            pth = "frames/b%07.2f.png" % bb
            surf.write_to_png(pth); paths.append(pth)
        print(contact_sheet(paths))
    elif mode == "chunk":
        _encode(render, int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif mode == "render":
        n = workers or os.cpu_count() or 2
        cuts = [nf * i // n for i in range(n + 1)]
        parts = ["_part%02d.mp4" % i for i in range(n)]
        procs = [subprocess.Popen([sys.executable, sys.argv[0], "chunk", str(cuts[i]), str(cuts[i + 1]), parts[i]])
                 for i in range(n)]
        if any(p.wait() for p in procs):
            sys.exit("a render chunk failed")
        with open("_list.txt", "w") as fh:
            fh.writelines("file %s\n" % p for p in parts)
        full = name + "_full.mp4"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "_list.txt"]
        if os.path.exists(audio):
            cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
        subprocess.run(cmd + ["-c:v", "copy", "-movflags", "+faststart", full], check=True)
        for p in parts + ["_list.txt"]:
            os.remove(p)
        small = name + ".mp4"
        if os.path.getsize(full) > 29 * 1024 * 1024:
            deliver(full, small)
        else:
            shutil.copy(full, small)
        print("done:", full, "(%.1f MB)" % (os.path.getsize(full) / 2 ** 20), small,
              "(%.1f MB)" % (os.path.getsize(small) / 2 ** 20))
    return render
```

## Appendix B — `audio_kit.py`
```python
"""audio_kit.py — synthesise an original, licence-free soundtrack in numpy/scipy.

    from audio_kit import *
    T = Track(bpm=96, beats=136, root=138.59)          # root = tonic in Hz (C#3 here)
    T.add("drone", drone(T.hz(0)), T.tb(0), 0.3)      # bus, signal, time-in-seconds, gain, pan
    ...
    T.mixdown("music.wav")                            # also writes env.npy / wave.npy for visuals

Everything is placed in BEATS (T.tb(beat) -> seconds) so music and picture share one grid.
"""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100
_rng = np.random.default_rng(7)

# semitone sets — pick one that belongs to the film's culture/mood
SCALES = {
    "raga_bhairavi": [0, 1, 3, 5, 7, 8, 10],
    "raga_yaman": [0, 2, 4, 6, 7, 9, 11],
    "minor_penta": [0, 3, 5, 7, 10],
    "major_penta": [0, 2, 4, 7, 9],
    "hijaz": [0, 1, 4, 5, 7, 8, 10],          # West Asia / Mediterranean
    "in_sen": [0, 1, 5, 7, 10],               # Japan
    "pelog": [0, 1, 3, 7, 8],                 # Indonesia (approx.)
    "dorian": [0, 2, 3, 5, 7, 9, 10],         # Celtic / folk
    "phrygian_dom": [0, 1, 4, 5, 7, 8, 10],   # flamenco / klezmer
    "whole_tone": [0, 2, 4, 6, 8, 10],        # dreamlike / space
}


def tt(d):
    return np.arange(int(d * SR)) / SR


def _bp(lo, hi, n):
    return signal.sosfilt(signal.butter(2, [lo, hi], "band", fs=SR, output="sos"), n)


# ------------------------------------------------------------------ instruments (each returns a mono np array)
def drone(f, dur=4.5):
    """Tanpura-like buzzing drone note; retrigger every beat cycling (5th, root, root, low root)."""
    t = tt(dur); y = np.zeros_like(t); ph = _rng.uniform(0, 2 * np.pi, 60)
    for k in range(1, 48):
        if f * k > 9000:
            break
        bloom = 0.55 + 0.45 * np.sin(2 * np.pi * t * (0.35 + 0.11 * k) + ph[k])
        env = k ** -0.55 * np.exp(-t / (3.2 / (1 + 0.025 * k))) * bloom
        y += env * (np.sin(2 * np.pi * f * k * t + ph[k]) + 0.5 * np.sin(2 * np.pi * f * k * 1.0015 * t))
    y *= 1 - np.exp(-t / 0.004)
    return y / np.max(np.abs(y))


def pluck(f0, dur=1.4, f1=None, g0=0.05, gd=0.18, bright=1.0, buzz=2.2):
    """Plucked string (sitar/oud/koto-ish). f1 = glide (meend) target. buzz=0 for a clean guitar/harp."""
    t = tt(max(dur, 0.6))
    if f1 is None:
        f = np.full_like(t, f0)
    else:
        s = np.clip((t - g0) / gd, 0, 1); s = s * s * (3 - 2 * s)
        f = f0 * (f1 / f0) ** s
    phase = 2 * np.pi * np.cumsum(f) / SR
    y = np.zeros_like(t)
    for k in range(1, 30):
        if f0 * k > 11000:
            break
        a = k ** -0.8 * ((1.6 * bright) if 3 <= k <= 8 else 1.0)
        y += a * np.sin(k * phase) * np.exp(-t * (1.2 + 0.55 * k))
    y /= np.max(np.abs(y))
    if buzz:
        y = np.tanh(buzz * y) / np.tanh(buzz)
    y += _rng.normal(0, 1, len(t)) * np.exp(-t / 0.002) * 0.3
    return y * np.exp(-t / (len(t) / SR * 0.7))


def bell(f, dur=2.2, idx=2.5, ratio=3.5):
    t = tt(dur)
    m = idx * np.exp(-t / 0.5) * np.sin(2 * np.pi * f * ratio * t)
    return np.sin(2 * np.pi * f * t + m) * np.exp(-t / (dur * 0.35)) * (1 - np.exp(-t / 0.002))


def voice(f, dur, vowel=(700, 1220, 2600), vib=0.006):
    """Formant 'aah' choir / chant. vowels: a=(700,1220,2600) o=(500,900,2400) u=(350,700,2500)."""
    t = tt(dur)
    v = 1 + vib * np.sin(2 * np.pi * 5.2 * t) * np.clip(t, 0, 1)
    saw = 2 * ((np.cumsum(f * v) / SR) % 1) - 1
    y = sum(g * _bp(fm * 0.85, fm * 1.15, saw) for fm, g in zip(vowel, (1, 0.5, 0.25)))
    a = np.clip(t / 1.2, 0, 1) * np.clip((dur - t) / 1.5, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def pad(freqs, dur, cutoff=1400):
    t = tt(dur); y = np.zeros_like(t)
    for f in freqs:
        for d in (-0.004, 0.0, 0.005):
            y += 2 * ((f * (1 + d) * t + _rng.uniform()) % 1) - 1
    y = signal.sosfilt(signal.butter(2, cutoff, "low", fs=SR, output="sos"), y)
    a = np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 2.0, 0, 1)
    return y * a / (np.max(np.abs(y)) + 1e-9)


def sub(f, dur):
    t = tt(dur)
    y = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.3 * y) * (1 - np.exp(-t / 0.005)) * np.exp(-t / (dur * 1.5)) * np.clip((dur - t) / 0.03, 0, 1)


def kick():
    t = tt(0.5)
    y = np.sin(2 * np.pi * np.cumsum(48 + 120 * np.exp(-t / 0.035)) / SR) * np.exp(-t / 0.28)
    return np.tanh(1.6 * (y + 0.4 * _rng.normal(0, 1, len(t)) * np.exp(-t / 0.003)))


def clap():
    t = tt(0.4); n = _bp(900, 3000, _rng.normal(0, 1, len(t)))
    env = sum(np.where(t >= d, np.exp(-(t - d) / 0.008), 0) for d in (0, 0.011, 0.022))
    return n * (env + 0.6 * np.where(t > 0.03, np.exp(-(t - 0.03) / 0.11), 0)) * 0.8


def hat(open_=False):
    t = tt(0.3 if open_ else 0.06)
    n = signal.sosfilt(signal.butter(4, 7000, "high", fs=SR, output="sos"), _rng.normal(0, 1, len(t)))
    return n * np.exp(-t / (0.08 if open_ else 0.012)) * 0.35


def drum_tone(pitch=277, dec=0.32, bright=1.0):
    """Resonant hand-drum 'na/tin' (tabla, darbuka doum-tek, djembe tone by pitch)."""
    t = tt(0.9); y = np.zeros_like(t)
    for k, a in zip(range(1, 6), [1, .6, .45, .3, .2]):
        y += (a if k == 1 else a * bright) * np.sin(2 * np.pi * pitch * k * t) * np.exp(-t / (dec / (1 + .6 * (k - 1))))
    y += 0.6 * _bp(2500, 6000, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.006)
    return y * 0.5


def drum_bass(f0=68, f1=96, dec=0.75):
    """Pitch-bent bass stroke (tabla 'ge', frame drum 'dum')."""
    t = tt(1.2); s = np.clip(t / 0.28, 0, 1)
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * (1 - (1 - s) ** 2)) / SR
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t / dec) * (1 - np.exp(-t / 0.003)) * 0.9


def drum_slap():
    t = tt(0.12)
    return (0.5 * _bp(1500, 5000, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.018)
            + 0.3 * np.sin(2 * np.pi * 320 * t) * np.exp(-t / 0.03)) * 0.7


def drum_muted():
    t = tt(0.1)
    return _bp(150, 700, _rng.normal(0, 1, len(t))) * np.exp(-t / 0.02) * 1.2


def riser(dur, f0=200, f1=2400):
    t = tt(dur); n = _rng.normal(0, 1, len(t)); out = np.zeros_like(t); seg = int(0.05 * SR)
    for i in range(0, len(t), seg):
        c = f0 * (f1 / f0) ** (i / len(t))
        out[i:i + seg] = _bp(c * 0.7, min(c * 1.6, 20000), n[i:i + seg])
    ph = np.cumsum(110 * 2 ** (3 * (t / dur) ** 2)) / SR
    return (out + 0.3 * (2 * (ph % 1) - 1)) * (t / dur) ** 2


def boom(dur=3.0):
    t = tt(dur)
    y = np.sin(2 * np.pi * np.cumsum(30 + 45 * np.exp(-t / 0.2)) / SR) * np.exp(-t / 0.9)
    n = signal.sosfilt(signal.butter(2, 900, "low", fs=SR, output="sos"), _rng.normal(0, 1, len(t)))
    return np.tanh(2 * y) + 0.5 * n * np.exp(-t / 0.35)


def rumble(dur):
    t = tt(dur)
    return signal.sosfilt(signal.butter(2, 180, "low", fs=SR, output="sos"), _rng.normal(0, 1, len(t))) * \
        np.clip(t / 0.3, 0, 1) * 3.5


# ------------------------------------------------------------------ track
class Track:
    SEND = {"drone": 0.35, "perc": 0.18, "kick": 0.02, "bass": 0.0, "mel": 0.45, "fx": 0.5, "pad": 0.5}
    GAIN = {"drone": 0.55, "perc": 0.8, "kick": 0.9, "bass": 0.75, "mel": 0.62, "fx": 0.6, "pad": 0.55}

    def __init__(self, bpm, beats, root=138.59, scale="raga_bhairavi", tail=2.0, fps=30):
        self.bpm, self.beat, self.beats, self.root, self.fps = bpm, 60 / bpm, beats, root, fps
        self.scale = SCALES[scale] if isinstance(scale, str) else scale
        self.dur = beats * self.beat + tail
        self.N = int(self.dur * SR)
        self.buses = {k: np.zeros((2, self.N)) for k in self.SEND}
        self.stutters = []
        self._cache = {}

    def tb(self, b):
        return b * self.beat

    def hz(self, semi, octv=0):
        return self.root * 2 ** (octv + semi / 12)

    def deg(self, d, octv=0):
        """Scale degree -> Hz (d may exceed scale length or be negative)."""
        n = len(self.scale)
        return self.hz(self.scale[d % n], octv + d // n)

    def add(self, bus, sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= self.N or i < 0:
            return
        sig = sig[: self.N - i]
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
        self.buses[bus][0, i:i + len(sig)] += sig * gain * l
        self.buses[bus][1, i:i + len(sig)] += sig * gain * r

    def at(self, bus, sig, beat, gain=1.0, pan=0.0):
        self.add(bus, sig, self.tb(beat), gain, pan)

    def cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # ---- pattern helpers
    def drone_bed(self, b0, b1, level=lambda b: 0.3):
        notes = [self.hz(7, -1), self.hz(0), self.hz(0), self.hz(0, -1)]
        sigs = [self.cached(("drone", i), lambda f=f: drone(f)) for i, f in enumerate(notes)]
        for b in range(int(b0), int(b1)):
            self.at("drone", sigs[b % 4], b, level(b), [-0.4, 0.3, -0.1, 0.4][b % 4])

    def melody(self, b0, notes, octv=1, gain=0.55, pan=0.1, **pk):
        """notes: [(beat_offset, scale_degree, dur_beats?, glide_degree?)]; degrees index T.scale."""
        for n in notes:
            f0 = self.deg(n[1], octv)
            f1 = self.deg(n[3], octv) if len(n) > 3 and n[3] is not None else None
            self.at("mel", pluck(f0, self.tb(n[2]) if len(n) > 2 else 1.4, f1, **pk), b0 + n[0], gain, pan)

    def hand_drum(self, b0, b1, pattern=("B", "b", "t", "s", "t", "m", "B", "t"), step=0.5, gain=1.0, fills=True):
        """B=bass+tone, b=bass, t=tone, T=long tone, s=slap, m=muted, '-'=rest. Default is keherwa-like."""
        S = {"b": self.cached("db", drum_bass), "t": self.cached("dt", drum_tone),
             "T": self.cached("dT", lambda: drum_tone(dec=0.55, bright=0.35)),
             "s": self.cached("ds", drum_slap), "m": self.cached("dm", drum_muted)}
        b, bar = b0, 0
        while b < b1 - 1e-6:
            for i, s in enumerate(pattern):
                bb = b + i * step
                if bb >= b1:
                    break
                g = gain * (1.0 if i % 2 == 0 else 0.8)
                if s == "B":
                    self.at("perc", S["b"], bb, g * 0.9, -0.15); self.at("perc", S["t"], bb, g, 0.15)
                elif s in S:
                    self.at("perc", S[s], bb, g, {"b": -.15, "t": .2, "T": .2, "s": .3, "m": -.3}[s])
            span = len(pattern) * step
            if fills and bar % 2 == 1:
                self.at("perc", S["s"], b + span - 0.75, gain * 0.7); self.at("perc", S["s"], b + span - 0.25, gain * 0.6)
            b += span; bar += 1

    def tihai(self, land, phrase="Bssb", step=0.25, gap=0.5):
        """Rhythmic cadence: phrase ×3 ending exactly ON `land` beat (pair with a visual hit)."""
        S = {"B": (drum_bass, drum_tone), "b": (drum_bass,), "s": (drum_slap,), "t": (drum_tone,)}
        L = len(phrase) * step
        start = land - (3 * L + 2 * gap) + step
        for r in range(3):
            for i, c in enumerate(phrase):
                for fn in S[c]:
                    self.at("perc", self.cached(("th", fn.__name__), fn), start + r * (L + gap) + i * step, 1.1)
        self.at("kick", self.cached("kick", kick), land, 0.8)

    def groove(self, b0, b1, claps=True, four=True, bass_roots=(0, -2, -7, -5), hats=True):
        K, C, Hh = self.cached("kick", kick), self.cached("clap", clap), self.cached("hat", hat)
        for b in np.arange(b0, b1, 1.0):
            if four or (b - b0) % 2 == 0:
                self.at("kick", K, b, 0.95)
            if claps and int(b - b0) % 2 == 1:
                self.at("perc", C, b, 0.55)
            if hats:
                self.at("perc", Hh, b + 0.5, 0.6, 0.3); self.at("perc", Hh, b + 0.75, 0.25, -0.3)
        for i, b in enumerate(np.arange(b0, b1, 4.0)):
            for s in np.arange(0, 4, 0.5):
                self.at("bass", sub(self.hz(bass_roots[i % len(bass_roots)], -1), self.tb(0.42)), b + s,
                        0.55 if s % 1 else 0.4)

    def riser_into(self, beat, length=4, gain=0.4):
        self.at("fx", riser(self.tb(length)), beat - length, gain)

    def stutter(self, beat, reps=4, div=0.125):
        self.stutters.append((beat, reps, div))

    # ---- mix
    def mixdown(self, path="music.wav", fade_beats=(None, None)):
        kick_env = signal.sosfilt(signal.butter(1, 8, "low", fs=SR, output="sos"), np.abs(self.buses["kick"][0]))
        kick_env /= kick_env.max() + 1e-9
        duck = 1 - 0.7 * np.clip(kick_env * 3, 0, 1)
        for k in ("bass", "drone", "pad"):
            self.buses[k] *= duck
        irt = tt(2.8)
        ir = np.stack([_rng.normal(0, 1, len(irt)), _rng.normal(0, 1, len(irt))]) * np.exp(-irt / 0.7)
        ir = signal.sosfilt(signal.butter(1, 5000, "low", fs=SR, output="sos"), ir)
        ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
        dry = sum(v * self.GAIN[k] for k, v in self.buses.items())
        wet_in = sum(v * self.GAIN[k] * self.SEND[k] for k, v in self.buses.items())
        mix = dry + np.stack([signal.fftconvolve(wet_in[c], ir[c])[:self.N] for c in range(2)]) * 0.55
        for b, reps, div in self.stutters:
            i0, L = int(self.tb(b) * SR), int(self.tb(div) * SR)
            seg = mix[:, i0:i0 + L].copy()
            for r in range(reps):
                mix[:, i0 + r * L:i0 + (r + 1) * L] = seg[:, :mix[:, i0 + r * L:i0 + (r + 1) * L].shape[1]] * (1 - .15 * r)
        mix = signal.sosfilt(signal.butter(2, 28, "high", fs=SR, output="sos"), mix)
        mix /= np.max(np.abs(mix)); mix = np.tanh(1.5 * mix) / np.tanh(1.5)
        fs_, fe_ = fade_beats
        if fs_ is not None:
            a, e = int(self.tb(fs_) * SR), int(self.tb(fe_) * SR)
            fade = np.ones(self.N); fade[a:e] = np.linspace(1, 0, e - a) ** 2; fade[e:] = 0
            mix *= fade
        mix *= 0.89 / np.max(np.abs(mix))
        wavfile.write(path, SR, (mix.T * 32767).astype(np.int16))
        # per-frame loudness + waveform snapshot for audio-reactive visuals
        mono, spf = mix.mean(0), SR // self.fps
        nf = int(self.dur * self.fps)
        env = np.array([np.sqrt(np.mean(mono[i * spf:(i + 1) * spf] ** 2)) for i in range(nf)])
        np.save("env.npy", env / (env.max() + 1e-9))
        wave = np.zeros((nf, 512), np.float32)
        for i in range(nf):
            seg = mono[i * spf:i * spf + 2048]
            if len(seg) == 2048:
                wave[i] = seg[::4]
        np.save("wave.npy", wave)
        print("wrote", path, "%.1fs" % self.dur)
        return mix
```

## Appendix C — tested starter (15 s "Silk Road" demo)
`audio.py`
```python
from audio_kit import *  # audio_kit.py beside this file

T = Track(bpm=110, beats=28, root=146.83, scale="hijaz")
T.drone_bed(0, 26, level=lambda b: 0.3 if b < 8 else 0.16)
for i in range(4):
    T.at("fx", bell(T.deg(i + 4, 1)), 4 + i, 0.18, -0.4 + 0.25 * i)
T.riser_into(8, 4, 0.3)
T.hand_drum(8, 16, pattern=("b", "-", "s", "t", "b", "b", "s", "-"))
T.melody(8, [(0, 4, 1), (1, 5, 1, 4), (2, 3, 1.5), (4, 2, .5), (4.5, 1, .5), (5, 0, 1.5)])
T.stutter(15.5)
T.groove(16, 24)
T.hand_drum(16, 24, gain=0.8)
T.melody(16, [(0, 7, .5), (.5, 6, .5), (1, 7, .7), (1.75, 4, .8), (3, 5, 1.2, 7), (4, 4, .5), (4.5, 3, .5), (5, 2, .5), (6, 0, 1.5)])
T.at("fx", boom(), 16, 0.5)
T.tihai(24)
T.at("pad", voice(T.hz(0), T.tb(4)), 24, 0.25)
T.mixdown("music.wav", fade_beats=(25, 28))
```
`film.py`
```python
from engine import *  # engine.py beside this file

PAPER, INK, NIGHT = hx("F3E9D2"), hx("1A1410"), hx("101826")
LAPIS, SAFFRON, POMEGRANATE, JADE = hx("1F3A93"), hx("F4A300"), hx("C8102E"), hx("0F8A6B")

get_font("anton", "ofl/anton/Anton-Regular.ttf")
get_font("mono", "ofl/spacemono/SpaceMono-Regular.ttf")
get_font("fri", "ofl/fraunces/Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", [144, 380, 100, 1])
get_font("arabic", "ofl/notonaskharabic/NotoNaskhArabic[wght].ttf", [700])

for n, s in [("anton", "SILK ROAD"), ("mono", "c. 130 BCE · Chang'an → Samarkand → Antioch"), ("arabic", "طريق الحرير")]:
    assert not missing_glyphs(n, s), (n, missing_glyphs(n, s))

ROUTE = bezier((180, 700), (600, 300), (1200, 900), (1740, 420), 120)
ROUTE_CUM = cumlen(ROUTE)


def s_open(ctx, b, f):
    bg(ctx, NIGHT)
    w = wave_at(f).astype(float)
    ys = 540 + w / (abs(w).max() + .03) * (60 + 200 * env_at(f))
    rgba(ctx, SAFFRON); ctx.set_line_width(3)
    polyline(ctx, np.stack([np.linspace(0, W, len(ys)), ys], 1)); ctx.stroke()
    riso(ctx, lambda c: text(ctx, "SILK ROAD", "anton", 300, c, W / 2, 620, ax=.5, sc=back(ph(b, 4, .6))),
         PAPER, POMEGRANATE, dark=True, k=1.8)
    text(ctx, "طريق الحرير", "arabic", 90, SAFFRON, W / 2, 330, ax=.5, alpha=ph(b, 5, 1))
    return PAPER


def s_route(ctx, b, f):
    bg(ctx, PAPER)
    ctx.set_source(halftone(LAPIS, 10, 2.4)); ctx.rectangle(0, 760, W, 320); ctx.fill()
    rgba(ctx, POMEGRANATE); ctx.set_line_width(6)
    e = path_partial(ctx, ROUTE, ROUTE_CUM, eio(ph(b, 8, 6))); ctx.stroke()
    if e is not None:
        rgba(ctx, SAFFRON); ctx.arc(e[0], e[1], 12 + 5 * pulse(b), 0, 2 * PI); ctx.fill()
    for i, (x, y, name) in enumerate([(180, 700, "CHANG'AN"), (960, 620, "SAMARKAND"), (1740, 420, "ANTIOCH")]):
        text(ctx, name, "anton", 70, LAPIS, x, y - 30, ax=.5, sc=back(ph(b, 8 + i * 2.5, .5)))
    text_circle(ctx, "SILK · SPICE · PAPER · IDEAS · ", "mono", 16, INK, 1600, 850, 90, b * .3, alpha=ph(b, 9, 1))
    typewriter(ctx, "c. 130 BCE · Chang'an → Samarkand → Antioch", "mono", 22, INK, 120, 990, b, 9)
    return INK


def s_drop(ctx, b, f):
    pal = [(POMEGRANATE, PAPER), (LAPIS, SAFFRON)][int((b - 16) // 4) % 2]
    bg(ctx, pal[0])
    riso(ctx, lambda c: text(ctx, "6,400 km", "anton", fit_size("6,400 km", "anton", 1500, 400), c, W / 2, 560,
                             ax=.5, ay=.5, sc=1 + .04 * pulse(b, 8)), pal[1], JADE, dark=True, k=2)
    text(ctx, "of trade, carried on foot and hoof", "fri", 56, PAPER, W / 2, 820, ax=.5, alpha=ph(b, 17, 1))
    return PAPER


def s_end(ctx, b, f):
    bg(ctx, NIGHT)
    rgba(ctx, POMEGRANATE); ctx.arc(W / 2, H / 2, 18 + 8 * pulse(b), 0, 2 * PI); ctx.fill()
    return PAPER


def hud(ctx, b, fg):
    reg_marks(ctx, fg, (LAPIS, SAFFRON, POMEGRANATE, JADE))
    if 8 <= b < 24:
        text(ctx, "PLATE 0%d" % (1 + int(b >= 16)), "mono", 15, fg, W - 70, 86, ax=1)


SCENES = [(0, s_open), (8, s_route), (16, s_drop), (24, s_end)]
run(SCENES, 28, bpm=110, name="demo",
    wipes=[(8, POMEGRANATE, SAFFRON), (16, LAPIS, JADE, iris_wipe), (24, SAFFRON, POMEGRANATE)],
    glitches=[(15.5, 16.1)], flashes=[(16, WHITE, .5)], hud=hud, fade_out=25)
```
