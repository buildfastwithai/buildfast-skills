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
